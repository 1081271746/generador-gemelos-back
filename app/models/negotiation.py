from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Negotiation(Base):
    __tablename__ = "negotiations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )


    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenarios.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
    )

    scenario_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    processing_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )