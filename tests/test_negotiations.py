import pytest
from sqlalchemy import select

from app.core.errors import DomainError
from app.models import Event
from app.schemas.negotiation import NegotiationCreate, NegotiationFinish
from app.services.negotiation_service import create_negotiation, finish_negotiation
from app.services.event_service import list_events


def test_scenario_snapshot_completion_and_persistent_events(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    scenario.objective = "Changed later"
    db.commit()
    assert negotiation.scenario_snapshot["objective"] == "Reduce cost"
    finish_negotiation(db, owner.id, negotiation.id, NegotiationFinish(status="completed", result="Agreement reached"))
    assert len(list_events(db, owner.id)) == 2
    assert list_events(db, owner.id + 1) == []
    with pytest.raises(DomainError):
        finish_negotiation(db, owner.id, negotiation.id, NegotiationFinish(status="cancelled", result="Cancel"))
    assert db.scalar(select(Event).where(Event.event_type == "negotiation.completed"))
