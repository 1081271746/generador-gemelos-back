from unittest.mock import AsyncMock

import httpx
import pytest

from app.ai.gemini import GeminiService
from app.core.config import Settings
from app.core.errors import ExternalServiceError
from app.schemas.analysis import TwinResponse


def make_service(status, body):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body)))
    redis = AsyncMock()
    redis.eval.return_value = 1
    return GeminiService(Settings(GEMINI_API_KEY="test-only-placeholder"), client, redis)


async def test_validated_response_without_live_quota():
    service = make_service(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [
        {"text": '{"content":"I offer 120","kind":"offer"}'}]}}]})
    result = await service.generate("Act as supplier", {}, TwinResponse)
    assert result.content == "I offer 120"
    await service.close()


@pytest.mark.parametrize("status,body", [(429, {}), (503, {}), (200, {}), (200, {
    "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"kind":"invented"}'}]}}]
})])
async def test_quota_and_invalid_responses_are_controlled(status, body):
    service = make_service(status, body)
    with pytest.raises(ExternalServiceError):
        await service.generate("test", {}, TwinResponse)
    await service.close()


async def test_missing_key_does_not_produce_fake_reply():
    service = GeminiService(Settings(GEMINI_API_KEY=""), httpx.AsyncClient(), AsyncMock())
    with pytest.raises(ExternalServiceError, match="not configured"):
        await service.generate("test", {}, TwinResponse)
    await service.close()


async def test_timeout_does_not_expose_provider_error_or_credentials():
    def timeout(request):
        raise httpx.ReadTimeout("provider details must not escape")
    redis = AsyncMock()
    redis.eval.return_value = 1
    service = GeminiService(Settings(GEMINI_API_KEY="test-only-placeholder"),
        httpx.AsyncClient(transport=httpx.MockTransport(timeout)), redis)
    with pytest.raises(ExternalServiceError) as error:
        await service.generate("test", {}, TwinResponse)
    assert "provider details" not in str(error.value)
    await service.close()
