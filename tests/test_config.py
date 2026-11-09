import pytest

from app.core.config import Settings


def test_rejects_missing_secrets():
    with pytest.raises(RuntimeError):
        Settings(SECRET_KEY="", SERVICE_SECRET="").validate_security()


def test_rejects_equal_secrets():
    with pytest.raises(RuntimeError):
        Settings(SECRET_KEY="a" * 40, SERVICE_SECRET="a" * 40).validate_security()
