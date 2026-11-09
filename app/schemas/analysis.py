from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DIMENSION_NAMES = ("assertiveness", "cooperation", "flexibility", "argumentation", "conflict_management")


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: int = Field(gt=0)
    quote: str = Field(min_length=1, max_length=1000)


class Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float = Field(ge=0, le=100)
    explanation: str = Field(min_length=1, max_length=3000)
    evidence: list[Evidence] = Field(min_length=1, max_length=20)


class Dimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assertiveness: Dimension
    cooperation: Dimension
    flexibility: Dimension
    argumentation: Dimension
    conflict_management: Dimension


class Exercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1, max_length=4000)
    scenario: str = Field(min_length=1, max_length=4000)


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=5000)
    strategies: list[str] = Field(max_length=20)
    strengths: list[str] = Field(max_length=20)
    improvement_areas: list[str] = Field(max_length=20)
    dimensions: Dimensions
    outcome: str = Field(min_length=1, max_length=5000)
    objective_evaluation: str = Field(min_length=1, max_length=5000)
    recommendations: list[str] = Field(min_length=1, max_length=20)
    exercises: list[Exercise] = Field(min_length=1, max_length=10)
    alerts: list[str] = Field(max_length=20)
    interpretation: Literal["contextual_indicators"] = "contextual_indicators"


class TwinResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=10000)
    kind: Literal["offer", "counteroffer", "argument", "concession"]


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    negotiation_id: int
    user_id: int
    payload: AnalysisResult
    created_at: datetime
