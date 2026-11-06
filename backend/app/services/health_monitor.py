"""Turns heartbeats into a system status, and status changes into incidents."""
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models._time import as_utc, utcnow
from app.models.system import System, SystemStatus
from app.models.telemetry import Telemetry
from app.services import incident_manager
from app.services.audit_logger import log_event


@dataclass
class Heartbeat:
    reported_status: str   # "up" or "down"
    latency_ms: int
    error_rate: float
    message: str = ""


def evaluate(hb: Heartbeat) -> tuple[SystemStatus, str]:
    if hb.reported_status == "down":
        return SystemStatus.DOWN, f"System reports down: {hb.message or 'no detail'}"
    problems = []
    if hb.latency_ms > settings.latency_degraded_ms:
        problems.append(f"latency {hb.latency_ms} ms > {settings.latency_degraded_ms} ms")
    if hb.error_rate > settings.error_rate_degraded:
        problems.append(f"error rate {hb.error_rate:.0%} > {settings.error_rate_degraded:.0%}")
    if problems:
        return SystemStatus.DEGRADED, "; ".join(problems)
    return SystemStatus.OPERATIONAL, "Within thresholds"


def apply_status(db: Session, system: System, new_status: SystemStatus, reason: str) -> None:
    old = system.status
    system.status_reason = reason
    if old == new_status:
        return
    system.status = new_status
    log_event(db, actor="system", action="system.status_changed", entity_type="system",
              entity_id=system.code, details={"from": old, "to": new_status.value, "reason": reason})
    if new_status in (SystemStatus.DEGRADED, SystemStatus.DOWN):
        incident_manager.open_for_system_status(db, system, new_status, reason)
    elif new_status == SystemStatus.OPERATIONAL and old in (SystemStatus.DEGRADED, SystemStatus.DOWN):
        incident_manager.mark_recovered(db, system)


def record_heartbeat(db: Session, system: System, hb: Heartbeat) -> Telemetry:
    now = utcnow()
    t = Telemetry(system_id=system.id, received_at=now, reported_status=hb.reported_status,
                  latency_ms=hb.latency_ms, error_rate=hb.error_rate, message=hb.message)
    db.add(t)
    system.last_heartbeat_at = now
    status, reason = evaluate(hb)
    apply_status(db, system, status, reason)
    return t


def check_timeouts(db: Session) -> list[System]:
    """Mark systems DOWN when they stop sending heartbeats."""
    now = utcnow()
    limit = timedelta(seconds=settings.heartbeat_timeout_seconds)
    timed_out = []
    # Integrations report through sync jobs, not heartbeats (see fda_pipeline.check_staleness).
    for system in db.scalars(select(System).where(System.system_type != "INTEGRATION")):
        last = as_utc(system.last_heartbeat_at)
        if last is None or system.status == SystemStatus.DOWN:
            continue
        if now - last > limit:
            secs = int((now - last).total_seconds())
            # Name the moment of the last heartbeat: unlike "for N s" this stays true while the outage lasts.
            apply_status(db, system, SystemStatus.DOWN,
                         f"No heartbeat since {last:%Y-%m-%d %H:%M:%S} UTC (timeout {settings.heartbeat_timeout_seconds} s)")
            timed_out.append(system)
    return timed_out
