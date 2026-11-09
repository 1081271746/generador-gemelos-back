from unittest.mock import AsyncMock

import pytest

from app.core.errors import DomainError, ExternalServiceError
from app.schemas.message import MessageCreate
from app.schemas.negotiation import NegotiationCreate, NegotiationFinish
from app.schemas.analysis import TwinResponse
from app.services.conversation_service import process_user_message
from app.services.negotiation_service import create_negotiation, finish_negotiation
from app.services.message_service import prepare_turn, get_negotiation_messages


async def test_idempotent_turn_and_immutable_history(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    clients = AsyncMock()
    clients.reply.return_value = TwinResponse(content="Counteroffer 120", kind="counteroffer")
    data = MessageCreate(negotiation_id=negotiation.id, content="Offer 100", kind="offer")
    first = await process_user_message(db, owner.id, data, clients)
    second = await process_user_message(db, owner.id, data, clients)
    assert [m.id for m in first] == [m.id for m in second]
    clients.reply.assert_awaited_once()
    assert len(get_negotiation_messages(db, owner.id, negotiation.id)) == 2
    with pytest.raises(DomainError):
        await process_user_message(db, owner.id, data.model_copy(update={"content": "Changed"}), clients)


async def test_ai_failure_preserves_user_message_and_allows_retry(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    data = MessageCreate(negotiation_id=negotiation.id, content="Offer 100")
    clients = AsyncMock()
    clients.reply.side_effect = ExternalServiceError()
    with pytest.raises(ExternalServiceError):
        await process_user_message(db, owner.id, data, clients)
    assert len(get_negotiation_messages(db, owner.id, negotiation.id)) == 1
    clients.reply.side_effect = None
    clients.reply.return_value = TwinResponse(content="Try 120", kind="offer")
    assert len(await process_user_message(db, owner.id, data, clients)) == 2


def test_lease_prevents_concurrent_turns_and_completion(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    data = MessageCreate(negotiation_id=negotiation.id, content="Offer")
    prepare_turn(db, owner.id, data)
    with pytest.raises(DomainError):
        prepare_turn(db, owner.id, MessageCreate(negotiation_id=negotiation.id, content="Another"))
    with pytest.raises(DomainError):
        finish_negotiation(db, owner.id, negotiation.id, NegotiationFinish(status="completed", result="Done"))
