from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._time import utcnow


class Telemetry(Base):
    """One heartbeat reported by a system."""

    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.id"), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    reported_status: Mapped[str] = mapped_column(String(16))  # what the system says: up / down
    latency_ms: Mapped[int] = mapped_column(Integer)
    error_rate: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(String(256), default="")
