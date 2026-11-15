from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from app.core.errors import ExternalServiceError
from app.schemas.analysis import AnalysisResult, DIMENSION_NAMES


class ContextMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: int = Field(gt=0)
    sender_type: Literal["user", "twin"]
    content: str = Field(min_length=1, max_length=10000)
    kind: Literal["", "offer", "counteroffer", "argument", "concession"] = ""


class ScenarioContext(BaseModel):
    model_config = ConfigDict(extra="ignore")
    context: str = Field(min_length=1, max_length=10000)
    objective: str = Field(min_length=1, max_length=5000)
    counterpart_role: str = Field(min_length=1, max_length=150)
    counterpart_goal: str = Field(min_length=1, max_length=5000)
    counterpart_limits: str = Field(min_length=1, max_length=5000)


class NegotiationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    negotiation_id: int = Field(gt=0)
    scenario: ScenarioContext
    profile: dict = Field(default_factory=dict)
    result: str = Field(default="", max_length=10000)
    messages: list[ContextMessage] = Field(min_length=1, max_length=500)

    def checked(self):
        ids = [message.message_id for message in self.messages]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate message identifiers")
        return self.model_dump()


def validate_analysis(result: AnalysisResult, context: dict) -> AnalysisResult:
    messages = {message["message_id"]: message["content"]
                for message in context["messages"] if message["sender_type"] == "user"}
    for name in DIMENSION_NAMES:
        for evidence in getattr(result.dimensions, name).evidence:
            if evidence.message_id not in messages or evidence.quote not in messages[evidence.message_id]:
                raise ExternalServiceError("AI returned unverifiable evidence")
    return result
