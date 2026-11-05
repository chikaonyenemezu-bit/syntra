from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemStatus(StrEnum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class System(Base):
    """A computerised system in the landscape (system inventory entry)."""

    __tablename__ = "systems"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g. MES-01
    name: Mapped[str] = mapped_column(String(128))
    system_type: Mapped[str] = mapped_column(String(32))  # MES, LIMS, ERP, INTEGRATION
    description: Mapped[str] = mapped_column(String(512), default="")
    gxp_relevant: Mapped[bool] = mapped_column(Boolean, default=True)
    gamp_category: Mapped[int | None] = mapped_column(Integer, nullable=True)  # GAMP 5: 1, 3, 4, 5
    owner: Mapped[str] = mapped_column(String(128), default="")

    status: Mapped[str] = mapped_column(String(16), default=SystemStatus.UNKNOWN)
    status_reason: Mapped[str] = mapped_column(String(256), default="")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Demo only: fault injected into the simulator for this system (None, "degraded", "down", "silent").
    simulated_fault: Mapped[str | None] = mapped_column(String(16), nullable=True)
