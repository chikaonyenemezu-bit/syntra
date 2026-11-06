from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._time import utcnow
from app.models.system import System


class ChangeStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"      # submitted, waiting for approvals
    APPROVED = "approved"        # all required approvals signed
    IMPLEMENTED = "implemented"  # deployed by IT Ops, waiting for verification
    VERIFIED = "verified"        # verified by QA: closed
    REJECTED = "rejected"


class ChangeCategory(StrEnum):
    MINOR = "minor"    # no impact on validated functionality
    MAJOR = "major"    # affects GxP functionality; usually needs revalidation


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True, index=True, default="")
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    justification: Mapped[str] = mapped_column(Text)
    impact_assessment: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(16), default=ChangeCategory.MINOR)
    risk: Mapped[str] = mapped_column(String(16), default="low")
    requires_revalidation: Mapped[bool] = mapped_column(Boolean, default=False)
    target_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=ChangeStatus.DRAFT, index=True)

    requested_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    implemented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    implemented_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    implementation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    system: Mapped[System] = relationship()
