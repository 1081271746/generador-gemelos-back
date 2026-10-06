from datetime import datetime

from pydantic import BaseModel


class MessageCreate(BaseModel):
    negotiation_id: int
    content: str


class MessageResponse(BaseModel):
    id: int
    negotiation_id: int
    sender_type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True