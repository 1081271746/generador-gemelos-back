from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("negotiation_id", "request_id", "sender_type"),)

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    negotiation_id: Mapped[int] = mapped_column(
        ForeignKey("negotiations.id"),
        nullable=False,
        index=True,
    )

    sender_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(30), default="argument", server_default="argument")
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )