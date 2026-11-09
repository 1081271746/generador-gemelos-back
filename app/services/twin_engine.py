from app.rpc.client import ServiceClients
from app.rpc.negotiation_pb2 import NegotiationContext
from app.schemas.analysis import TwinResponse


async def generate_twin_response(context: NegotiationContext, clients: ServiceClients) -> TwinResponse:
    return await clients.reply(context)
