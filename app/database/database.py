from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def make_engine(url: str):
    options = {"check_same_thread": False, "timeout": 20} if url.startswith("sqlite") else {}
    database_engine = create_engine(url, connect_args=options, pool_pre_ping=True)
    if url.startswith("sqlite"):
        @event.listens_for(database_engine, "connect")
        def configure_sqlite(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
    return database_engine


engine = make_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
