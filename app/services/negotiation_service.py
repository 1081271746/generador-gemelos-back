from sqlalchemy.orm import Session

from app.models.negotiation import Negotiation
from app.models.scenario import Scenario
from app.schemas.negotiation import NegotiationCreate


def create_negotiation(
    db: Session,
    user_id: int,
    negotiation_data: NegotiationCreate,
) -> Negotiation:
    scenario = (
        db.query(Scenario)
        .filter(
            Scenario.id == negotiation_data.scenario_id,
            Scenario.user_id == user_id,
        )
        .first()
    )

    if scenario is None:
        raise ValueError("Scenario not found.")

    negotiation = Negotiation(
        user_id=user_id,
        scenario_id=scenario.id,
        status="active",
    )

    db.add(negotiation)
    db.commit()
    db.refresh(negotiation)

    return negotiation

def get_user_negotiations(
    db: Session,
    user_id: int,
) -> list[Negotiation]:
    return (
        db.query(Negotiation)
        .filter(Negotiation.user_id == user_id)
        .order_by(Negotiation.started_at.desc())
        .all()
    )

def get_negotiation_by_id(
    db: Session,
    negotiation_id: int,
    user_id: int,
) -> Negotiation | None:
    return (
        db.query(Negotiation)
        .filter(
            Negotiation.id == negotiation_id,
            Negotiation.user_id == user_id,
        )
        .first()
    )