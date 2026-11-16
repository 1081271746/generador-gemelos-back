"""Real official SDK over mock HTTP; no key, external API or user database."""
import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from groq import AsyncGroq
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select

from app.ai.analysis_engine import AnalysisEngine
from app.ai.groq import GroqService
from app.ai.model_manager import create_provider
from app.ai.twin_engine import TwinEngine
from app.core.config import Settings, settings
from app.core.errors import ExternalServiceError
from app.main import create_app
from app.models import Analysis
from app.rpc.ai_server import unpack_context
from app.schemas.analysis import AnalysisResult, TwinResponse
from app.schemas.message import MessageCreate
from app.schemas.negotiation import NegotiationCreate, NegotiationFinish
from app.services.analysis_service import analyze_negotiation
from app.services.conversation_service import process_user_message
from app.services.message_service import get_negotiation_messages
from app.services.negotiation_service import create_negotiation, finish_negotiation
from training.seed import examples


def completion(content='{"content":"Propongo 120","kind":"counteroffer"}',
               finish="stop", **message_fields):
    return {"id": "test", "object": "chat.completion", "created": 0, "model": "test",
            "choices": [{"index": 0, "finish_reason": finish,
                         "message": {"role": "assistant", "content": content, **message_fields}}]}


def service_with(handler=None, *, status=200, body=None, **configuration):
    handler = handler or (lambda request: httpx.Response(
        status, json=completion() if body is None else body))
    config = Settings(GROQ_API_KEY="test-only-placeholder", **configuration)
    client = AsyncGroq(api_key=config.GROQ_API_KEY, max_retries=0,
                       http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    redis = AsyncMock()
    redis.eval.return_value = 1
    return GroqService(config, client, redis)


async def test_official_sdk_initialization_and_close():
    service = GroqService(Settings(GROQ_API_KEY="test-only-placeholder"), redis_client=AsyncMock())
    assert isinstance(service.client, AsyncGroq)
    assert service.client.max_retries == 0
    assert service.client.timeout == 30
    await service.close()
    assert service.client.is_closed()
    service.redis.aclose.assert_awaited_once()


async def test_sdk_receives_prompts_schema_and_full_ordered_context():
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=completion())
    service = service_with(handler, GROQ_MODEL="configurable-model")
    context = list(examples())[0].context.model_dump()
    try:
        result = await TwinEngine(service).reply(context)
        assert result.kind == "counteroffer"
        request = captured[0]
        assert request["model"] == "configurable-model"
        assert "negotiation counterpart" in request["messages"][0]["content"]
        expected = context.copy()
        # Engine checks preserve the complete scenario, profile and message history.
        sent = json.loads(request["messages"][1]["content"])
        assert sent["messages"] == expected["messages"]
        assert sent["scenario"] == expected["scenario"]
        assert sent["profile"] == expected["profile"]
        assert request["response_format"]["json_schema"]["schema"] == TwinResponse.model_json_schema()
        assert request["response_format"]["json_schema"]["strict"] is False
        assert service.redis.eval.await_count == 1
    finally:
        await service.close()


async def test_analysis_existing_prompt_and_evidence_validation():
    example = list(examples())[1]
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=completion(json.dumps(example.expected)))
    service = service_with(handler)
    try:
        result = await AnalysisEngine(service).analyze(example.context.model_dump())
        assert isinstance(result, AnalysisResult)
        assert result.interpretation == "contextual_indicators"
        assert "exact quotes" in captured[0]["messages"][0]["content"]
    finally:
        await service.close()


@pytest.mark.parametrize("status,match", [
    (401, "credentials"), (403, "permission"), (429, "quota"),
    (400, "rejected"), (404, "rejected"), (422, "rejected"), (500, "unavailable"),
])
async def test_sdk_errors_are_controlled_and_not_retried(status, match):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "private-provider-detail"}})
    service = service_with(handler)
    try:
        with pytest.raises(ExternalServiceError, match=match) as error:
            await service.generate("test", {}, TwinResponse)
        assert "private-provider-detail" not in str(error.value)
        assert "test-only-placeholder" not in str(error.value)
        assert len(calls) == 1
    finally:
        await service.close()


@pytest.mark.parametrize("body", [
    {}, {"choices": []}, completion(None), completion(""), completion(" "),
    completion("not json"), completion('{"kind":"invented"}'),
    completion('{"content":"a","kind":"offer","extra":"forbidden"}'),
    completion(finish="length"), completion(finish="content_filter"),
    completion(refusal="blocked"),
])
async def test_empty_malformed_blocked_or_truncated_responses_are_rejected(body):
    service = service_with(body=body)
    try:
        with pytest.raises(ExternalServiceError):
            await service.generate("test", {}, TwinResponse)
    finally:
        await service.close()


@pytest.mark.parametrize("failure,match", [
    (httpx.ReadTimeout("private-provider-detail"), "timed out"),
    (httpx.ConnectError("private-provider-detail"), "connection failed"),
])
async def test_transport_errors(failure, match):
    def handler(request):
        raise failure
    service = service_with(handler)
    try:
        with pytest.raises(ExternalServiceError, match=match):
            await service.generate("test", {}, TwinResponse)
    finally:
        await service.close()


async def test_total_deadline_includes_quota_wait():
    service = service_with(GROQ_TIMEOUT_SECONDS=0.01)
    async def slow(*args):
        await asyncio.sleep(1)
    service.redis.eval.side_effect = slow
    try:
        with pytest.raises(ExternalServiceError, match="timed out"):
            await service.generate("test", {}, TwinResponse)
    finally:
        await service.close()


async def test_missing_key_does_not_contact_groq_or_redis():
    service = GroqService(Settings(GROQ_API_KEY="  "), redis_client=AsyncMock())
    try:
        assert service.client is None
        with pytest.raises(ExternalServiceError, match="not configured"):
            await service.generate("test", {}, TwinResponse)
        service.redis.eval.assert_not_awaited()
    finally:
        await service.close()


@pytest.mark.parametrize("quota_failure", ["over_limit", "redis_unavailable"])
async def test_quota_failure_never_calls_provider(quota_failure):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion())
    service = service_with(handler)
    if quota_failure == "over_limit":
        service.redis.eval.return_value = 11
    else:
        service.redis.eval.side_effect = RedisConnectionError("private-redis-detail")
    try:
        with pytest.raises(ExternalServiceError):
            await service.generate("test", {}, TwinResponse)
        assert not calls
    finally:
        await service.close()


async def test_oversized_utf8_context_rejected_before_quota():
    service = service_with()
    try:
        with pytest.raises(ExternalServiceError, match="context limit"):
            await service.generate("test", {"content": "ñ" * 100001}, TwinResponse)
        service.redis.eval.assert_not_awaited()
    finally:
        await service.close()


async def test_cancellation_propagates_without_fake_reply():
    service = service_with()
    service.redis.eval.side_effect = asyncio.CancelledError
    try:
        with pytest.raises(asyncio.CancelledError):
            await service.generate("test", {}, TwinResponse)
    finally:
        await service.close()


def test_environment_configuration(monkeypatch):
    for key, value in {"GROQ_API_KEY": "test-only-placeholder",
                       "GROQ_MODEL": "openai/gpt-oss-20b",
                       "GROQ_TIMEOUT_SECONDS": "12.5",
                       "GROQ_REQUESTS_PER_MINUTE": "7"}.items():
        monkeypatch.setenv(key, value)
    config = Settings()
    assert config.GROQ_MODEL == "openai/gpt-oss-20b"
    assert config.GROQ_TIMEOUT_SECONDS == 12.5
    assert config.GROQ_REQUESTS_PER_MINUTE == 7
    assert config.GROQ_API_KEY == "test-only-placeholder"
    assert config.GROQ_API_KEY not in repr(config)


@pytest.mark.parametrize("override", [
    {"GROQ_TIMEOUT_SECONDS": 0}, {"GROQ_TIMEOUT_SECONDS": float("nan")},
    {"GROQ_TIMEOUT_SECONDS": float("inf")}, {"GROQ_REQUESTS_PER_MINUTE": 0},
    {"GROQ_MODEL": " "},
])
def test_invalid_configuration_fails(override):
    config = Settings(SECRET_KEY="a" * 40, SERVICE_SECRET="b" * 40, **override)
    with pytest.raises(RuntimeError):
        config.validate_security()


async def test_groq_default_and_removed_gemini_never_falls_back(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    service = create_provider()
    assert isinstance(service, GroqService)
    await service.close()
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    with pytest.raises(ValueError, match="groq or local"):
        create_provider()


@pytest.mark.parametrize("key,configured", [("", False), ("test-only-placeholder", True)])
def test_health_preserves_contract_without_remote_probe(session_factory, monkeypatch, key, configured):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", key)
    clients = AsyncMock()
    application = create_app(session_factory, lambda: clients, start_dispatcher=False)
    with TestClient(application) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "database": "ok", "gemini_configured": False, "groq_configured": configured,
            "ai_provider": "groq", "ai_readiness": "not_probed",
        }
        if key:
            assert key not in response.text
        clients.reply.assert_not_awaited()
        clients.analyze.assert_not_awaited()


async def test_failed_groq_turn_retains_user_message_and_can_retry(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    service = service_with(status=429)
    class Clients:
        async def reply(self, context):
            return await TwinEngine(service).reply(unpack_context(context))
    data = MessageCreate(negotiation_id=negotiation.id, content="Offer 100", kind="offer")
    try:
        with pytest.raises(ExternalServiceError):
            await process_user_message(db, owner.id, data, Clients())
        db.refresh(negotiation)
        assert negotiation.processing_token is None
        messages = get_negotiation_messages(db, owner.id, negotiation.id)
        assert len(messages) == 1 and messages[0].sender_type == "user"
    finally:
        await service.close()
    service = service_with()
    try:
        result = await process_user_message(db, owner.id, data, Clients())
        assert len(result) == 2
        assert len(get_negotiation_messages(db, owner.id, negotiation.id)) == 2
    finally:
        await service.close()


async def test_invalid_groq_analysis_is_not_saved(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    clients = AsyncMock()
    clients.reply.return_value = TwinResponse(content="Propongo 120", kind="counteroffer")
    await process_user_message(db, owner.id, MessageCreate(
        negotiation_id=negotiation.id, content="Offer 100"), clients)
    finish_negotiation(db, owner.id, negotiation.id,
                       NegotiationFinish(status="completed", result="No agreement"))
    service = service_with(body=completion('{"invalid":"analysis"}'))
    class Clients:
        async def analyze(self, context):
            return await AnalysisEngine(service).analyze(unpack_context(context))
    try:
        with pytest.raises(ExternalServiceError):
            await analyze_negotiation(db, owner.id, negotiation.id, Clients())
        assert db.scalar(select(Analysis).where(Analysis.negotiation_id == negotiation.id)) is None
    finally:
        await service.close()
