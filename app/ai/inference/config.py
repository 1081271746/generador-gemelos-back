import os
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InferenceConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    base_url: str = "http://127.0.0.1:8090/v1"
    model: str = "negotiation-local"
    timeout: float = Field(default=30, gt=0, le=600)
    max_tokens: int = Field(default=2048, ge=64, le=8192)
    max_context_bytes: int = Field(default=24000, ge=1000, le=200000)
    max_response_bytes: int = Field(default=131072, ge=1024, le=1048576)
    concurrency: int = Field(default=1, ge=1, le=8)
    queue_timeout: float = Field(default=2, gt=0, le=30)
    schema_mode: Literal["full", "structural"] = "full"

    @model_validator(mode="after")
    def validate_endpoint(self):
        url = urlsplit(self.base_url)
        if (url.scheme not in ("http", "https") or not url.hostname or url.username
                or url.password or url.query or url.fragment):
            raise ValueError("AI_BASE_URL must be an HTTP endpoint without credentials, query or fragment")
        if url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Remote inference requires HTTPS")
        return self

    @classmethod
    def from_env(cls):
        mapping = {
            "base_url": "AI_BASE_URL", "model": "AI_MODEL", "timeout": "AI_TIMEOUT_SECONDS",
            "max_tokens": "AI_MAX_TOKENS", "max_context_bytes": "AI_MAX_CONTEXT_BYTES",
            "concurrency": "AI_CONCURRENCY", "queue_timeout": "AI_QUEUE_TIMEOUT_SECONDS",
            "schema_mode": "AI_SCHEMA_MODE",
        }
        return cls(**{key: os.environ[name] for key, name in mapping.items() if name in os.environ})
