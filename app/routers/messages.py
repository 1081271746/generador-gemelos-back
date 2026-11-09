from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.services.conversation_service import process_user_message
from app.services.message_service import get_negotiation_messages


router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("/", response_model=list[MessageResponse], status_code=201)
async def create(data: MessageCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await process_user_message(db, user.id, data, request.app.state.clients)


@router.get("/{negotiation_id}", response_model=list[MessageResponse])
def list_messages(negotiation_id: int, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_negotiation_messages(db, user.id, negotiation_id, offset, limit)
