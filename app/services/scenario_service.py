from sqlalchemy.orm import Session

from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioCreate


def create_scenario(
    db: Session,
    user_id: int,
    scenario_data: ScenarioCreate,
) -> Scenario:
    scenario = Scenario(
        user_id=user_id,
        title=scenario_data.title,
        description=scenario_data.description,
        context=scenario_data.context,
        objective=scenario_data.objective,
        counterpart_role=scenario_data.counterpart_role,
        counterpart_goal=scenario_data.counterpart_goal,
        counterpart_limits=scenario_data.counterpart_limits,
    )

    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return scenario


def get_user_scenarios(
    db: Session,
    user_id: int,
) -> list[Scenario]:
    return (
        db.query(Scenario)
        .filter(Scenario.user_id == user_id)
        .order_by(Scenario.created_at.desc())
        .all()
    )

def get_scenario_by_id(
    db: Session,
    scenario_id: int,
    user_id: int,
) -> Scenario | None:
    return (
        db.query(Scenario)
        .filter(
            Scenario.id == scenario_id,
            Scenario.user_id == user_id,
        )
        .first()
    )