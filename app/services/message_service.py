from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.negotiation import Negotiation
from app.schemas.message import MessageCreate


def create_message(
    db: Session,
    user_id: int,
    message_data: MessageCreate,
) -> Message:
    negotiation = (
        db.query(Negotiation)
        .filter(
            Negotiation.id == message_data.negotiation_id,
            Negotiation.user_id == user_id,
        )
        .first()
    )

def create_twin_message(
    db: Session,
    negotiation_id: int,
    content: str,
) -> Message:
    negotiation = (
        db.query(Negotiation)
        .filter(
            Negotiation.id == negotiation_id,
            Negotiation.status == "active",
        )
        .first()
    )

    if negotiation is None:
        raise ValueError("Active negotiation not found.")

    message = Message(
        negotiation_id=negotiation.id,
        sender_type="twin",
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message    

    if negotiation is None:
        raise ValueError("Negotiation not found.")

    message = Message(
    negotiation_id=negotiation.id,
    sender_type="user",
    content=message_data.content,
)

    db.add(message)
    db.commit()
    db.refresh(message)

    return message

def get_negotiation_messages(
    db: Session,
    user_id: int,
    negotiation_id: int,
) -> list[Message]:
    negotiation = (
        db.query(Negotiation)
        .filter(
            Negotiation.id == negotiation_id,
            Negotiation.user_id == user_id,
        )
        .first()
    )

    if negotiation is None:
        raise ValueError("Negotiation not found.")

    return (
        db.query(Message)
        .filter(Message.negotiation_id == negotiation_id)
        .order_by(Message.created_at.asc())
        .all()
    )