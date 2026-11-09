from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioCreate
from app.repositories.negotiation_repository import NegotiationRepository


def create_scenario(db: Session, user_id: int, data: ScenarioCreate) -> Scenario:
    scenario = Scenario(user_id=user_id, **data.model_dump())
    db.add(scenario)
    db.commit()
    return scenario


def get_user_scenarios(db: Session, user_id: int, offset: int = 0, limit: int = 50) -> list[Scenario]:
    return list(db.scalars(select(Scenario).where(Scenario.user_id == user_id).order_by(Scenario.id.desc()).offset(offset).limit(limit)))


def get_scenario_by_id(db: Session, scenario_id: int, user_id: int) -> Scenario:
    return NegotiationRepository(db, user_id).scenario(scenario_id)


def update_scenario(db: Session, user_id: int, scenario_id: int, data: ScenarioCreate) -> Scenario:
    scenario = get_scenario_by_id(db, scenario_id, user_id)
    for name, value in data.model_dump().items():
        setattr(scenario, name, value)
    db.commit()
    return scenario


def archive_scenario(db: Session, user_id: int, scenario_id: int) -> None:
    scenario = get_scenario_by_id(db, scenario_id, user_id)
    scenario.is_active = False
    db.commit()
