from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: str
    sequence: int
    negotiation_id: int
    event_type: str
    payload: dict
    created_at: datetime
