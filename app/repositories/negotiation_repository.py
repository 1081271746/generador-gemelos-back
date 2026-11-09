from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import Message, Negotiation, Scenario


class NegotiationRepository:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def scenario(self, scenario_id: int) -> Scenario:
        result = self.db.scalar(select(Scenario).where(Scenario.id == scenario_id, Scenario.user_id == self.user_id))
        if result is None:
            raise DomainError("Scenario not found", 404)
        return result

    def negotiation(self, negotiation_id: int) -> Negotiation:
        result = self.db.scalar(select(Negotiation).where(Negotiation.id == negotiation_id, Negotiation.user_id == self.user_id))
        if result is None:
            raise DomainError("Negotiation not found", 404)
        return result

    def messages(self, negotiation_id: int, offset: int = 0, limit: int | None = None) -> list[Message]:
        self.negotiation(negotiation_id)
        query = select(Message).where(Message.negotiation_id == negotiation_id).order_by(Message.id).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return list(self.db.scalars(query))
