"""Live model -> authenticated gRPC smoke, isolated keys, synthetic context only."""
import argparse
import asyncio
import json
from pathlib import Path
from secrets import token_urlsafe
import time

import grpc

from app.ai.inference.config import InferenceConfig
from app.ai.inference.local import LocalInference
from app.core.config import settings
from app.core.security import create_service_token
from app.rpc import negotiation_pb2 as pb, negotiation_pb2_grpc as rpc
from app.rpc.ai_server import AIServicer
from app.schemas.analysis import TwinResponse
from training.seed import examples


async def smoke(base_url):
    # Isolated process: never use a production identity or persist these keys.
    settings.SERVICE_SECRET = token_urlsafe(48)
    provider = LocalInference(InferenceConfig(base_url=base_url, timeout=240, max_tokens=512))
    server = grpc.aio.server()
    rpc.add_TwinNegotiationServiceServicer_to_server(AIServicer(provider), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    data = next(examples()).context
    request = pb.NegotiationContext(user_id=1, negotiation_id=1,
        scenario_json=data.scenario.model_dump_json(),
        messages=[pb.ConversationMessage(**item.model_dump()) for item in data.messages])
    started = time.monotonic()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = rpc.TwinNegotiationServiceStub(channel)
            try:
                await stub.GenerateReply(request, timeout=5)
                raise RuntimeError("Unauthenticated gRPC unexpectedly succeeded")
            except grpc.aio.AioRpcError as error:
                if error.code() != grpc.StatusCode.UNAUTHENTICATED:
                    raise
            metadata = [("authorization", f"Bearer {create_service_token(1, 'twin')}")]
            result = await stub.GenerateReply(
                request, metadata=metadata, timeout=250)
            reply = TwinResponse.model_validate_json(result.json)
            return {"status": "completed",
                    "source": "real base Qwen2.5-1.5B-Instruct Q4_K_M; not fine-tuned",
                    "authenticated_grpc": True, "seconds": round(time.monotonic() - started, 3),
                    "reply": reply.model_dump(), "expert_quality_verified": False}
    except grpc.aio.AioRpcError as error:
        return {"status": "failed", "grpc_status": error.code().name,
                "seconds": round(time.monotonic() - started, 3),
                "expert_quality_verified": False}
    finally:
        await server.stop(0)
        await provider.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8090/v1")
    parser.add_argument("--output", default="generated-artifacts/live-grpc.json")
    args = parser.parse_args()
    result = asyncio.run(smoke(args.base_url))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "completed" else 1)
