from datetime import datetime

from pydantic import BaseModel


class ScenarioCreate(BaseModel):
    title: str
    description: str
    context: str
    objective: str
    counterpart_role: str
    counterpart_goal: str
    counterpart_limits: str


class ScenarioResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    context: str
    objective: str
    counterpart_role: str
    counterpart_goal: str
    counterpart_limits: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True