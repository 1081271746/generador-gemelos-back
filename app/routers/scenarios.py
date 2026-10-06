from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.models.scenario import Scenario
from app.models.user import User
from app.schemas.scenario import ScenarioCreate, ScenarioResponse
from app.services.scenario_service import (
    create_scenario,
    get_user_scenarios,
)

from app.services.scenario_service import (
    create_scenario,
    get_user_scenarios,
    get_scenario_by_id,
)

router = APIRouter(
    prefix="/scenarios",
    tags=["Scenarios"],
)


@router.post(
    "/",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_scenario(
    scenario_data: ScenarioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_scenario(
        db,
        current_user.id,
        scenario_data,
    )

@router.get(
    "/",
    response_model=list[ScenarioResponse],
)
def get_scenarios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_scenarios(
        db,
        current_user.id,
    )

@router.get(
    "/{scenario_id}",
    response_model=ScenarioResponse,
)
def get_scenario(
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scenario = get_scenario_by_id(
        db,
        scenario_id,
        current_user.id,
    )

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    return scenario

    