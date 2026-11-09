from datetime import datetime

from sqlalchemy import select, update, or_
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models.negotiation import Negotiation
from app.repositories.negotiation_repository import NegotiationRepository
from app.schemas.negotiation import NegotiationCreate, NegotiationFinish
from app.schemas.scenario import ScenarioCreate
from app.services.event_service import record_event
from app.utils.time import utc_now


def create_negotiation(db: Session, user_id: int, data: NegotiationCreate) -> Negotiation:
    scenario = NegotiationRepository(db, user_id).scenario(data.scenario_id)
    if not scenario.is_active:
        raise DomainError("Scenario is archived", 409)
    snapshot = ScenarioCreate.model_validate(scenario, from_attributes=True).model_dump()
    negotiation = Negotiation(user_id=user_id, scenario_id=scenario.id, scenario_snapshot=snapshot)
    db.add(negotiation)
    db.flush()
    record_event(db, user_id, negotiation.id, "negotiation.started")
    db.commit()
    return negotiation


def get_user_negotiations(db: Session, user_id: int, offset: int = 0, limit: int = 50) -> list[Negotiation]:
    return list(db.scalars(select(Negotiation).where(Negotiation.user_id == user_id).order_by(Negotiation.id.desc()).offset(offset).limit(limit)))


def get_negotiation_by_id(db: Session, negotiation_id: int, user_id: int) -> Negotiation:
    return NegotiationRepository(db, user_id).negotiation(negotiation_id)


def finish_negotiation(db: Session, user_id: int, negotiation_id: int, data: NegotiationFinish) -> Negotiation:
    negotiation = get_negotiation_by_id(db, negotiation_id, user_id)
    now = utc_now()
    result = db.execute(update(Negotiation).where(
        Negotiation.id == negotiation_id, Negotiation.user_id == user_id, Negotiation.status == "active",
        or_(Negotiation.processing_token.is_(None), Negotiation.processing_until < now),
    ).values(status=data.status, result=data.result, ended_at=now))
    if not result.rowcount:
        db.rollback()
        raise DomainError("Negotiation is closed or processing a request", 409)
    record_event(db, user_id, negotiation_id, f"negotiation.{data.status}")
    db.commit()
    db.refresh(negotiation)
    return negotiation
