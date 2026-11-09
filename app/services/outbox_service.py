import asyncio
import logging

import grpc
from sqlalchemy import select, update
from starlette.concurrency import run_in_threadpool

from app.core.errors import ExternalServiceError
from app.models import Event


logger = logging.getLogger(__name__)


def pending_events(session_factory):
    with session_factory() as db:
        return [(event.event_id, event.user_id) for event in db.scalars(
            select(Event).where(Event.delivered.is_(False)).order_by(Event.sequence).limit(100))]


def acknowledge_event(session_factory, event_id: str):
    with session_factory() as db:
        db.execute(update(Event).where(Event.event_id == event_id).values(delivered=True))
        db.commit()


async def dispatch_pending(session_factory, clients) -> int:
    count = 0
    for event_id, user_id in await run_in_threadpool(pending_events, session_factory):
        try:
            await clients.publish(event_id, user_id)
        except (grpc.aio.AioRpcError, ExternalServiceError):
            break
        await run_in_threadpool(acknowledge_event, session_factory, event_id)
        count += 1
    return count


async def run_dispatcher(session_factory, clients):
    while True:
        try:
            await dispatch_pending(session_factory, clients)
        except Exception:
            logger.warning("Event dispatcher iteration failed; pending events will be retried")
        await asyncio.sleep(1)
