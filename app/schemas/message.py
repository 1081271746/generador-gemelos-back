from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    negotiation_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=10000)
    kind: Literal["offer", "counteroffer", "argument", "concession"] = "argument"
    request_id: UUID = Field(default_factory=uuid4)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negotiation_id: int
    sender_type: str
    content: str
    kind: str
    request_id: str | None
    created_at: datetime
