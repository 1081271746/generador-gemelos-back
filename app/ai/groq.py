"""Groq transport for the existing inference contract; never falls back."""
import asyncio
import json
import time
from typing import TypeVar

from groq import (
    AsyncGroq, APIConnectionError, APIResponseValidationError, APIStatusError,
    APITimeoutError, AuthenticationError, PermissionDeniedError, RateLimitError,
)
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, settings
from app.core.errors import ExternalServiceError


Result = TypeVar("Result", bound=BaseModel)


class GroqService:
    def __init__(self, config: Settings = settings, client: AsyncGroq | None = None,
                 redis_client: Redis | None = None):
        self.config = config
        self.client = client
        if self.client is None and config.GROQ_API_KEY.strip():
            self.client = AsyncGroq(
                api_key=config.GROQ_API_KEY, timeout=config.GROQ_TIMEOUT_SECONDS,
                max_retries=0,
            )
        self.redis = redis_client if redis_client is not None else Redis.from_url(
            config.REDIS_URL, decode_responses=True,
            socket_connect_timeout=config.GROQ_TIMEOUT_SECONDS,
            socket_timeout=config.GROQ_TIMEOUT_SECONDS,
        )

    async def reserve_quota(self) -> None:
        # Same atomic Redis mechanism as before, with a provider-specific namespace.
        key = f"groq:quota:{self.config.GROQ_MODEL}:{int(time.time() // 60)}"
        count = await self.redis.eval(
            "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],65) end; return n",
            1, key,
        )
        if count > self.config.GROQ_REQUESTS_PER_MINUTE:
            raise ExternalServiceError("Configured AI rate limit reached; retry later")

    async def generate(self, instructions: str, context: dict, schema: type[Result]) -> Result:
        if not self.config.GROQ_API_KEY.strip() or self.client is None:
            raise ExternalServiceError("Groq is not configured")
        try:
            serialized = json.dumps(context, ensure_ascii=False, default=str)
            if len(serialized.encode("utf-8")) > 200000:
                raise ExternalServiceError("Conversation exceeds configured AI context limit")
            async with asyncio.timeout(self.config.GROQ_TIMEOUT_SECONDS):
                await self.reserve_quota()
                response = await self.client.chat.completions.create(
                    model=self.config.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": instructions},
                        {"role": "user", "content": serialized},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema.__name__,
                            # Preserve optional fields/dictionaries in existing schemas.
                            # Full local Pydantic and engine validation remains mandatory.
                            "strict": False, "schema": schema.model_json_schema(),
                        },
                    },
                    max_completion_tokens=8192,
                )
                choice = response.choices[0]
                if choice.finish_reason != "stop" or getattr(choice.message, "refusal", None):
                    raise ExternalServiceError("AI response blocked or incomplete")
                content = choice.message.content
                if not isinstance(content, str) or not content.strip():
                    raise ExternalServiceError("Groq returned an empty response")
                return schema.model_validate_json(content)
        except (AuthenticationError, PermissionDeniedError):
            raise ExternalServiceError("Groq credentials are invalid or lack permission") from None
        except (APITimeoutError, TimeoutError):
            raise ExternalServiceError("Groq request timed out") from None
        except RateLimitError:
            raise ExternalServiceError("Groq quota exhausted; retry later") from None
        except APIConnectionError:
            raise ExternalServiceError("Groq connection failed") from None
        except APIStatusError:
            raise ExternalServiceError("Groq rejected the request or is unavailable") from None
        except RedisError:
            raise ExternalServiceError("AI quota service unavailable") from None
        except (APIResponseValidationError, ValidationError, ValueError,
                KeyError, IndexError, TypeError, AttributeError):
            raise ExternalServiceError("AI returned an invalid response") from None

    async def close(self) -> None:
        try:
            if self.client is not None:
                await self.client.close()
        finally:
            await self.redis.aclose()
