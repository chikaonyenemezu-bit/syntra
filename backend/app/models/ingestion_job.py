from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._time import utcnow


class JobStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"   # every record accepted
    PARTIAL = "partial"       # completed, some records rejected
    FAILED = "failed"         # source could not be read; nothing imported


class IngestionJob(Base):
    """One run of an integration: what was fetched, accepted and rejected."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True, index=True, default="")
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.id"), index=True)
    trigger: Mapped[str] = mapped_column(String(16))      # scheduled | manual
    source: Mapped[str] = mapped_column(String(32))       # live | sample | sample_with_errors
    source_detail: Mapped[str] = mapped_column(Text, default="")  # URL or fixture name
    triggered_by: Mapped[str] = mapped_column(String(64), default="system")
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.RUNNING, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    fetched: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    unchanged: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    rejected_records: Mapped[list["RejectedRecord"]] = relationship(
        back_populates="job", order_by="RejectedRecord.id", cascade="all, delete-orphan")

    @property
    def rejection_rate(self) -> float:
        return self.rejected / self.fetched if self.fetched else 0.0


class RejectedRecord(Base):
    """A record that failed validation. Kept in quarantine with its reasons, never silently dropped."""

    __tablename__ = "rejected_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("ingestion_jobs.id"), index=True)
    record_key: Mapped[str] = mapped_column(String(64))   # recall number, or position if missing
    reasons: Mapped[str] = mapped_column(Text)            # JSON list of reasons
    payload: Mapped[str] = mapped_column(Text)            # original record as received (JSON)
    rejected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[IngestionJob] = relationship(back_populates="rejected_records")
