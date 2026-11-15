from app.ai.inference.base import InferenceProvider
from app.ai.prompts import ANALYSIS_INSTRUCTIONS
from app.ai.response_validator import NegotiationInput, validate_analysis
from app.schemas.analysis import AnalysisResult


class AnalysisEngine:
    def __init__(self, provider: InferenceProvider):
        self.provider = provider

    async def analyze(self, context: dict) -> AnalysisResult:
        data = NegotiationInput.model_validate(context).checked()
        if not any(message["sender_type"] == "user" for message in data["messages"]):
            raise ValueError("Analysis requires user messages")
        result = await self.provider.generate(ANALYSIS_INSTRUCTIONS, data, AnalysisResult)
        return validate_analysis(result, data)
