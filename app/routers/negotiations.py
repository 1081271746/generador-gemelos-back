from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.negotiation import NegotiationCreate, NegotiationResponse, NegotiationFinish
from app.services import negotiation_service as service


router = APIRouter(prefix="/negotiations", tags=["Negotiations"])


@router.post("/", response_model=NegotiationResponse, status_code=201)
def create(data: NegotiationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.create_negotiation(db, user.id, data)


@router.get("/", response_model=list[NegotiationResponse])
def list_negotiations(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.get_user_negotiations(db, user.id, offset, limit)


@router.get("/{negotiation_id}", response_model=NegotiationResponse)
def get(negotiation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.get_negotiation_by_id(db, negotiation_id, user.id)


@router.patch("/{negotiation_id}", response_model=NegotiationResponse)
def finish(negotiation_id: int, data: NegotiationFinish, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.finish_negotiation(db, user.id, negotiation_id, data)
