import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import DomainError
from app.database.base import Base
from app.database.database import SessionLocal
from app.rpc.client import ServiceClients
from app.routers import auth, scenarios, negotiations, messages, analyses, events
from app.services.outbox_service import run_dispatcher
from app.websocket.events import router as websocket_router


def check_schema(session_factory):
    with session_factory() as db:
        inspector = inspect(db.get_bind())
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                raise RuntimeError("Database is not initialized; run: python -m alembic upgrade head")
            actual = {column["name"] for column in inspector.get_columns(table.name)}
            if not set(table.columns.keys()).issubset(actual):
                raise RuntimeError("Database schema is outdated; run: python -m alembic upgrade head")


def create_app(session_factory=SessionLocal, client_factory=ServiceClients, start_dispatcher: bool = True):
    @asynccontextmanager
    async def lifespan(application):
        settings.validate_security()
        await run_in_threadpool(check_schema, session_factory)
        application.state.clients = client_factory()
        dispatcher = asyncio.create_task(run_dispatcher(session_factory, application.state.clients)) if start_dispatcher else None
        try:
            yield
        finally:
            if dispatcher:
                dispatcher.cancel()
                with suppress(asyncio.CancelledError):
                    await dispatcher
            await application.state.clients.close()

    application = FastAPI(title="Negotiation Twin Generator API", version="2.0.0", lifespan=lifespan)
    application.state.session_factory = session_factory
    application.state.cors_origins = settings.CORS_ORIGINS
    application.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
    for router in (auth.router, scenarios.router, negotiations.router, messages.router, analyses.router, events.router, websocket_router):
        application.include_router(router)

    @application.exception_handler(DomainError)
    async def domain_error(request, error):
        return JSONResponse({"detail": error.message}, status_code=error.status_code)

    @application.exception_handler(IntegrityError)
    async def integrity_error(request, error):
        return JSONResponse({"detail": "Operation conflicts with existing data"}, status_code=409)

    @application.get("/")
    def root():
        return {"message": "Negotiation Twin Generator API is running.", "docs": "/docs"}

    @application.get("/health")
    def health():
        try:
            with session_factory() as db:
                db.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"database": "unavailable"}, status_code=503)
        return {"database": "ok", "gemini_configured": bool(settings.GEMINI_API_KEY)}

    return application


app = create_app()
