from app.models import Message
from app.schemas.negotiation import NegotiationCreate
from app.services.negotiation_service import create_negotiation


def test_orm_relationships_preserve_owned_history(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    message = Message(negotiation_id=negotiation.id, sender_type="user", content="Offer 100")
    db.add(message)
    db.commit()
    assert negotiation.user.id == owner.id
    assert negotiation.scenario.id == scenario.id
    assert negotiation.messages[0].content == "Offer 100"
    assert message.negotiation.id == negotiation.id
