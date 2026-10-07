from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.services.conversation_service import process_user_message
from app.services.message_service import get_negotiation_messages


router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


@router.post(
    "/",
    response_model=list[MessageResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_new_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_message, twin_message = process_user_message(
            db,
            current_user.id,
            message_data,
        )

        return [
            user_message,
            twin_message,
        ]

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )


@router.get(
    "/{negotiation_id}",
    response_model=list[MessageResponse],
)
def get_messages(
    negotiation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_negotiation_messages(
            db,
            current_user.id,
            negotiation_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )