import json

from sqlalchemy.orm import Session

from app.models import NegotiatorProfile
from app.repositories.negotiation_repository import NegotiationRepository
from app.rpc import negotiation_pb2 as pb


def build_twin_context(db: Session, user_id: int, negotiation_id: int) -> pb.NegotiationContext:
    repository = NegotiationRepository(db, user_id)
    negotiation = repository.negotiation(negotiation_id)
    profile = db.get(NegotiatorProfile, user_id)
    return pb.NegotiationContext(
        user_id=user_id, negotiation_id=negotiation.id,
        scenario_json=json.dumps(negotiation.scenario_snapshot),
        profile_json=json.dumps(profile.payload if profile else {}),
        result=negotiation.result or "",
        messages=[pb.ConversationMessage(message_id=message.id, sender_type=message.sender_type,
            content=message.content, kind=message.kind) for message in repository.messages(negotiation_id)],
    )
