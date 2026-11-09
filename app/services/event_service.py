from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import Event
from app.repositories.negotiation_repository import NegotiationRepository


EVENT_TYPES = {
    "negotiation.started", "message.created", "twin.responded", "negotiation.completed",
    "negotiation.cancelled", "analysis.completed", "recommendation.created",
    "profile.updated", "twin.failed",
}


def record_event(db: Session, user_id: int, negotiation_id: int, event_type: str, payload: dict | None = None) -> Event:
    if event_type not in EVENT_TYPES:
        raise DomainError("Invalid event type", 422)
    NegotiationRepository(db, user_id).negotiation(negotiation_id)
    event = Event(user_id=user_id, negotiation_id=negotiation_id, event_type=event_type, payload=payload or {})
    db.add(event)
    db.flush()
    return event


def list_events(db: Session, user_id: int, after: int = 0, negotiation_id: int = 0, limit: int = 100) -> list[Event]:
    if negotiation_id:
        NegotiationRepository(db, user_id).negotiation(negotiation_id)
    query = select(Event).where(Event.user_id == user_id, Event.sequence > after)
    if negotiation_id:
        query = query.where(Event.negotiation_id == negotiation_id)
    return list(db.scalars(query.order_by(Event.sequence).limit(limit)))
