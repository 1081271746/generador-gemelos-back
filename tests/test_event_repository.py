import pytest

from app.core.errors import DomainError
from app.repositories.event_repository import EventRepository
from app.schemas.negotiation import NegotiationCreate
from app.services.negotiation_service import create_negotiation
from app.services.event_service import list_events, record_event


def test_persisted_event_is_authorized_and_replayable(db, owner, scenario, session_factory):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    event = list_events(db, owner.id)[0]
    repository = EventRepository(session_factory)
    assert repository.publication(event.event_id, owner.id).event_type == "negotiation.started"
    with pytest.raises(DomainError):
        repository.publication(event.event_id, owner.id + 1)
    assert len(repository.since(owner.id, negotiation.id, 0)) == 1
    assert repository.since(owner.id, negotiation.id, event.sequence) == []
    with pytest.raises(DomainError):
        record_event(db, owner.id, negotiation.id, "invented")
