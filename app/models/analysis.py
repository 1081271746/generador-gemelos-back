from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    negotiation_id: Mapped[int] = mapped_column(ForeignKey("negotiations.id"), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NegotiatorProfile(Base):
    __tablename__ = "negotiator_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    sample_count: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
