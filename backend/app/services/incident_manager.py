
"""Syntra incident workflow and GxP documentation.

Incident lifecycle:
    open -> acknowledged -> resolved -> closed

GxP documentation:
    investigation -> QA review -> authorized closure

Controls:
- Incident recovery does not automatically close an incident.
- IT Operations submits documented investigations.
- Each investigation submission creates a new revision.
- QA reviews an identified investigation revision.
- QA may approve or return an investigation.
- GxP closure requires approval of the latest revision.
- The resolver cannot close their own incident.
- Significant actions are written to the audit trail.
- Transactions are committed by the API layer.

This service does not independently implement electronic
signature authentication. That must be enforced by the API
using Syntra's existing signature infrastructure.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models._time import utcnow
from app.models.incident import Incident, IncidentStatus, Severity
from app.models.incident_documentation import (
    IncidentInvestigation,
    IncidentQAReview,
)
from app.models.system import System, SystemStatus
from app.models.user import Role, User
from app.services.audit_logger import log_event


class WorkflowError(Exception):
    """Raised when a workflow action is not permitted."""

    def __init__(
        self,
        message: str,
        forbidden: bool = False,
    ):
        super().__init__(message)
        self.forbidden = forbidden


ACTIVE = (
    IncidentStatus.OPEN,
    IncidentStatus.ACKNOWLEDGED,
)


def _snapshot(inc: Incident) -> dict:
    return {
        "number": inc.number,
        "status": inc.status,
        "severity": inc.severity,
    }


def _require_role(user: User, role: Role) -> None:
    if user.role != role:
        raise WorkflowError(
            f"This action requires the {role.value} role.",
            forbidden=True,
        )


def _required_text(
    value: str,
    field: str,
    minimum: int,
) -> str:
    cleaned = value.strip() if isinstance(value, str) else ""

    if len(cleaned) < minimum:
        raise WorkflowError(
            f"{field} requires at least {minimum} characters."
        )

    return cleaned


def _latest_investigation(
    db: Session,
    incident_id: int,
) -> IncidentInvestigation | None:
    return db.scalars(
        select(IncidentInvestigation)
        .where(
            IncidentInvestigation.incident_id == incident_id
        )
        .order_by(
            IncidentInvestigation.revision.desc(),
            IncidentInvestigation.id.desc(),
        )
        .limit(1)
    ).first()


def _latest_review(
    db: Session,
    investigation_id: int,
) -> IncidentQAReview | None:
    return db.scalars(
        select(IncidentQAReview)
        .where(
            IncidentQAReview.investigation_id
            == investigation_id
        )
        .order_by(IncidentQAReview.id.desc())
        .limit(1)
    ).first()


# --------------------------------------------------
# Incident creation
# --------------------------------------------------

def open_incident(
    db: Session,
    *,
    title: str,
    description: str,
    severity: Severity,
    actor: str,
    source: str = "manual",
    system: System | None = None,
) -> Incident:

    inc = Incident(
        title=title,
        description=description,
        severity=severity,
        source=source,
        system_id=system.id if system else None,
        gxp_impact=bool(
            system and system.gxp_relevant
        ),
        opened_by=actor,
        status=IncidentStatus.OPEN,
    )

    db.add(inc)
    db.flush()

    inc.number = f"INC-{inc.id:06d}"

    log_event(
        db,
        actor=actor,
        action="incident.opened",
        entity_type="incident",
        entity_id=inc.number,
        details={
            **_snapshot(inc),
            "title": title,
            "source": source,
            "system": system.code if system else None,
            "gxp_impact": inc.gxp_impact,
        },
    )

    return inc


# --------------------------------------------------
# Automatic incident monitoring
# --------------------------------------------------

def active_incident_for(
    db: Session,
    system: System,
) -> Incident | None:

    return db.scalars(
        select(Incident)
        .where(
            Incident.system_id == system.id,
            Incident.status.in_(ACTIVE),
        )
        .order_by(Incident.id.desc())
    ).first()


def open_for_system_status(
    db: Session,
    system: System,
    new_status: SystemStatus,
    reason: str,
) -> Incident | None:

    """Open one incident per outage, avoiding duplicates."""

    existing = active_incident_for(db, system)

    if existing:
        if (
            new_status == SystemStatus.DOWN
            and existing.severity != Severity.CRITICAL
            and system.gxp_relevant
        ):
            old = existing.severity

            existing.severity = Severity.CRITICAL

            log_event(
                db,
                actor="system",
                action="incident.escalated",
                entity_type="incident",
                entity_id=existing.number,
                details={
                    "from": old,
                    "to": existing.severity,
                    "reason": reason,
                },
            )

        return existing

    if new_status == SystemStatus.DOWN:
        severity = (
            Severity.CRITICAL
            if system.gxp_relevant
            else Severity.HIGH
        )
    else:
        severity = Severity.MEDIUM

    return open_incident(
        db,
        system=system,
        source="monitor",
        actor="system",
        severity=severity,
        title=(
            f"{system.code} {new_status.value}: {reason}"
        ),
        description=(
            "Automatically opened by the health monitor. "
            f"{system.name} changed to "
            f"'{new_status.value}'. Reason: {reason}"
        ),
    )


# --------------------------------------------------
# Technical recovery
# --------------------------------------------------

def mark_recovered(
    db: Session,
    system: System,
) -> Incident | None:

    inc = active_incident_for(db, system)

    if inc and inc.recovered_at is None:
        inc.recovered_at = utcnow()

        log_event(
            db,
            actor="system",
            action="incident.system_recovered",
            entity_type="incident",
            entity_id=inc.number,
            details={
                "system": system.code,
                "note": (
                    "System operational again; "
                    "incident stays open for review"
                ),
            },
        )

    return inc


# --------------------------------------------------
# Incident acknowledgement
# --------------------------------------------------

def acknowledge(
    db: Session,
    inc: Incident,
    user: User,
) -> Incident:

    _require_role(user, Role.IT_OPS)

    if inc.status != IncidentStatus.OPEN:
        raise WorkflowError(
            "Only open incidents can be acknowledged "
            f"(current: {inc.status})"
        )

    inc.status = IncidentStatus.ACKNOWLEDGED
    inc.acknowledged_at = utcnow()
    inc.acknowledged_by = user.username

    log_event(
        db,
        actor=user.username,
        action="incident.acknowledged",
        entity_type="incident",
        entity_id=inc.number,
        details=_snapshot(inc),
    )

    return inc


# --------------------------------------------------
# Structured investigation submission
# --------------------------------------------------

def submit_investigation(
    db: Session,
    inc: Incident,
    user: User,
    *,
    root_cause: str,
    gxp_impact_assessment: str,
    corrective_actions: str,
    recovery_verification: str,
    evidence_references: str,
) -> IncidentInvestigation:

    _require_role(user, Role.IT_OPS)

    if inc.status == IncidentStatus.CLOSED:
        raise WorkflowError(
            "Closed incidents cannot receive new "
            "investigation submissions."
        )

    # Lock the parent incident row to serialize
    # revision allocation for the same incident.
    db.scalar(
        select(Incident)
        .where(Incident.id == inc.id)
        .with_for_update()
    )

    latest = _latest_investigation(db, inc.id)

    revision = (
        latest.revision + 1
        if latest is not None
        else 1
    )

    investigation = IncidentInvestigation(
        incident_id=inc.id,
        revision=revision,
        root_cause=_required_text(
            root_cause, "Root cause", 20
        ),
        gxp_impact_assessment=_required_text(
            gxp_impact_assessment,
            "GxP impact assessment",
            20,
        ),
        corrective_actions=_required_text(
            corrective_actions,
            "Corrective actions",
            20,
        ),
        recovery_verification=_required_text(
            recovery_verification,
            "Recovery verification",
            20,
        ),
        evidence_references=_required_text(
            evidence_references,
            "Evidence references",
            10,
        ),
        submitted_by=user.username,
        submitted_at=utcnow(),
    )

    db.add(investigation)
    db.flush()

    log_event(
        db,
        actor=user.username,
        action="incident.investigation_submitted",
        entity_type="incident",
        entity_id=inc.number,
        details={
            "investigation_id": investigation.id,
            "revision": investigation.revision,
            "submitted_by": user.username,
            "root_cause": investigation.root_cause,
            "gxp_impact_assessment":
                investigation.gxp_impact_assessment,
            "corrective_actions":
                investigation.corrective_actions,
            "recovery_verification":
                investigation.recovery_verification,
            "evidence_references":
                investigation.evidence_references,
        },
    )

    return investigation


# --------------------------------------------------
# Incident resolution
# --------------------------------------------------

def resolve(
    db: Session,
    inc: Incident,
    user: User,
    note: str,
) -> Incident:

    _require_role(user, Role.IT_OPS)

    if inc.status not in ACTIVE:
        raise WorkflowError(
            "Only open or acknowledged incidents "
            f"can be resolved (current: {inc.status})"
        )

    cleaned_note = _required_text(
        note,
        "Resolution note",
        10,
    )

    # GxP incidents require structured documentation
    # before the technical resolution is accepted.
    if inc.gxp_impact:
        investigation = _latest_investigation(
            db, inc.id
        )

        if investigation is None:
            raise WorkflowError(
                "A documented investigation is required "
                "before resolving a GxP incident."
            )

    inc.status = IncidentStatus.RESOLVED
    inc.resolved_at = utcnow()
    inc.resolved_by = user.username
    inc.resolution_note = cleaned_note

    log_event(
        db,
        actor=user.username,
        action="incident.resolved",
        entity_type="incident",
        entity_id=inc.number,
        details={
            **_snapshot(inc),
            "resolution_note": inc.resolution_note,
        },
    )

    return inc


# --------------------------------------------------
# QA investigation review
# --------------------------------------------------

def review_investigation(
    db: Session,
    inc: Incident,
    user: User,
    *,
    decision: str,
    justification: str,
) -> IncidentQAReview:

    _require_role(user, Role.QA)

    if not inc.gxp_impact:
        raise WorkflowError(
            "This QA documentation workflow is "
            "intended for GxP-impacting incidents."
        )

    if inc.status != IncidentStatus.RESOLVED:
        raise WorkflowError(
            "The incident must be resolved before "
            "formal QA review."
        )

    if decision not in ("approved", "returned"):
        raise WorkflowError(
            "QA decision must be approved or returned."
        )

    reason = _required_text(
        justification,
        "QA justification",
        20,
    )

    # Lock the parent incident while evaluating
    # and saving the QA decision.
    db.scalar(
        select(Incident)
        .where(Incident.id == inc.id)
        .with_for_update()
    )

    investigation = _latest_investigation(
        db, inc.id
    )

    if investigation is None:
        raise WorkflowError(
            "No documented investigation exists "
            "for QA review."
        )

    existing_review = _latest_review(
        db, investigation.id
    )

    if existing_review is not None:
        raise WorkflowError(
            "This investigation revision already "
            "has a QA decision. Submit a new "
            "revision for another review."
        )

    review = IncidentQAReview(
        incident_id=inc.id,
        investigation_id=investigation.id,
        decision=decision,
        justification=reason,
        reviewed_by=user.username,
        reviewed_at=utcnow(),
    )

    db.add(review)
    db.flush()

    log_event(
        db,
        actor=user.username,
        action=f"incident.qa_{decision}",
        entity_type="incident",
        entity_id=inc.number,
        details={
            "review_id": review.id,
            "investigation_id": investigation.id,
            "investigation_revision":
                investigation.revision,
            "decision": decision,
            "justification": reason,
            "reviewed_by": user.username,
        },
    )

    return review


# --------------------------------------------------
# Controlled incident closure
# --------------------------------------------------

def close(
    db: Session,
    inc: Incident,
    user: User,
) -> Incident:

    if inc.status != IncidentStatus.RESOLVED:
        raise WorkflowError(
            "Only resolved incidents can be closed "
            f"(current: {inc.status})"
        )

    if user.role not in (
        Role.IT_OPS,
        Role.QA,
    ):
        raise WorkflowError(
            "Incident closure requires IT Operations "
            "or QA authorization.",
            forbidden=True,
        )

    if inc.gxp_impact and user.role != Role.QA:
        raise WorkflowError(
            "GxP incidents must be closed by QA.",
            forbidden=True,
        )

    if user.username == inc.resolved_by:
        raise WorkflowError(
            "The person who resolved the incident "
            "cannot close it (four-eyes principle).",
            forbidden=True,
        )

    if inc.gxp_impact:
        investigation = _latest_investigation(
            db, inc.id
        )

        if investigation is None:
            raise WorkflowError(
                "Closure blocked: no documented "
                "investigation exists."
            )

        review = _latest_review(
            db, investigation.id
        )

        if review is None:
            raise WorkflowError(
                "Closure blocked: the latest "
                "investigation has not been "
                "reviewed by QA."
            )

        if review.decision != "approved":
            raise WorkflowError(
                "Closure blocked: the latest "
                "investigation was returned "
                "for correction."
            )

        if review.reviewed_by != user.username:
            raise WorkflowError(
                "Closure requires the QA reviewer "
                "who approved the latest investigation."
            )

    inc.status = IncidentStatus.CLOSED
    inc.closed_at = utcnow()
    inc.closed_by = user.username

    details = _snapshot(inc)

    if inc.gxp_impact:
        details.update({
            "investigation_id": investigation.id,
            "investigation_revision":
                investigation.revision,
            "qa_review_id": review.id,
            "qa_review_decision": review.decision,
            "qa_reviewed_by": review.reviewed_by,
            "qa_justification": review.justification,
        })

    log_event(
        db,
        actor=user.username,
        action="incident.closed",
        entity_type="incident",
        entity_id=inc.number,
        details=details,
    )

    return inc
