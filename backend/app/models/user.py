from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._time import utcnow


class Role(StrEnum):
    VIEWER = "viewer"            # read-only
    IT_OPS = "it_ops"            # runs systems, handles incidents
    SYSTEM_OWNER = "system_owner"  # business owner of a system
    QA = "qa"                    # quality assurance, closes GxP incidents
    ADMIN = "admin"              # user and platform administration


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), default=Role.VIEWER)
    password_hash: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
