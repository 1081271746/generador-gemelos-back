from unittest.mock import AsyncMock

import grpc
import pytest

from app.core.security import create_service_token
from app.rpc import negotiation_pb2 as pb, negotiation_pb2_grpc as rpc
from app.rpc.ai_server import AIServicer
from app.schemas.analysis import TwinResponse


async def test_real_grpc_ai_authentication_and_validated_reply(scenario):
    from app.schemas.scenario import ScenarioCreate
    provider = AsyncMock()
    provider.generate.return_value = TwinResponse(content="I offer 120", kind="offer")
    server = grpc.aio.server()
    rpc.add_TwinNegotiationServiceServicer_to_server(AIServicer(provider), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = rpc.TwinNegotiationServiceStub(channel)
            request = pb.NegotiationContext(user_id=scenario.user_id, negotiation_id=1,
                scenario_json=ScenarioCreate.model_validate(scenario, from_attributes=True).model_dump_json(),
                messages=[pb.ConversationMessage(message_id=1, sender_type="user", content="Offer")])
            with pytest.raises(grpc.aio.AioRpcError) as error:
                await stub.GenerateReply(request, timeout=2)
            assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED
            metadata = [("authorization", f"Bearer {create_service_token(scenario.user_id, 'twin')}")]
            result = await stub.GenerateReply(request, metadata=metadata, timeout=2)
            assert TwinResponse.model_validate_json(result.json).kind == "offer"
            request.user_id += 1
            with pytest.raises(grpc.aio.AioRpcError) as error:
                await stub.GenerateReply(request, metadata=metadata, timeout=2)
            assert error.value.code() == grpc.StatusCode.PERMISSION_DENIED
    finally:
        await server.stop(0)
