import grpc
from pydantic import ValidationError

from app.core.config import settings
from app.core.errors import ExternalServiceError
from app.core.security import create_service_token
from app.rpc import negotiation_pb2 as pb, negotiation_pb2_grpc as rpc
from app.rpc.transport import create_channel
from app.schemas.analysis import TwinResponse, AnalysisResult


class ServiceClients:
    def __init__(self):
        self.twin_channel = create_channel(settings.TWIN_GRPC_TARGET)
        self.analysis_channel = create_channel(settings.ANALYSIS_GRPC_TARGET)
        self.event_channel = create_channel(settings.EVENT_GRPC_TARGET)
        self.twin = rpc.TwinNegotiationServiceStub(self.twin_channel)
        self.analysis = rpc.NegotiationAnalysisServiceStub(self.analysis_channel)
        self.events = rpc.NegotiationEventServiceStub(self.event_channel)

    async def invoke(self, method, request, scope, schema):
        try:
            metadata = [("authorization", f"Bearer {create_service_token(request.user_id, scope)}")]
            response = await method(request, metadata=metadata, timeout=settings.GRPC_TIMEOUT_SECONDS)
            return schema.model_validate_json(response.json)
        except (grpc.aio.AioRpcError, ValidationError):
            raise ExternalServiceError() from None

    async def reply(self, request: pb.NegotiationContext) -> TwinResponse:
        return await self.invoke(self.twin.GenerateReply, request, "twin", TwinResponse)

    async def analyze(self, request: pb.NegotiationContext) -> AnalysisResult:
        return await self.invoke(self.analysis.AnalyzeNegotiation, request, "analysis", AnalysisResult)

    async def publish(self, event_id: str, user_id: int) -> None:
        metadata = [("authorization", f"Bearer {create_service_token(user_id, 'events.publish')}")]
        response = await self.events.PublishEvent(pb.PublishRequest(event_id=event_id), metadata=metadata, timeout=5)
        if not response.accepted:
            raise ExternalServiceError("Event service rejected publication")

    def subscribe(self, token: str, negotiation_id: int = 0, after: int = 0):
        return self.events.SubscribeEvents(pb.Subscription(negotiation_id=negotiation_id, after_sequence=after),
            metadata=[("authorization", f"Bearer {token}")])

    async def close(self) -> None:
        await self.twin_channel.close()
        await self.analysis_channel.close()
        await self.event_channel.close()
