from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import DomainError
from app.models import Message, Negotiation
from app.repositories.negotiation_repository import NegotiationRepository
from app.schemas.analysis import TwinResponse
from app.schemas.message import MessageCreate
from app.services.event_service import record_event


def get_negotiation_messages(db: Session, user_id: int, negotiation_id: int, offset: int = 0, limit: int = 100):
    return NegotiationRepository(db, user_id).messages(negotiation_id, offset, limit)


def prepare_turn(db: Session, user_id: int, data: MessageCreate):
    NegotiationRepository(db, user_id).negotiation(data.negotiation_id)
    request_id = str(data.request_id)
    existing = list(db.scalars(select(Message).where(Message.negotiation_id == data.negotiation_id,
        Message.request_id == request_id).order_by(Message.id)))
    if existing and (existing[0].content != data.content or existing[0].kind != data.kind):
        raise DomainError("Idempotency key already used with different content", 409)
    if len(existing) == 2:
        db.rollback()
        return existing, None
    if existing:
        latest = db.scalar(select(Message.id).where(Message.negotiation_id == data.negotiation_id).order_by(Message.id.desc()).limit(1))
        if latest != existing[0].id:
            raise DomainError("Cannot retry an older incomplete turn after later messages", 409)
    now = datetime.utcnow()
    lease = str(uuid4())
    updated = db.execute(update(Negotiation).where(
        Negotiation.id == data.negotiation_id, Negotiation.user_id == user_id, Negotiation.status == "active",
        or_(Negotiation.processing_token.is_(None), Negotiation.processing_until < now),
    ).values(processing_token=lease, processing_until=now + timedelta(seconds=settings.GRPC_TIMEOUT_SECONDS + 15)))
    if not updated.rowcount:
        db.rollback()
        raise DomainError("Negotiation is closed or processing another request", 409)
    if not existing:
        message = Message(negotiation_id=data.negotiation_id, sender_type="user", content=data.content,
            kind=data.kind, request_id=request_id)
        db.add(message)
        db.flush()
        record_event(db, user_id, data.negotiation_id, "message.created", {"message_id": message.id})
        existing = [message]
    db.commit()
    return existing, lease


def complete_turn(db: Session, user_id: int, data: MessageCreate, lease: str, response: TwinResponse):
    updated = db.execute(update(Negotiation).where(Negotiation.id == data.negotiation_id,
        Negotiation.user_id == user_id, Negotiation.status == "active", Negotiation.processing_token == lease,
    ).values(processing_token=None, processing_until=None))
    if not updated.rowcount:
        db.rollback()
        raise DomainError("Turn lease expired; retry with the same request_id", 409)
    message = Message(negotiation_id=data.negotiation_id, sender_type="twin",
        content=response.content, kind=response.kind, request_id=str(data.request_id))
    db.add(message)
    db.flush()
    record_event(db, user_id, data.negotiation_id, "twin.responded", {"message_id": message.id})
    db.commit()
    return message


def fail_turn(db: Session, user_id: int, negotiation_id: int, lease: str):
    db.rollback()
    updated = db.execute(update(Negotiation).where(Negotiation.id == negotiation_id,
        Negotiation.user_id == user_id, Negotiation.processing_token == lease,
    ).values(processing_token=None, processing_until=None))
    if updated.rowcount:
        record_event(db, user_id, negotiation_id, "twin.failed", {"reason": "AI service unavailable"})
    db.commit()
