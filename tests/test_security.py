import jwt
import pytest

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token, create_service_token, decode_service_token


@pytest.fixture(autouse=True)
def signing_keys(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "test-access-signing-material-only-00000")
    monkeypatch.setattr(settings, "SERVICE_SECRET", "test-service-signing-material-only-0000")


def test_argon2_and_invalid_hash():
    encoded = hash_password("A sufficiently long password")
    assert encoded.startswith("$argon2id$")
    assert verify_password("A sufficiently long password", encoded)
    assert not verify_password("incorrect", encoded)
    assert not verify_password("anything", "invalid")


def test_jwt_token_types_and_scopes():
    token = create_access_token({"sub": "1", "ver": 0})
    assert decode_access_token(token)["sub"] == "1"
    internal = create_service_token(1, "twin")
    assert decode_service_token(internal, "twin") == 1
    with pytest.raises(jwt.InvalidTokenError):
        decode_service_token(internal, "analysis")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(internal)
