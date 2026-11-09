from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.routers.analyses import router as analyses_router
from app.routers.events import router as events_router
from app.schemas.negotiation import NegotiationCreate
from app.services.negotiation_service import create_negotiation


def test_read_routes_are_private_and_paginated(db, owner, scenario):
    app = FastAPI()
    app.include_router(analyses_router)
    app.include_router(events_router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        assert client.get("/profile").status_code == 401
        app.dependency_overrides[get_current_user] = lambda: owner
        assert client.get("/profile").json()["sample_count"] == 0
        assert client.get("/recommendations").json()["exercises"] == []
        create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
        assert len(client.get("/events").json()) == 1
        assert client.get("/events?after=-1").status_code == 422
