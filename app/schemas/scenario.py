from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ScenarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=5000)
    context: str = Field(min_length=1, max_length=10000)
    objective: str = Field(min_length=1, max_length=5000)
    counterpart_role: str = Field(min_length=1, max_length=150)
    counterpart_goal: str = Field(min_length=1, max_length=5000)
    counterpart_limits: str = Field(min_length=1, max_length=5000)


class ScenarioResponse(ScenarioCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
