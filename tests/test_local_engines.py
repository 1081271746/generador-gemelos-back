from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from app.ai.analysis_engine import AnalysisEngine
from app.ai.policy import validate_numeric_limits
from app.ai.twin_engine import TwinEngine
from app.core.errors import ExternalServiceError
from app.schemas.analysis import AnalysisResult, TwinResponse
from training.seed import examples


def context_data():
    return next(examples()).context.model_dump()


async def test_twin_preserves_scenario_history_and_private_profile():
    data = context_data()
    data["profile"] = {"dimension_averages": {"cooperation": 65}}
    fake = AsyncMock()
    fake.generate.return_value = TwinResponse(content="Propongo 95 por caja.", kind="counteroffer")
    result = await TwinEngine(fake).reply(data)
    sent = fake.generate.call_args.args[1]
    assert sent["scenario"]["counterpart_limits"] == data["scenario"]["counterpart_limits"]
    assert sent["profile"] == data["profile"]
    assert sent["messages"] == data["messages"]
    assert result.content == "Propongo 95 por caja."


@pytest.mark.parametrize("change", ["duplicate", "last_twin", "unknown_sender", "empty"])
async def test_invalid_context_never_reaches_model(change):
    data = context_data()
    if change == "duplicate":
        data["messages"] *= 2
    elif change == "last_twin":
        data["messages"][-1]["sender_type"] = "twin"
    elif change == "unknown_sender":
        data["messages"][-1]["sender_type"] = "system"
    else:
        data["messages"] = []
    fake = AsyncMock()
    with pytest.raises(ValueError):
        await TwinEngine(fake).reply(data)
    fake.generate.assert_not_called()


@pytest.mark.parametrize("limit,bad,good", [
    ("No vender por debajo de 90 por caja", "Acepto 80 por caja", "Propongo 95 por caja"),
    ("Minimum 100 per unit", "Acepto 90", "Propongo 120"),
    ("Salario máximo 4500", "Ofrezco 5000", "Ofrezco 4500"),
    ("Descuento máximo 10%", "Descuento 30%", "Descuento 10%"),
])
def test_numeric_guard(limit, bad, good):
    with pytest.raises(ExternalServiceError):
        validate_numeric_limits(bad, limit)
    validate_numeric_limits(good, limit)


async def test_twin_fails_closed_on_out_of_bounds_model_reply():
    fake = AsyncMock()
    fake.generate.return_value = TwinResponse(content="Acepto 80 por caja.", kind="offer")
    with pytest.raises(ExternalServiceError):
        await TwinEngine(fake).reply(context_data())


def test_ambiguous_thousands_separator_does_not_weaken_limit():
    with pytest.raises(ExternalServiceError, match="unambiguous"):
        validate_numeric_limits("Propongo 5000", "Precio mínimo 9.000")


def test_private_boundary_must_not_be_labeled_in_the_reply():
    with pytest.raises(ExternalServiceError, match="private numeric boundary"):
        validate_numeric_limits("El precio mínimo es 90", "No vender por debajo de 90")
    validate_numeric_limits("Propongo 90 por caja.", "No vender por debajo de 90")


async def test_analysis_exact_user_quotes_only():
    example = list(examples())[1]
    fake = AsyncMock()
    fake.generate.return_value = AnalysisResult.model_validate(example.expected)
    result = await AnalysisEngine(fake).analyze(example.context.model_dump())
    assert result.interpretation == "contextual_indicators"
    wrong = deepcopy(example.expected)
    wrong["dimensions"]["cooperation"]["evidence"][0]["quote"] = "An invented statement"
    fake.generate.return_value = AnalysisResult.model_validate(wrong)
    with pytest.raises(ExternalServiceError):
        await AnalysisEngine(fake).analyze(example.context.model_dump())
    wrong["dimensions"]["cooperation"]["evidence"][0] = {"message_id": 2,
                                                           "quote": example.context.messages[1].content}
    fake.generate.return_value = AnalysisResult.model_validate(wrong)
    with pytest.raises(ExternalServiceError):
        await AnalysisEngine(fake).analyze(example.context.model_dump())
