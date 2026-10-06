from datetime import datetime

from pydantic import BaseModel


class NegotiationCreate(BaseModel):
    scenario_id: int


class NegotiationResponse(BaseModel):
    id: int
    user_id: int
    scenario_id: int
    status: str
    started_at: datetime
    ended_at: datetime | None

    class Config:
        from_attributes = True