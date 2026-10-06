from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.negotiation import Negotiation
from app.models.scenario import Scenario


def build_twin_context(
    db: Session,
    user_id: int,
    negotiation_id: int,
) -> dict:
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

    scenario = (
        db.query(Scenario)
        .filter(Scenario.id == negotiation.scenario_id)
        .first()
    )

    if scenario is None:
        raise ValueError("Scenario not found.")

    messages = (
        db.query(Message)
        .filter(Message.negotiation_id == negotiation.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return {
        "negotiation": {
            "id": negotiation.id,
            "status": negotiation.status,
        },
        "scenario": {
            "title": scenario.title,
            "description": scenario.description,
            "context": scenario.context,
            "objective": scenario.objective,
            "counterpart_role": scenario.counterpart_role,
            "counterpart_goal": scenario.counterpart_goal,
            "counterpart_limits": scenario.counterpart_limits,
        },
        "messages": [
            {
                "sender_type": message.sender_type,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }