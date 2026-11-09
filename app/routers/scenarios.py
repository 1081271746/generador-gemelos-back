from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.scenario import ScenarioCreate, ScenarioResponse
from app.services import scenario_service as service


router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.post("/", response_model=ScenarioResponse, status_code=201)
def create(data: ScenarioCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.create_scenario(db, user.id, data)


@router.get("/", response_model=list[ScenarioResponse])
def list_scenarios(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.get_user_scenarios(db, user.id, offset, limit)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get(scenario_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.get_scenario_by_id(db, scenario_id, user.id)


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update(scenario_id: int, data: ScenarioCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.update_scenario(db, user.id, scenario_id, data)


@router.delete("/{scenario_id}", status_code=204)
def archive(scenario_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.archive_scenario(db, user.id, scenario_id)
    return Response(status_code=204)
