from app.ai.inference.base import InferenceProvider
from app.ai.prompts import TWIN_INSTRUCTIONS
from app.ai.response_validator import NegotiationInput
from app.ai.policy import validate_numeric_limits, numeric_bounds
from app.schemas.analysis import TwinResponse


class TwinEngine:
    def __init__(self, provider: InferenceProvider):
        self.provider = provider

    async def reply(self, context: dict) -> TwinResponse:
        data = NegotiationInput.model_validate(context).checked()
        if data["messages"][-1]["sender_type"] != "user":
            raise ValueError("A twin turn requires a final user message")
        instructions = TWIN_INSTRUCTIONS
        if numeric_bounds(data["scenario"]["counterpart_limits"]):
            instructions += """
Cuando existan límites numéricos explícitos de precio, salario o descuento,
no repitas cifras no viables ni números de otras magnitudes en tu respuesta.
Propón únicamente una cifra monetaria o porcentual dentro del límite.
No reveles el límite privado como tal. Si falta información, pide una aclaración.
"""
        result = await self.provider.generate(instructions, data, TwinResponse)
        validate_numeric_limits(result.content, data["scenario"]["counterpart_limits"])
        return result
