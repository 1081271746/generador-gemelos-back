import json

import grpc
import httpx
import pytest

from app.ai.inference.config import InferenceConfig
from app.ai.inference.local import LocalInference
from app.core.security import create_service_token
from app.rpc import negotiation_pb2 as pb, negotiation_pb2_grpc as rpc
from app.rpc.ai_server import AIServicer
from training.seed import examples


async def test_actual_grpc_uses_self_hosted_http_contract_and_preserves_auth():
    def handler(request):
        body = json.loads(request.content)
        assert body["response_format"]["type"] == "json_schema"
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": '{"content":"Propongo 95 por caja.","kind":"counteroffer"}'}}]})
    provider = LocalInference(InferenceConfig(), httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    server = grpc.aio.server()
    rpc.add_TwinNegotiationServiceServicer_to_server(AIServicer(provider), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    data = next(examples()).context
    request = pb.NegotiationContext(user_id=1, negotiation_id=1,
        scenario_json=data.scenario.model_dump_json(),
        messages=[pb.ConversationMessage(**item.model_dump()) for item in data.messages])
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = rpc.TwinNegotiationServiceStub(channel)
            with pytest.raises(grpc.aio.AioRpcError) as error:
                await stub.GenerateReply(request, timeout=2)
            assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED
            metadata = [("authorization", f"Bearer {create_service_token(1, 'twin')}")]
            result = await stub.GenerateReply(request, metadata=metadata, timeout=2)
            assert json.loads(result.json)["content"] == "Propongo 95 por caja."
    finally:
        await server.stop(0)
        await provider.close()
