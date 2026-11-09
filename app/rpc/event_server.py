import asyncio
import signal
from uuid import UUID

import grpc
import jwt
from fastapi import HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import DomainError
from app.database.database import SessionLocal
from app.repositories.event_repository import EventRepository
from app.rpc import negotiation_pb2 as pb, negotiation_pb2_grpc as rpc
from app.rpc.transport import bearer, bind_server, require_service


class EventServicer(rpc.NegotiationEventServiceServicer):
    def __init__(self, session_factory, redis_client: Redis):
        self.repository = EventRepository(session_factory)
        self.redis = redis_client

    async def PublishEvent(self, request, context):
        user_id = await require_service(context, "events.publish")
        try:
            UUID(request.event_id)
            event = await run_in_threadpool(self.repository.publication, request.event_id, user_id)
            await self.redis.publish(f"negotiation:user:{user_id}", str(event.sequence))
            return pb.PublishResult(accepted=True)
        except ValueError:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid event identifier")
        except DomainError:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "Event unavailable")
        except RedisError:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "Event broker unavailable")

    async def SubscribeEvents(self, request, context):
        if request.after_sequence < 0 or request.negotiation_id < 0:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid subscription")
        try:
            token = bearer(context)
            user_id = await run_in_threadpool(self.repository.authenticate, token, request.negotiation_id)
        except (jwt.InvalidTokenError, HTTPException):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid subscription credentials")
        except DomainError:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "Negotiation unavailable")
        cursor = request.after_sequence
        try:
            async with self.redis.pubsub() as subscription:
                await subscription.subscribe(f"negotiation:user:{user_id}")
                while not context.cancelled():
                    await run_in_threadpool(self.repository.authenticate, token, request.negotiation_id)
                    events = await run_in_threadpool(self.repository.since, user_id, request.negotiation_id, cursor)
                    for event in events:
                        if event.sequence > cursor:
                            yield event
                            cursor = event.sequence
                    if len(events) == 200:
                        continue
                    await subscription.get_message(ignore_subscribe_messages=True, timeout=1.0)
        except (jwt.InvalidTokenError, HTTPException):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Subscription credentials expired or revoked")
        except DomainError:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "Subscription unavailable")
        except RedisError:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "Event broker disconnected; reconnect using the last sequence")


async def serve():
    settings.validate_security()
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    server = grpc.aio.server(options=[("grpc.max_receive_message_length", 1024 * 1024)])
    rpc.add_NegotiationEventServiceServicer_to_server(EventServicer(SessionLocal, redis), server)
    bind_server(server, settings.EVENT_GRPC_TARGET)
    stopping = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, stopping.set)
    await server.start()
    try:
        await stopping.wait()
    finally:
        await server.stop(5)
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(serve())
