from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.time import utc_now


class Negotiation(Base):
    __tablename__ = "negotiations"
    user: Mapped["User"] = relationship(back_populates="negotiations")
    scenario: Mapped["Scenario"] = relationship(back_populates="negotiations")
    messages: Mapped[list["Message"]] = relationship(back_populates="negotiation", order_by="Message.id")
    analysis: Mapped["Analysis | None"] = relationship(back_populates="negotiation")

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
        default=utc_now,
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )