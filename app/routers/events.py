from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.event import EventResponse
from app.services.event_service import list_events


router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=list[EventResponse])
def history(after: int = Query(0, ge=0), negotiation_id: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_events(db, user.id, after, negotiation_id, limit)
