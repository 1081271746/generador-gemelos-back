import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import DomainError
from app.database.database import get_db
from app.routers.auth import router


@pytest.fixture
def auth_client(db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    @app.exception_handler(DomainError)
    async def handle_error(request, error):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": error.message}, status_code=error.status_code)
    with TestClient(app) as client:
        yield client


def test_registration_login_logout_and_isolation(auth_client):
    data = {"username": "student", "email": "student@example.com", "password": "test-long-password"}
    assert auth_client.post("/auth/register", json=data).status_code == 201
    assert auth_client.post("/auth/register", json=data).status_code == 409
    assert auth_client.get("/auth/me").status_code == 401
    token = auth_client.post("/auth/login", json=data | {"username": None}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert auth_client.get("/auth/me", headers=headers).json()["username"] == "student"
    assert auth_client.post("/auth/logout", headers=headers).status_code == 204
    assert auth_client.get("/auth/me", headers=headers).status_code == 401


def test_password_change_revokes_previous_tokens(auth_client, owner):
    token = auth_client.post("/auth/login", json={"email": owner.email, "password": "test-password-long"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert auth_client.post("/auth/password", headers=headers, json={
        "current_password": "test-password-long", "new_password": "new-test-password-long"
    }).status_code == 204
    assert auth_client.get("/auth/me", headers=headers).status_code == 401
