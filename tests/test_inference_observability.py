import asyncio
import json

import httpx
import pytest

from app.ai.inference.config import InferenceConfig
from app.ai.inference.local import LocalInference
from app.ai.inference.schema import structural_schema
from app.ai.inference.telemetry import InferenceFailure
from app.schemas.analysis import AnalysisResult, TwinResponse
from tests.test_local_inference import completion


def service(handler, events, **kwargs):
    return LocalInference(InferenceConfig(**kwargs),
                          httpx.AsyncClient(transport=httpx.MockTransport(handler)), observer=events.append)


def test_structural_schema_preserves_all_fields_and_numeric_scales():
    original = AnalysisResult.model_json_schema()
    result = structural_schema(original)
    assert result["required"] == original["required"]
    assert set(result["properties"]) == set(original["properties"])
    assert result["additionalProperties"] is False
    assert set(result["$defs"]["Dimensions"]["properties"]) == set(original["$defs"]["Dimensions"]["properties"])
    assert result["$defs"]["Dimension"]["properties"]["score"]["maximum"] == 100
    assert result["$defs"]["Evidence"]["required"] == ["message_id", "quote"]
    assert "maxLength" not in result["properties"]["summary"]
    assert original["properties"]["summary"]["maxLength"] == 5000
    # An actual property called maxLength must survive.
    assert structural_schema({"properties": {"maxLength": {"type": "string", "maxLength": 3}}}) == {
        "properties": {"maxLength": {"type": "string"}}}


async def test_structural_grammar_does_not_weaken_final_validation():
    events = []
    def handler(request):
        schema = json.loads(request.content)["response_format"]["json_schema"]["schema"]
        assert "maxLength" not in schema["properties"]["content"]
        return httpx.Response(200, json=completion({"content": "x" * 10001, "kind": "offer"}))
    provider = service(handler, events, schema_mode="structural")
    try:
        with pytest.raises(InferenceFailure) as error:
            await provider.generate("rules", {}, TwinResponse)
        assert error.value.code == "schema_invalid"
        assert events[-1]["success"] is False
    finally:
        await provider.close()


@pytest.mark.parametrize("data,code", [
    (completion(finish="length"), "output_limit"),
    ({"choices": []}, "protocol_invalid"),
    (completion({"content": "", "kind": "offer"}), "schema_invalid"),
])
async def test_failure_codes_are_not_collapsed(data, code):
    events = []
    provider = service(lambda request: httpx.Response(200, json=data), events)
    try:
        with pytest.raises(InferenceFailure) as error:
            await provider.generate("private-system", {"private": "do-not-log"}, TwinResponse)
        assert error.value.code == code
        assert events[-1]["error_code"] == code
        assert "do-not-log" not in json.dumps(events)
        assert "private-system" not in json.dumps(events)
    finally:
        await provider.close()


async def test_metrics_capture_safe_usage_and_redact_untrusted_finish_reason():
    events = []
    data = completion()
    data["usage"] = {"prompt_tokens": 379, "completion_tokens": 64, "other_secret": "never-log"}
    provider = service(lambda request: httpx.Response(200, json=data), events)
    try:
        await provider.generate("private", {}, TwinResponse)
        assert events[-1]["prompt_tokens"] == 379 and events[-1]["completion_tokens"] == 64
        assert events[-1]["success"] is True
        data["choices"][0]["finish_reason"] = "arbitrary-sensitive-value"
        with pytest.raises(InferenceFailure):
            await provider.generate("private", {}, TwinResponse)
        assert events[-1]["finish_reason"] == "unknown"
        assert "arbitrary-sensitive-value" not in json.dumps(events)
        assert "never-log" not in json.dumps(events)
    finally:
        await provider.close()


async def test_queue_and_generation_deadline_have_separate_codes():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=completion())
    events = []
    provider = service(handler, events, queue_timeout=0.01, timeout=0.01)
    try:
        await provider.slots.acquire()
        with pytest.raises(InferenceFailure) as error:
            await provider.generate("rules", {}, TwinResponse)
        assert error.value.code == "queue_timeout"
        provider.slots.release()
        with pytest.raises(InferenceFailure) as error:
            await provider.generate("rules", {}, TwinResponse)
        assert error.value.code == "generation_timeout"
        assert provider.slots._value == 1
    finally:
        await provider.close()


async def test_cancellation_releases_slot_and_emits_no_response():
    started = asyncio.Event()
    async def handler(request):
        started.set()
        await asyncio.sleep(10)
    events = []
    provider = service(handler, events)
    try:
        task = asyncio.create_task(provider.generate("rules", {}, TwinResponse))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert events[-1]["error_code"] == "cancelled"
        assert provider.slots._value == 1
    finally:
        await provider.close()
