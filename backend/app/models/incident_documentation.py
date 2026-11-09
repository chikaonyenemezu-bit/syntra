
"""Structured, traceable GxP incident documentation."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._time import utcnow


class IncidentInvestigation(Base):
    __tablename__ = "incident_investigations"

    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "revision",
            name="uq_incident_investigation_revision",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id"),
        nullable=False,
        index=True,
    )

    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    gxp_impact_assessment: Mapped[str] = mapped_column(Text, nullable=False)
    corrective_actions: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_verification: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_references: Mapped[str] = mapped_column(Text, nullable=False)

    submitted_by: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    incident = relationship("Incident")


class IncidentQAReview(Base):
    __tablename__ = "incident_qa_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)

    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id"),
        nullable=False,
        index=True,
    )

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("incident_investigations.id"),
        nullable=False,
    )

    decision: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    justification: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    reviewed_by: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    incident = relationship("Incident")
    investigation = relationship("IncidentInvestigation")
