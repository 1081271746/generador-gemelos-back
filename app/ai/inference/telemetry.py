from dataclasses import asdict, dataclass
from typing import Literal

from app.core.errors import ExternalServiceError

FailureCode = Literal[
    "input_too_large", "queue_timeout", "generation_timeout", "http_error",
    "transport_error", "response_too_large", "output_limit", "schema_invalid", "protocol_invalid", "cancelled",
]


class InferenceFailure(ExternalServiceError):
    """Stable internal code. HTTP/gRPC public contracts remain unchanged."""
    def __init__(self, code: FailureCode, message: str):
        self.code = code
        super().__init__(message)


@dataclass
class GenerationMetrics:
    success: bool = False
    error_code: str | None = None
    duration_ms: int = 0
    queue_ms: int = 0
    http_status: int | None = None
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    schema_mode: str = "full"

    def as_dict(self):
        return asdict(self)


def safe_token_count(value):
    return value if type(value) is int and 0 <= value <= 1000000 else None
