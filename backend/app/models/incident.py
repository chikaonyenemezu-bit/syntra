from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._time import utcnow
from app.models.system import System


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"   # technically fixed by IT Ops
    CLOSED = "closed"       # formally closed (QA for GxP-relevant systems)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True, index=True, default="")
    system_id: Mapped[int | None] = mapped_column(ForeignKey("systems.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default=Severity.MEDIUM)
    status: Mapped[str] = mapped_column(String(16), default=IncidentStatus.OPEN, index=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")  # monitor | manual
    gxp_impact: Mapped[bool] = mapped_column(default=False)

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    opened_by: Mapped[str] = mapped_column(String(64), default="system")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    system: Mapped[System | None] = relationship()
