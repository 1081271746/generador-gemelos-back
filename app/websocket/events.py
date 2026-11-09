import asyncio
import json
from contextlib import suppress

import grpc
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from app.core.errors import DomainError
from app.repositories.event_repository import EventRepository


router = APIRouter()


class AuthenticationFrame(BaseModel):
    token: str = Field(min_length=1, max_length=8192)
    negotiation_id: int = Field(0, ge=0)
    after_sequence: int = Field(0, ge=0)


async def stream_events(websocket: WebSocket, frame: AuthenticationFrame):
    cursor = frame.after_sequence
    failures = 0
    while True:
        stream = websocket.app.state.clients.subscribe(frame.token, frame.negotiation_id, cursor)
        try:
            async for event in stream:
                if event.sequence <= cursor:
                    continue
                await websocket.send_json({
                    "type": "event", "event_id": event.event_id, "sequence": event.sequence,
                    "negotiation_id": event.negotiation_id, "event_type": event.event_type,
                    "payload": json.loads(event.payload_json), "created_at": event.created_at,
                })
                cursor = event.sequence
                failures = 0
            return
        except grpc.aio.AioRpcError as error:
            if error.code() in (grpc.StatusCode.UNAUTHENTICATED, grpc.StatusCode.PERMISSION_DENIED):
                await websocket.close(code=4401)
                return
            failures += 1
            if failures >= 3:
                await websocket.close(code=1013, reason="Event service unavailable; reconnect using last sequence")
                return
            await asyncio.sleep(0.5 * failures)
        finally:
            stream.cancel()


async def wait_for_disconnect(websocket: WebSocket):
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


@router.websocket("/ws/events")
async def events(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin and origin not in websocket.app.state.cors_origins:
        await websocket.close(code=4403)
        return
    await websocket.accept()
    try:
        frame = AuthenticationFrame.model_validate(await asyncio.wait_for(websocket.receive_json(), timeout=10))
        repository = EventRepository(websocket.app.state.session_factory)
        await run_in_threadpool(repository.authenticate, frame.token, frame.negotiation_id)
    except (ValidationError, HTTPException, DomainError, ValueError, asyncio.TimeoutError):
        await websocket.close(code=4401)
        return
    except WebSocketDisconnect:
        return
    producer = asyncio.create_task(stream_events(websocket, frame))
    receiver = asyncio.create_task(wait_for_disconnect(websocket))
    try:
        await asyncio.wait([producer, receiver], return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in (producer, receiver):
            task.cancel()
        for task in (producer, receiver):
            with suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                await task
