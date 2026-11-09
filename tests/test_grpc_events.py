import asyncio
import socket
import subprocess
import time
from uuid import uuid4

import grpc
import pytest
from redis import Redis as SyncRedis
from redis.asyncio import Redis

from app.core.security import create_access_token, create_service_token, hash_password
from app.models import User, Event
from app.rpc import negotiation_pb2 as pb, negotiation_pb2_grpc as rpc
from app.rpc.event_server import EventServicer
from app.schemas.negotiation import NegotiationCreate
from app.services.event_service import record_event
from app.services.negotiation_service import create_negotiation


@pytest.fixture
def redis_url():
    with socket.socket() as socket_handle:
        socket_handle.bind(("127.0.0.1", 0))
        port = socket_handle.getsockname()[1]
    process = subprocess.Popen(["redis-server", "--bind", "127.0.0.1", "--port", str(port),
        "--save", "", "--appendonly", "no"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = SyncRedis(host="127.0.0.1", port=port)
    try:
        for _ in range(100):
            try:
                if client.ping():
                    break
            except Exception:
                time.sleep(0.02)
        else:
            raise RuntimeError("Real Redis did not start")
        yield f"redis://127.0.0.1:{port}/0"
    finally:
        client.close()
        process.terminate()
        process.wait(timeout=5)


@pytest.fixture
async def event_endpoint(session_factory, redis_url):
    redis = Redis.from_url(redis_url, decode_responses=True)
    server = grpc.aio.server()
    rpc.add_NegotiationEventServiceServicer_to_server(EventServicer(session_factory, redis), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield f"127.0.0.1:{port}"
    finally:
        await server.stop(0)
        await redis.aclose()


def access_metadata(user):
    return [("authorization", f"Bearer {create_access_token({'sub': str(user.id), 'ver': user.token_version})}")]


def publish_metadata(user):
    return [("authorization", f"Bearer {create_service_token(user.id, 'events.publish')}")]


async def test_real_fanout_replay_duplicates_and_separate_backend_channels(db, owner, scenario, event_endpoint):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    started = db.query(Event).first()
    async with grpc.aio.insecure_channel(event_endpoint) as channel_a, grpc.aio.insecure_channel(event_endpoint) as channel_b:
        backend_a = rpc.NegotiationEventServiceStub(channel_a)
        backend_b = rpc.NegotiationEventServiceStub(channel_b)
        first = backend_a.SubscribeEvents(pb.Subscription(negotiation_id=negotiation.id), metadata=access_metadata(owner))
        second = backend_b.SubscribeEvents(pb.Subscription(negotiation_id=negotiation.id), metadata=access_metadata(owner))
        try:
            assert (await asyncio.wait_for(first.read(), 3)).event_id == started.event_id
            assert (await asyncio.wait_for(second.read(), 3)).event_id == started.event_id
            event = record_event(db, owner.id, negotiation.id, "message.created", {"message_id": 1})
            db.commit()
            for _ in range(2):
                response = await backend_a.PublishEvent(pb.PublishRequest(event_id=event.event_id), metadata=publish_metadata(owner), timeout=2)
                assert response.accepted
            received = await asyncio.gather(asyncio.wait_for(first.read(), 3), asyncio.wait_for(second.read(), 3))
            assert [item.sequence for item in received] == [event.sequence, event.sequence]
            next_event = record_event(db, owner.id, negotiation.id, "twin.responded", {"message_id": 2})
            db.commit()
            await backend_b.PublishEvent(pb.PublishRequest(event_id=next_event.event_id), metadata=publish_metadata(owner), timeout=2)
            assert (await asyncio.wait_for(first.read(), 3)).event_id == next_event.event_id
            first.cancel()
            resumed = backend_a.SubscribeEvents(pb.Subscription(after_sequence=event.sequence), metadata=access_metadata(owner))
            try:
                assert (await asyncio.wait_for(resumed.read(), 3)).event_id == next_event.event_id
            finally:
                resumed.cancel()
        finally:
            first.cancel()
            second.cancel()


async def test_stream_isolation_and_invalid_publications(db, owner, scenario, event_endpoint):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    other = User(username="other", email="other@example.com", hashed_password=hash_password("another-test-password"))
    db.add(other)
    db.commit()
    async with grpc.aio.insecure_channel(event_endpoint) as channel:
        stub = rpc.NegotiationEventServiceStub(channel)
        forbidden = stub.SubscribeEvents(pb.Subscription(negotiation_id=negotiation.id), metadata=access_metadata(other))
        with pytest.raises(grpc.aio.AioRpcError) as error:
            await forbidden.read()
        assert error.value.code() == grpc.StatusCode.PERMISSION_DENIED
        with pytest.raises(grpc.aio.AioRpcError) as error:
            await stub.PublishEvent(pb.PublishRequest(event_id="not-a-uuid"), metadata=publish_metadata(owner), timeout=2)
        assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        event = db.query(Event).first()
        with pytest.raises(grpc.aio.AioRpcError) as error:
            await stub.PublishEvent(pb.PublishRequest(event_id=event.event_id), metadata=publish_metadata(other), timeout=2)
        assert error.value.code() == grpc.StatusCode.PERMISSION_DENIED
        assert stub is not None


async def test_two_real_fastapi_instances_share_grpc_redis_events(db, owner, scenario, session_factory, event_endpoint, monkeypatch):
    from fastapi.testclient import TestClient
    from app.core.config import settings
    from app.database.database import get_db
    from app.main import create_app

    monkeypatch.setattr(settings, "EVENT_GRPC_TARGET", event_endpoint)
    token = create_access_token({"sub": str(owner.id), "ver": owner.token_version})
    scenario_id = scenario.id
    db.rollback()

    def session_dependency():
        with session_factory() as session:
            yield session

    def run_clients():
        app_a = create_app(session_factory)
        app_b = create_app(session_factory)
        app_a.dependency_overrides[get_db] = session_dependency
        app_b.dependency_overrides[get_db] = session_dependency
        headers = {"Authorization": f"Bearer {token}"}
        with TestClient(app_a) as backend_a, TestClient(app_b) as backend_b:
            response = backend_a.post("/negotiations/", headers=headers, json={"scenario_id": scenario_id})
            assert response.status_code == 201
            negotiation_id = response.json()["id"]
            with backend_a.websocket_connect("/ws/events") as socket_a, backend_b.websocket_connect("/ws/events") as socket_b:
                frame = {"token": token, "negotiation_id": negotiation_id, "after_sequence": 0}
                socket_a.send_json(frame)
                socket_b.send_json(frame)
                first_a, first_b = socket_a.receive_json(), socket_b.receive_json()
                assert first_a["event_id"] == first_b["event_id"]
                assert first_a["event_type"] == "negotiation.started"
                result = backend_a.patch(f"/negotiations/{negotiation_id}", headers=headers,
                    json={"status": "cancelled", "result": "User ended practice"})
                assert result.status_code == 200
                next_a, next_b = socket_a.receive_json(), socket_b.receive_json()
                assert next_a["event_id"] == next_b["event_id"]
                assert next_b["event_type"] == "negotiation.cancelled"
                cursor = next_b["sequence"]
            with backend_b.websocket_connect("/ws/events") as resumed:
                resumed.send_json({"token": token, "after_sequence": first_b["sequence"]})
                assert resumed.receive_json()["sequence"] == cursor

    await asyncio.wait_for(asyncio.to_thread(run_clients), timeout=15)
