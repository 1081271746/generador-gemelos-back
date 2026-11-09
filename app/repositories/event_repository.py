from sqlalchemy import select

from app.core.dependencies import user_from_token
from app.core.errors import DomainError
from app.models import Event
from app.repositories.negotiation_repository import NegotiationRepository
from app.rpc import negotiation_pb2 as pb
from app.services.event_service import list_events, EVENT_TYPES


def to_proto(event: Event) -> pb.NegotiationEvent:
    import json
    return pb.NegotiationEvent(event_id=event.event_id, sequence=event.sequence, user_id=event.user_id,
        negotiation_id=event.negotiation_id, event_type=event.event_type,
        payload_json=json.dumps(event.payload), created_at=event.created_at.isoformat() + "Z")


class EventRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def authenticate(self, token: str, negotiation_id: int) -> int:
        with self.session_factory() as db:
            user = user_from_token(token, db)
            if negotiation_id:
                NegotiationRepository(db, user.id).negotiation(negotiation_id)
            return user.id

    def publication(self, event_id: str, user_id: int) -> pb.NegotiationEvent:
        with self.session_factory() as db:
            event = db.scalar(select(Event).where(Event.event_id == event_id, Event.user_id == user_id))
            if event is None:
                raise DomainError("Event not found", 404)
            NegotiationRepository(db, user_id).negotiation(event.negotiation_id)
            if event.event_type not in EVENT_TYPES:
                raise DomainError("Invalid stored event", 422)
            return to_proto(event)

    def since(self, user_id: int, negotiation_id: int, after: int) -> list[pb.NegotiationEvent]:
        with self.session_factory() as db:
            return [to_proto(event) for event in list_events(db, user_id, after, negotiation_id, 200)]
