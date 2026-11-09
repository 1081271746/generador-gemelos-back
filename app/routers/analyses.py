from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.analysis import AnalysisResponse
from app.services import analysis_service
from app.services.profile_service import get_profile


router = APIRouter(tags=["Analysis and profile"])


@router.post("/negotiations/{negotiation_id}/analysis", response_model=AnalysisResponse, status_code=201)
async def analyze(negotiation_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await analysis_service.analyze_negotiation(db, user.id, negotiation_id, request.app.state.clients)


@router.get("/analyses", response_model=list[AnalysisResponse])
def list_analyses(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analysis_service.list_analyses(db, user.id, offset, limit)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analysis_service.get_analysis(db, user.id, analysis_id)


@router.get("/profile")
def profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_profile(db, user.id)


@router.get("/recommendations")
def recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = get_profile(db, user.id)["payload"]
    return {"recommendations": payload.get("recommendations", []), "exercises": payload.get("exercises", [])}
