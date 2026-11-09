from unittest.mock import AsyncMock
import pytest
from app.core.errors import ExternalServiceError
from app.schemas.negotiation import NegotiationCreate
from app.services.negotiation_service import create_negotiation
from app.services.outbox_service import dispatch_pending, pending_events


async def test_outbox_survives_broker_failure_and_retries(db, owner, scenario, session_factory):
    create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    clients = AsyncMock()
    clients.publish.side_effect = ExternalServiceError()
    assert await dispatch_pending(session_factory, clients) == 0
    assert len(pending_events(session_factory)) == 1
    clients.publish.side_effect = None
    assert await dispatch_pending(session_factory, clients) == 1
    assert pending_events(session_factory) == []
