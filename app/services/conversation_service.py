from sqlalchemy.orm import Session

from app.services.message_service import (
    create_message,
    create_twin_message,
)
from app.services.twin_engine import generate_twin_response
from app.services.twin_service import build_twin_context
from app.schemas.message import MessageCreate


def process_user_message(
    db: Session,
    user_id: int,
    message_data: MessageCreate,
) -> tuple:
    user_message = create_message(
        db,
        user_id,
        message_data,
    )

    context = build_twin_context(
        db,
        user_id,
        message_data.negotiation_id,
    )

    twin_response = generate_twin_response(context)

    twin_message = create_twin_message(
        db,
        message_data.negotiation_id,
        twin_response,
    )

    return user_message, twin_message