"""Bounded HTTP client for a self-hosted llama.cpp server, not a paid API."""
import asyncio
import json
import logging
import time

import httpx
from pydantic import ValidationError

from app.ai.inference.base import Result
from app.ai.inference.config import InferenceConfig
from app.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)


class LocalInference:
    def __init__(self, config: InferenceConfig | None = None, http_client=None):
        self.config = config or InferenceConfig.from_env()
        self.http = http_client or httpx.AsyncClient(
            timeout=self.config.timeout, follow_redirects=False, trust_env=False,
            limits=httpx.Limits(max_connections=self.config.concurrency))
        self.slots = asyncio.Semaphore(self.config.concurrency)

    async def generate(self, instructions: str, context: dict, schema: type[Result]) -> Result:
        serialized = json.dumps(context, ensure_ascii=False, allow_nan=False)
        if len(serialized.encode()) > self.config.max_context_bytes:
            raise ExternalServiceError("AI context too large; shorten the negotiation")
        acquired = False
        started = time.monotonic()
        success = False
        try:
            await asyncio.wait_for(self.slots.acquire(), timeout=self.config.queue_timeout)
            acquired = True
            body = {
                "model": self.config.model,
                "messages": [{"role": "system", "content": instructions},
                             {"role": "user", "content": serialized}],
                "temperature": 0.2, "max_tokens": self.config.max_tokens, "stream": False,
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": schema.__name__, "strict": True, "schema": schema.model_json_schema()}},
            }
            async with asyncio.timeout(self.config.timeout):
                async with self.http.stream("POST", self.config.base_url.rstrip("/") + "/chat/completions",
                                            json=body) as response:
                    if response.status_code != 200:
                        raise ExternalServiceError("Local AI unavailable or context rejected")
                    payload = bytearray()
                    async for chunk in response.aiter_bytes():
                        payload.extend(chunk)
                        if len(payload) > self.config.max_response_bytes:
                            raise ExternalServiceError("Local AI response too large")
            data = json.loads(payload)
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ExternalServiceError("Local AI response incomplete")
            result = schema.model_validate_json(choice["message"]["content"])
            success = True
            return result
        except (httpx.HTTPError, TimeoutError, ValidationError, ValueError, KeyError, IndexError, TypeError):
            raise ExternalServiceError("Local AI failed or returned invalid JSON") from None
        finally:
            if acquired:
                self.slots.release()
            # Never log prompts, messages, profiles, responses or credentials.
            logger.info("local_ai completed=%s duration_ms=%d", success, (time.monotonic() - started) * 1000)

    async def close(self):
        await self.http.aclose()
