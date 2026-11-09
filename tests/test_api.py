from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.database.database import get_db
from app.main import create_app
from app.schemas.analysis import TwinResponse


def test_api_workflow_and_ownership(session_factory, db):
    clients = AsyncMock()
    clients.reply.return_value = TwinResponse(content="Counteroffer 120", kind="counteroffer")
    app = create_app(session_factory, lambda: clients, start_dispatcher=False)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        assert client.get("/health").json()["database"] == "ok"
        account = {"username": "student", "email": "student@example.com", "password": "a-test-password-long"}
        assert client.post("/auth/register", json=account).status_code == 201
        login = client.post("/auth/login", json=account).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        scenario = {"title": "Supply", "description": "Supply contract", "context": "Annual contract",
            "objective": "Reduce cost", "counterpart_role": "Supplier", "counterpart_goal": "Margin",
            "counterpart_limits": "Minimum 100"}
        created = client.post("/scenarios/", headers=headers, json=scenario)
        assert created.status_code == 201
        negotiation = client.post("/negotiations/", headers=headers, json={"scenario_id": created.json()["id"]})
        negotiation_id = negotiation.json()["id"]
        turn = client.post("/messages/", headers=headers, json={"negotiation_id": negotiation_id, "content": "Offer 100", "kind": "offer"})
        assert turn.status_code == 201
        assert len(turn.json()) == 2
        assert client.patch(f"/negotiations/{negotiation_id}", headers=headers,
            json={"status": "completed", "result": "Agreement at 120"}).status_code == 200
        assert client.post("/messages/", headers=headers, json={"negotiation_id": negotiation_id, "content": "More"}).status_code == 409
        assert len(client.get("/events", headers=headers).json()) == 4
        client.post("/auth/register", json={**account, "username": "other", "email": "other@example.com"})
        other = client.post("/auth/login", json={"email": "other@example.com", "password": account["password"]}).json()
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        assert client.get(f"/negotiations/{negotiation_id}", headers=other_headers).status_code == 404
        assert client.get(f"/messages/{negotiation_id}", headers=other_headers).status_code == 404
        assert client.get("/events", headers=other_headers).json() == []
