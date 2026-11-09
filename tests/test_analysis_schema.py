import pytest
from pydantic import ValidationError
from app.schemas.analysis import Dimension, TwinResponse


def test_analysis_requires_evidence_and_bounded_scores():
    with pytest.raises(ValidationError):
        Dimension(score=101, explanation="Test", evidence=[])
    with pytest.raises(ValidationError):
        TwinResponse(content="A response", kind="unknown")
    assert Dimension(score=50, explanation="Contextual tendency",
        evidence=[{"message_id": 1, "quote": "I propose"}]).score == 50
