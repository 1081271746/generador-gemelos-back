from unittest.mock import AsyncMock

import pytest

from app.core.errors import ExternalServiceError
from app.models import Message
from app.schemas.analysis import AnalysisResult, DIMENSION_NAMES
from app.schemas.negotiation import NegotiationCreate, NegotiationFinish
from app.services.analysis_service import analyze_negotiation
from app.services.negotiation_service import create_negotiation, finish_negotiation
from app.services.profile_service import get_profile


@pytest.fixture
def completed_negotiation(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    message = Message(negotiation_id=negotiation.id, sender_type="user", content="I propose 100", kind="offer")
    db.add(message)
    db.commit()
    finish_negotiation(db, owner.id, negotiation.id, NegotiationFinish(status="completed", result="No agreement"))
    return negotiation, message


def analysis_result(message_id, quote="I propose 100"):
    dimension = {"score": 60, "explanation": "A contextual observation", "evidence": [{"message_id": message_id, "quote": quote}]}
    return AnalysisResult(summary="A price negotiation", strategies=["anchoring"], strengths=["clear proposals"],
        improvement_areas=["explain reasons"], dimensions={name: dimension for name in DIMENSION_NAMES},
        outcome="No agreement", objective_evaluation="Cost goal not reached", recommendations=["Explain your offer"],
        exercises=[{"title": "Explain an offer", "instructions": "Support price with costs", "scenario": "Supply renewal"}],
        alerts=[])


async def test_analysis_saved_once_and_profile_evolution(db, owner, completed_negotiation):
    negotiation, message = completed_negotiation
    clients = AsyncMock()
    clients.analyze.return_value = analysis_result(message.id)
    first = await analyze_negotiation(db, owner.id, negotiation.id, clients)
    second = await analyze_negotiation(db, owner.id, negotiation.id, clients)
    assert first.id == second.id
    clients.analyze.assert_awaited_once()
    profile = get_profile(db, owner.id)
    assert profile["sample_count"] == 1
    assert profile["payload"]["dimension_averages"]["cooperation"] == 60


async def test_fabricated_evidence_is_not_saved(db, owner, completed_negotiation):
    negotiation, message = completed_negotiation
    clients = AsyncMock()
    clients.analyze.return_value = analysis_result(message.id, "Invented quotation")
    with pytest.raises(ExternalServiceError, match="evidence"):
        await analyze_negotiation(db, owner.id, negotiation.id, clients)
    assert get_profile(db, owner.id)["sample_count"] == 0
