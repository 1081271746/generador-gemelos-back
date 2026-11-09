from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NegotiationCreate(BaseModel):
    scenario_id: int = Field(gt=0)


class NegotiationFinish(BaseModel):
    status: Literal["completed", "cancelled"]
    result: str = Field(min_length=1, max_length=10000)


class NegotiationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    scenario_id: int
    status: str
    result: str | None
    scenario_snapshot: dict
    started_at: datetime
    ended_at: datetime | None
