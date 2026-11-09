import pytest
from pydantic import ValidationError

from app.schemas.message import MessageCreate
from app.schemas.user import UserCreate


def test_rejects_blank_and_oversized_messages():
    for content in ("  ", "a" * 10001):
        with pytest.raises(ValidationError):
            MessageCreate(negotiation_id=1, content=content)


def test_rejects_short_password_and_extra_fields():
    with pytest.raises(ValidationError):
        UserCreate(username="demo", email="demo@example.com", password="short")
    with pytest.raises(ValidationError):
        MessageCreate(negotiation_id=1, content="hello", sender_type="twin")
