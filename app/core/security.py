from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(data: dict) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        **data, "iat": now, "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid4()), "iss": "negotiation-api", "aud": "negotiation-client", "type": "access",
    }, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"],
        issuer="negotiation-api", audience="negotiation-client",
        options={"require": ["exp", "iat", "sub", "ver", "jti", "type"]})


def create_service_token(user_id: int, scope: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(user_id), "scope": scope, "type": "service", "iat": now,
        "exp": now + timedelta(minutes=2), "iss": "negotiation-api", "aud": "negotiation-internal",
    }, settings.SERVICE_SECRET, algorithm="HS256")


def decode_service_token(token: str, scope: str) -> int:
    payload = jwt.decode(token, settings.SERVICE_SECRET, algorithms=["HS256"],
        issuer="negotiation-api", audience="negotiation-internal",
        options={"require": ["exp", "iat", "sub", "scope", "type"]})
    if payload["type"] != "service" or payload["scope"] != scope or int(payload["sub"]) < 1:
        raise jwt.InvalidTokenError("Invalid service scope")
    return int(payload["sub"])
