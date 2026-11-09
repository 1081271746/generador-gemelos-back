import argparse
import asyncio
import json
import signal

import grpc
from pydantic import ValidationError

from app.ai.gemini import GeminiService
from app.ai.prompts import TWIN_INSTRUCTIONS, ANALYSIS_INSTRUCTIONS
from app.core.config import settings
from app.core.errors import ExternalServiceError
from app.rpc import negotiation_pb2 as pb, negotiation_pb2_grpc as rpc
from app.rpc.transport import bind_server, require_service
from app.schemas.analysis import TwinResponse, AnalysisResult


def unpack_context(request: pb.NegotiationContext) -> dict:
    if request.user_id < 1 or request.negotiation_id < 1 or not request.messages:
        raise ValueError("Invalid negotiation context")
    scenario = json.loads(request.scenario_json)
    required = ("context", "objective", "counterpart_role", "counterpart_goal", "counterpart_limits")
    if not isinstance(scenario, dict) or not all(scenario.get(name) for name in required):
        raise ValueError("Incomplete scenario")
    return {
        "negotiation_id": request.negotiation_id, "scenario": scenario,
        "profile": json.loads(request.profile_json or "{}"), "result": request.result,
        "messages": [{"message_id": message.message_id, "sender_type": message.sender_type,
            "content": message.content, "kind": message.kind} for message in request.messages],
    }


class AIServicer(rpc.TwinNegotiationServiceServicer, rpc.NegotiationAnalysisServiceServicer):
    def __init__(self, gemini: GeminiService):
        self.gemini = gemini

    async def generate(self, request, context, scope, instructions, schema):
        user_id = await require_service(context, scope)
        if user_id != request.user_id:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "User scope mismatch")
        try:
            data = unpack_context(request)
            result = await self.gemini.generate(instructions, data, schema)
            return pb.JsonResult(json=result.model_dump_json())
        except (ValueError, ValidationError, TypeError):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid negotiation data")
        except ExternalServiceError:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "AI service unavailable")

    async def GenerateReply(self, request, context):
        return await self.generate(request, context, "twin", TWIN_INSTRUCTIONS, TwinResponse)

    async def AnalyzeNegotiation(self, request, context):
        return await self.generate(request, context, "analysis", ANALYSIS_INSTRUCTIONS, AnalysisResult)


async def serve(kind: str):
    settings.validate_security()
    gemini = GeminiService()
    server = grpc.aio.server(options=[("grpc.max_receive_message_length", 1024 * 1024)])
    servicer = AIServicer(gemini)
    target = settings.TWIN_GRPC_TARGET if kind == "twin" else settings.ANALYSIS_GRPC_TARGET
    if kind == "twin":
        rpc.add_TwinNegotiationServiceServicer_to_server(servicer, server)
    else:
        rpc.add_NegotiationAnalysisServiceServicer_to_server(servicer, server)
    bind_server(server, target)
    stopping = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, stopping.set)
    await server.start()
    try:
        await stopping.wait()
    finally:
        await server.stop(5)
        await gemini.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["twin", "analysis"])
    asyncio.run(serve(parser.parse_args().kind))
