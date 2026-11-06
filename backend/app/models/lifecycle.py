"""GxP lifecycle of each computerised system (GAMP 5): validation state and periodic review.

The validation state is never edited directly. It changes only through controlled processes:
a verified change request (new validated version) or a signed periodic review.
"""
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._time import utcnow
from app.models.system import System


class ValidationStatus(StrEnum):
    NOT_VALIDATED = "not_validated"
    IN_VALIDATION = "in_validation"   # a change requiring revalidation is being implemented/tested
    VALIDATED = "validated"
    RETIRED = "retired"


class RiskClass(StrEnum):
    HIGH = "high"       # direct patient safety / product quality / data integrity impact
    MEDIUM = "medium"
    LOW = "low"


class ReviewOutcome(StrEnum):
    REMAINS_VALIDATED = "remains_validated"
    REMEDIATION_REQUIRED = "remediation_required"


class SystemLifecycle(Base):
    __tablename__ = "system_lifecycle"

    id: Mapped[int] = mapped_column(primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.id"), unique=True)
    risk_class: Mapped[str] = mapped_column(String(16), default=RiskClass.MEDIUM)
    current_version: Mapped[str] = mapped_column(String(32), default="")
    validated_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(16), default=ValidationStatus.NOT_VALIDATED)
    validated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    validation_report: Mapped[str | None] = mapped_column(String(64), nullable=True)  # document reference
    periodic_review_months: Mapped[int] = mapped_column(Integer, default=24)
    last_review_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_review_outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    system: Mapped[System] = relationship()


class PeriodicReview(Base):
    __tablename__ = "periodic_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True, default="")
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.id"), index=True)
    reviewed_on: Mapped[date] = mapped_column(Date)
    outcome: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    reviewer: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
