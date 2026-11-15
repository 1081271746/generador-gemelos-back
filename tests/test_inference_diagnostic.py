import asyncio
import json

import httpx

from scripts.diagnose_inference import measure


async def test_stream_diagnostic_records_limits_without_saving_generated_text():
    events = [
        {"choices": [{"delta": {"content": '{"summary":"synthetic-private-text"}'}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": "length"}],
         "usage": {"prompt_tokens": 381, "completion_tokens": 64, "total_tokens": 445}},
    ]
    def handler(request):
        body = json.loads(request.content)
        assert body["max_tokens"] == 64 and body["stream"] is True
        return httpx.Response(200, text="".join("data: " + json.dumps(event) + "\n\n" for event in events)
                              + "data: [DONE]\n\n")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await measure(client, "http://127.0.0.1:8090/v1", "full", {}, 64, 1)
    assert result["status"] == "incomplete" and result["finish_reason"] == "length"
    assert result["usage"]["completion_tokens"] == 64
    assert not result["quality_evaluated"]
    assert "summary" in result["known_fields_observed"]
    assert "synthetic-private-text" not in json.dumps(result)


async def test_busy_server_does_not_become_a_performance_measurement():
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(503, text="do-not-record-body"))) as client:
        result = await measure(client, "http://127.0.0.1:8090/v1", "full", {}, 64, 1)
    assert result["status"] == "http_error" and result["first_content_seconds"] is None
    assert "approx_decode_tokens_per_second" not in result
    assert "do-not-record-body" not in json.dumps(result)


async def test_diagnostic_deadline_is_distinct_from_token_limit():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await measure(client, "http://127.0.0.1:8090/v1", "full", {}, 64, 0.01)
    assert result["status"] == "deadline"
    assert result["finish_reason"] is None
