"""Bounded HTTP client for a self-hosted llama.cpp server, not a paid API."""
import asyncio
import json
import logging
import time

import httpx
from pydantic import ValidationError

from app.ai.inference.base import Result
from app.ai.inference.config import InferenceConfig
from app.ai.inference.schema import structural_schema
from app.ai.inference.telemetry import GenerationMetrics, InferenceFailure, safe_token_count

logger = logging.getLogger(__name__)


class LocalInference:
    def __init__(self, config: InferenceConfig | None = None, http_client=None, observer=None):
        self.config = config or InferenceConfig.from_env()
        self.http = http_client or httpx.AsyncClient(
            timeout=self.config.timeout, follow_redirects=False, trust_env=False,
            limits=httpx.Limits(max_connections=self.config.concurrency))
        self.slots = asyncio.Semaphore(self.config.concurrency)
        self.observer = observer

    async def generate(self, instructions: str, context: dict, schema: type[Result]) -> Result:
        acquired = False
        started = time.monotonic()
        metrics = GenerationMetrics(schema_mode=self.config.schema_mode)
        try:
            serialized = json.dumps(context, ensure_ascii=False, allow_nan=False)
            if len(serialized.encode()) > self.config.max_context_bytes:
                raise InferenceFailure("input_too_large", "AI context too large; shorten the negotiation")
            try:
                await asyncio.wait_for(self.slots.acquire(), timeout=self.config.queue_timeout)
            except TimeoutError:
                raise InferenceFailure("queue_timeout", "Local AI queue is full") from None
            acquired = True
            metrics.queue_ms = round((time.monotonic() - started) * 1000)
            response_schema = schema.model_json_schema()
            if self.config.schema_mode == "structural":
                response_schema = structural_schema(response_schema)
            body = {
                "model": self.config.model,
                "messages": [{"role": "system", "content": instructions},
                             {"role": "user", "content": serialized}],
                "temperature": 0.2, "max_tokens": self.config.max_tokens, "stream": False,
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": schema.__name__, "strict": True, "schema": response_schema}},
            }
            async with asyncio.timeout(self.config.timeout):
                async with self.http.stream("POST", self.config.base_url.rstrip("/") + "/chat/completions",
                                            json=body) as response:
                    metrics.http_status = response.status_code
                    if response.status_code != 200:
                        raise InferenceFailure("http_error", "Local AI unavailable or context rejected")
                    payload = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        payload.extend(chunk)
                        if len(payload) > self.config.max_response_bytes:
                            raise InferenceFailure("response_too_large", "Local AI response too large")
            data = json.loads(payload)
            usage = data.get("usage") or {}
            metrics.prompt_tokens = safe_token_count(usage.get("prompt_tokens"))
            metrics.completion_tokens = safe_token_count(usage.get("completion_tokens"))
            choice = data["choices"][0]
            reason = choice.get("finish_reason")
            metrics.finish_reason = reason if reason in {"stop", "length", "content_filter", "tool_calls"} else "unknown"
            if choice.get("finish_reason") != "stop":
                raise InferenceFailure("output_limit" if reason == "length" else "protocol_invalid",
                                       "Local AI response incomplete")
            try:
                result = schema.model_validate_json(choice["message"]["content"])
            except ValidationError:
                raise InferenceFailure("schema_invalid", "Local AI failed full output validation") from None
            metrics.success = True
            return result
        except InferenceFailure as error:
            metrics.error_code = error.code
            raise
        except asyncio.CancelledError:
            metrics.error_code = "cancelled"
            raise
        except (TimeoutError, httpx.TimeoutException):
            metrics.error_code = "generation_timeout"
            raise InferenceFailure("generation_timeout", "Local AI generation deadline exceeded") from None
        except httpx.HTTPError:
            metrics.error_code = "transport_error"
            raise InferenceFailure("transport_error", "Local AI transport failed") from None
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            metrics.error_code = "protocol_invalid"
            raise InferenceFailure("protocol_invalid", "Local AI returned an invalid protocol response") from None
        finally:
            if acquired:
                self.slots.release()
            metrics.duration_ms = round((time.monotonic() - started) * 1000)
            # Only a fixed set of scalar fields, never raw finish reasons,
            # prompts, exception strings, responses or credentials.
            logger.info("local_ai_metrics %s", json.dumps(metrics.as_dict()))
            if self.observer is not None:
                try:
                    self.observer(metrics.as_dict())
                except Exception:
                    logger.warning("local_ai_metrics observer_failed")

    async def close(self):
        await self.http.aclose()
