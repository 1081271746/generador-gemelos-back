from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
import pytest

from app.websocket.events import router
from app.core.security import create_access_token


class FakeStream:
    def __init__(self):
        self.cancelled = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        import asyncio
        await asyncio.sleep(3600)

    def cancel(self):
        self.cancelled = True


def test_websocket_rejects_invalid_auth_and_other_origins(session_factory):
    app = FastAPI()
    app.include_router(router)
    app.state.session_factory = session_factory
    app.state.cors_origins = ["http://localhost:4200"]
    with TestClient(app) as client:
        with client.websocket_connect("/ws/events") as ws:
            ws.send_json({"token": "invalid"})
            with pytest.raises(WebSocketDisconnect) as error:
                ws.receive_json()
            assert error.value.code == 4401
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/events", headers={"origin": "https://untrusted.example"}):
                pass
