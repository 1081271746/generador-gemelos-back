import ipaddress
from pathlib import Path

import grpc
import jwt

from app.core.config import settings
from app.core.security import decode_service_token


def local_target(target: str) -> bool:
    host = target.rsplit(":", 1)[0].strip("[]")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def create_channel(target: str) -> grpc.aio.Channel:
    options = [("grpc.max_receive_message_length", 1024 * 1024), ("grpc.max_send_message_length", 1024 * 1024)]
    if settings.GRPC_TLS_CA:
        credentials = grpc.ssl_channel_credentials(root_certificates=Path(settings.GRPC_TLS_CA).read_bytes())
        return grpc.aio.secure_channel(target, credentials, options=options)
    if not local_target(target):
        raise RuntimeError("Non-loopback gRPC connections require TLS")
    return grpc.aio.insecure_channel(target, options=options)


def bind_server(server: grpc.aio.Server, address: str) -> int:
    if settings.GRPC_TLS_CERT and settings.GRPC_TLS_KEY:
        credentials = grpc.ssl_server_credentials([(
            Path(settings.GRPC_TLS_KEY).read_bytes(), Path(settings.GRPC_TLS_CERT).read_bytes()
        )])
        return server.add_secure_port(address, credentials)
    if not local_target(address):
        raise RuntimeError("Non-loopback gRPC listeners require TLS")
    return server.add_insecure_port(address)


def bearer(context) -> str:
    metadata = dict(context.invocation_metadata())
    value = metadata.get("authorization", "")
    if not value.startswith("Bearer "):
        raise jwt.InvalidTokenError()
    return value[7:]


async def require_service(context, scope: str) -> int:
    try:
        return decode_service_token(bearer(context), scope)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid service credentials")
