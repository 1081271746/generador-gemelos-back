import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from app.ai.inference.config import InferenceConfig
from app.ai.inference.local import LocalInference
from app.ai.model_manager import create_provider
from app.core.errors import ExternalServiceError
from app.schemas.analysis import TwinResponse


def completion(content=None, finish="stop"):
    return {"choices": [{"finish_reason": finish, "message": {
        "content": json.dumps(content or {"content": "Propongo 120.", "kind": "counteroffer"})}}]}


def provider(handler, **kwargs):
    return LocalInference(InferenceConfig(**kwargs), httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_local_client_sends_schema_and_no_commercial_credentials():
    def handler(request):
        data = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        assert request.url.host == "127.0.0.1"
        assert "authorization" not in request.headers
        assert "x-goog-api-key" not in request.headers
        assert data["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
        assert data["max_tokens"] == 2048
        assert data["messages"][0]["role"] == "system"
        return httpx.Response(200, json=completion())
    service = provider(handler)
    try:
        assert (await service.generate("rules", {"messages": []}, TwinResponse)).kind == "counteroffer"
    finally:
        await service.close()


@pytest.mark.parametrize("status", [301, 400, 401, 429, 500, 503])
async def test_local_errors_are_not_fabricated_success(status):
    service = provider(lambda request: httpx.Response(status))
    try:
        with pytest.raises(ExternalServiceError):
            await service.generate("rules", {}, TwinResponse)
    finally:
        await service.close()


@pytest.mark.parametrize("data", [
    {}, {"choices": []}, completion(finish="length"),
    completion({"content": "", "kind": "offer"}),
    completion({"content": "OK", "kind": "execute_sql"}),
    completion({"content": "OK", "kind": "offer", "tool": "query"}),
])
async def test_invalid_and_truncated_output_rejected(data):
    service = provider(lambda request: httpx.Response(200, json=data))
    try:
        with pytest.raises(ExternalServiceError):
            await service.generate("rules", {}, TwinResponse)
    finally:
        await service.close()


async def test_large_context_rejected_before_network():
    def never(request):
        raise AssertionError("Network must not be reached")
    service = provider(never, max_context_bytes=1000)
    try:
        with pytest.raises(ExternalServiceError, match="context too large"):
            await service.generate("rules", {"text": "ñ" * 1000}, TwinResponse)
    finally:
        await service.close()


async def test_response_memory_bounded():
    service = provider(lambda request: httpx.Response(200, content=b"x" * 2000), max_response_bytes=1024)
    try:
        with pytest.raises(ExternalServiceError, match="too large"):
            await service.generate("rules", {}, TwinResponse)
    finally:
        await service.close()


async def test_deadline_and_slot_release():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=completion())
    service = provider(handler, timeout=0.01)
    try:
        with pytest.raises(ExternalServiceError):
            await service.generate("rules", {}, TwinResponse)
        assert service.slots._value == 1
    finally:
        await service.close()


async def test_overloaded_queue_does_not_accumulate():
    service = provider(lambda request: httpx.Response(200, json=completion()), queue_timeout=0.01)
    await service.slots.acquire()
    try:
        with pytest.raises(ExternalServiceError):
            await service.generate("rules", {}, TwinResponse)
    finally:
        service.slots.release()
        await service.close()


@pytest.mark.parametrize("url", ["file:///etc/passwd", "https://u:p@example.org/v1",
                                      "https://example.org/v1?key=x", "http://example.org/v1"])
def test_endpoint_validation(url):
    with pytest.raises(ValidationError):
        InferenceConfig(base_url=url)


async def test_local_is_default_and_unknown_provider_fails(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    service = create_provider()
    assert isinstance(service, LocalInference)
    await service.close()
    monkeypatch.setenv("AI_PROVIDER", "automatic-commercial-fallback")
    with pytest.raises(ValueError):
        create_provider()
