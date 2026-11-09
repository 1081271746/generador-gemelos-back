import asyncio

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.rpc.client import ServiceClients
from app.schemas.message import MessageCreate
from app.services.message_service import prepare_turn, complete_turn, fail_turn
from app.services.twin_service import build_twin_context
from app.services.twin_engine import generate_twin_response


async def process_user_message(db: Session, user_id: int, data: MessageCreate, clients: ServiceClients):
    messages, lease = await run_in_threadpool(prepare_turn, db, user_id, data)
    if lease is None:
        return messages
    try:
        context = await run_in_threadpool(build_twin_context, db, user_id, data.negotiation_id)
        await run_in_threadpool(db.rollback)
        response = await generate_twin_response(context, clients)
        message = await run_in_threadpool(complete_turn, db, user_id, data, lease, response)
        return [messages[0], message]
    except (Exception, asyncio.CancelledError):
        await asyncio.shield(run_in_threadpool(fail_turn, db, user_id, data.negotiation_id, lease))
        raise
