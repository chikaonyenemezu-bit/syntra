from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._time import utcnow


class Recall(Base):
    """A validated drug recall (openFDA enforcement report), stored as reference data."""

    __tablename__ = "recalls"

    id: Mapped[int] = mapped_column(primary_key=True)
    recall_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g. D-0123-2026
    event_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    classification: Mapped[str] = mapped_column(String(16), index=True)  # Class I / II / III
    status: Mapped[str] = mapped_column(String(32), index=True)          # Ongoing / Completed / Terminated
    product_type: Mapped[str] = mapped_column(String(32))
    product_description: Mapped[str] = mapped_column(Text)
    reason_for_recall: Mapped[str] = mapped_column(Text)
    recalling_firm: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    distribution_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_info: Mapped[str | None] = mapped_column(Text, nullable=True)  # lot numbers / expiry
    product_quantity: Mapped[str | None] = mapped_column(Text, nullable=True)
    voluntary_mandated: Mapped[str | None] = mapped_column(Text, nullable=True)
    recall_initiation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    source: Mapped[str] = mapped_column(String(32), default="openfda")  # openfda | sample
    content_hash: Mapped[str] = mapped_column(String(64))
    first_seen_job_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=True)
    last_changed_job_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
