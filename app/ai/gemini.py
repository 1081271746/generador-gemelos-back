import json
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, settings
from app.core.errors import ExternalServiceError


Result = TypeVar("Result", bound=BaseModel)


class GeminiService:
    def __init__(self, config: Settings = settings, http_client: httpx.AsyncClient | None = None, redis_client: Redis | None = None):
        self.config = config
        self.http = http_client or httpx.AsyncClient(timeout=config.GEMINI_TIMEOUT_SECONDS)
        self.redis = redis_client or Redis.from_url(config.REDIS_URL, decode_responses=True)

    async def reserve_quota(self) -> None:
        key = f"gemini:quota:{self.config.GEMINI_MODEL}:{int(time.time() // 60)}"
        count = await self.redis.eval(
            "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],65) end; return n",
            1, key)
        if count > self.config.GEMINI_REQUESTS_PER_MINUTE:
            raise ExternalServiceError("Configured AI rate limit reached; retry later")

    async def generate(self, instructions: str, context: dict, schema: type[Result]) -> Result:
        if not self.config.GEMINI_API_KEY:
            raise ExternalServiceError("Gemini is not configured")
        serialized = json.dumps(context, ensure_ascii=False, default=str)
        if len(serialized) > 200000:
            raise ExternalServiceError("Conversation exceeds configured AI context limit")
        try:
            await self.reserve_quota()
            response = await self.http.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.GEMINI_MODEL}:generateContent",
                headers={"x-goog-api-key": self.config.GEMINI_API_KEY},
                json={
                    "systemInstruction": {"parts": [{"text": instructions}]},
                    "contents": [{"role": "user", "parts": [{"text": serialized}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "responseJsonSchema": schema.model_json_schema(),
                    },
                },
            )
            if response.status_code == 429:
                raise ExternalServiceError("Gemini quota exhausted; retry later")
            if response.status_code != 200:
                raise ExternalServiceError()
            data = response.json()
            candidate = data["candidates"][0]
            if candidate.get("finishReason") != "STOP":
                raise ExternalServiceError("AI response blocked or incomplete")
            text = "".join(part.get("text", "") for part in candidate["content"]["parts"] if not part.get("thought"))
            return schema.model_validate_json(text)
        except (httpx.HTTPError, RedisError, ValidationError, ValueError, KeyError, IndexError, TypeError):
            raise ExternalServiceError("AI communication failed or returned an invalid response") from None

    async def close(self) -> None:
        await self.http.aclose()
        await self.redis.aclose()
