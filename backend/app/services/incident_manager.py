"""Incident workflow: open -> acknowledged -> resolved -> closed.

Rules (each one is a requirement in validation/URS.md):
- A resolution note is mandatory.
- Incidents on GxP-relevant systems can only be closed by QA.
- The person who resolved an incident cannot also close it (four-eyes principle).
- When a system recovers, the incident is NOT closed automatically; it is marked
  as recovered and still needs a human resolution and closure.
- Every transition is written to the audit trail in the same transaction.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models._time import utcnow
from app.models.incident import Incident, IncidentStatus, Severity
from app.models.system import System, SystemStatus
from app.models.user import Role, User
from app.services.audit_logger import log_event


class WorkflowError(Exception):
    """Raised when a transition is not allowed. Mapped to HTTP 409/403 by the API."""

    def __init__(self, message: str, forbidden: bool = False):
        super().__init__(message)
        self.forbidden = forbidden


ACTIVE = (IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED)


def _snapshot(inc: Incident) -> dict:
    return {"number": inc.number, "status": inc.status, "severity": inc.severity}


def open_incident(db: Session, *, title: str, description: str, severity: Severity,
                  actor: str, source: str = "manual", system: System | None = None) -> Incident:
    inc = Incident(
        title=title, description=description, severity=severity, source=source,
        system_id=system.id if system else None,
        gxp_impact=bool(system and system.gxp_relevant),
        opened_by=actor, status=IncidentStatus.OPEN,
    )
    db.add(inc)
    db.flush()
    inc.number = f"INC-{inc.id:06d}"
    log_event(db, actor=actor, action="incident.opened", entity_type="incident",
              entity_id=inc.number, details={
                  **_snapshot(inc), "title": title, "source": source,
                  "system": system.code if system else None, "gxp_impact": inc.gxp_impact,
              })
    return inc


def active_incident_for(db: Session, system: System) -> Incident | None:
    return db.scalars(
        select(Incident)
        .where(Incident.system_id == system.id, Incident.status.in_(ACTIVE))
        .order_by(Incident.id.desc())
    ).first()


def open_for_system_status(db: Session, system: System, new_status: SystemStatus,
                           reason: str) -> Incident | None:
    """Called by the health monitor. Opens one incident per outage, never duplicates."""
    existing = active_incident_for(db, system)
    if existing:
        if new_status == SystemStatus.DOWN and existing.severity != Severity.CRITICAL and system.gxp_relevant:
            old = existing.severity
            existing.severity = Severity.CRITICAL
            log_event(db, actor="system", action="incident.escalated", entity_type="incident",
                      entity_id=existing.number, details={"from": old, "to": existing.severity, "reason": reason})
        return existing

    if new_status == SystemStatus.DOWN:
        severity = Severity.CRITICAL if system.gxp_relevant else Severity.HIGH
    else:
        severity = Severity.MEDIUM
    return open_incident(
        db, system=system, source="monitor", actor="system", severity=severity,
        title=f"{system.code} {new_status.value}: {reason}",
        description=(f"Automatically opened by the health monitor. {system.name} changed "
                     f"to '{new_status.value}'. Reason: {reason}"),
    )


def mark_recovered(db: Session, system: System) -> Incident | None:
    inc = active_incident_for(db, system)
    if inc and inc.recovered_at is None:
        inc.recovered_at = utcnow()
        log_event(db, actor="system", action="incident.system_recovered", entity_type="incident",
                  entity_id=inc.number, details={"system": system.code,
                                                 "note": "System operational again; incident stays open for review"})
    return inc


def acknowledge(db: Session, inc: Incident, user: User) -> Incident:
    if inc.status != IncidentStatus.OPEN:
        raise WorkflowError(f"Only open incidents can be acknowledged (current: {inc.status})")
    inc.status = IncidentStatus.ACKNOWLEDGED
    inc.acknowledged_at = utcnow()
    inc.acknowledged_by = user.username
    log_event(db, actor=user.username, action="incident.acknowledged", entity_type="incident",
              entity_id=inc.number, details=_snapshot(inc))
    return inc


def resolve(db: Session, inc: Incident, user: User, note: str) -> Incident:
    if inc.status not in ACTIVE:
        raise WorkflowError(f"Only open or acknowledged incidents can be resolved (current: {inc.status})")
    if not note or len(note.strip()) < 10:
        raise WorkflowError("A resolution note of at least 10 characters is required")
    inc.status = IncidentStatus.RESOLVED
    inc.resolved_at = utcnow()
    inc.resolved_by = user.username
    inc.resolution_note = note.strip()
    log_event(db, actor=user.username, action="incident.resolved", entity_type="incident",
              entity_id=inc.number, details={**_snapshot(inc), "resolution_note": inc.resolution_note})
    return inc


def close(db: Session, inc: Incident, user: User) -> Incident:
    if inc.status != IncidentStatus.RESOLVED:
        raise WorkflowError(f"Only resolved incidents can be closed (current: {inc.status})")
    if inc.gxp_impact and user.role != Role.QA:
        raise WorkflowError("Incidents on GxP-relevant systems must be closed by QA", forbidden=True)
    if user.username == inc.resolved_by:
        raise WorkflowError("The person who resolved the incident cannot close it (four-eyes principle)",
                            forbidden=True)
    inc.status = IncidentStatus.CLOSED
    inc.closed_at = utcnow()
    inc.closed_by = user.username
    log_event(db, actor=user.username, action="incident.closed", entity_type="incident",
              entity_id=inc.number, details=_snapshot(inc))
    return inc
