from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.time import utc_now


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scenarios: Mapped[list["Scenario"]] = relationship(back_populates="user")
    negotiations: Mapped[list["Negotiation"]] = relationship(back_populates="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
    )