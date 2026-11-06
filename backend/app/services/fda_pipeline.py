"""openFDA recall integration: fetch → validate → quarantine or upsert → job record → integration health.

The integration is a monitored system (INT-FDA-01). Its status comes from the sync jobs instead of
heartbeats: a failed fetch makes it DOWN, a rejection rate above the threshold makes it DEGRADED,
and no successful sync for too long makes it DEGRADED. Status changes go through the same health
monitor as every other system, so incidents open and recover the same way.
"""
import hashlib
import json
import time
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.integrations.openfda import RecallSource, SourceError
from app.models._time import as_utc, utcnow
from app.models.ingestion_job import IngestionJob, JobStatus, RejectedRecord
from app.models.recall import Recall
from app.models.system import System, SystemStatus
from app.services.audit_logger import log_event
from app.services.data_validator import ValidationResult, validate_recall
from app.services.health_monitor import apply_status

INTEGRATION_CODE = "INT-FDA-01"

STORED_FIELDS = [
    "event_id", "classification", "status", "product_type", "product_description",
    "reason_for_recall", "recalling_firm", "city", "state", "country", "distribution_pattern",
    "code_info", "product_quantity", "voluntary_mandated",
    "recall_initiation_date", "report_date", "termination_date",
]


class IntegrationNotFound(Exception):
    pass


def get_integration(db: Session) -> System:
    system = db.scalars(select(System).where(System.code == INTEGRATION_CODE)).first()
    if system is None:
        raise IntegrationNotFound(f"Integration {INTEGRATION_CODE} is not registered")
    return system


def content_hash(record: dict) -> str:
    payload = json.dumps({f: record.get(f) for f in STORED_FIELDS}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _finish(job: IngestionJob, t0: float, status: JobStatus) -> None:
    job.status = status
    job.finished_at = utcnow()
    job.duration_ms = int((time.monotonic() - t0) * 1000)


def run_sync(db: Session, source: RecallSource, *, trigger: str = "scheduled", actor: str = "system",
             today: date | None = None) -> IngestionJob:
    """Run one sync. Commits nothing; the caller commits so job, data and audit land together."""
    system = get_integration(db)
    job = IngestionJob(system_id=system.id, trigger=trigger, source=source.name,
                       source_detail=source.detail, triggered_by=actor, status=JobStatus.RUNNING)
    db.add(job)
    db.flush()
    job.number = f"ING-{job.id:06d}"
    t0 = time.monotonic()

    try:
        raw_records = source.fetch()
    except SourceError as e:
        job.error_message = str(e)
        _finish(job, t0, JobStatus.FAILED)
        log_event(db, actor=actor, action="integration.sync_failed", entity_type="ingestion_job",
                  entity_id=job.number, details={"integration": system.code, "source": source.name,
                                                 "trigger": trigger, "error": str(e)})
        apply_status(db, system, SystemStatus.DOWN, f"Sync {job.number} failed: {e}")
        return job

    job.fetched = len(raw_records)
    numbers = [r.get("recall_number") for r in raw_records if isinstance(r, dict) and r.get("recall_number")]
    existing = {r.recall_number: r for r in db.scalars(select(Recall).where(Recall.recall_number.in_(numbers)))}
    seen: set[str] = set()
    record_source = "openfda" if source.name == "live" else "sample"

    for position, raw in enumerate(raw_records, start=1):
        result = validate_recall(raw, today=today, position=position)
        if result.valid and result.record["recall_number"] in seen:
            result = ValidationResult(None, ["Duplicate recall number within this batch"], result.key)
        if not result.valid:
            job.rejected += 1
            db.add(RejectedRecord(job_id=job.id, record_key=result.key, reasons=json.dumps(result.reasons),
                                  payload=json.dumps(raw, default=str, ensure_ascii=False)))
            continue

        rec = result.record
        number = rec["recall_number"]
        seen.add(number)
        digest = content_hash(rec)
        current = existing.get(number)

        if current is None:
            db.add(Recall(recall_number=number, source=record_source, content_hash=digest,
                          first_seen_job_id=job.id, last_changed_job_id=job.id,
                          **{f: rec[f] for f in STORED_FIELDS}))
            job.inserted += 1
        elif current.content_hash == digest:
            job.unchanged += 1
        else:
            changes = {f: {"from": getattr(current, f), "to": rec[f]}
                       for f in STORED_FIELDS if getattr(current, f) != rec[f]}
            for f in STORED_FIELDS:
                setattr(current, f, rec[f])
            current.content_hash = digest
            current.last_changed_job_id = job.id
            current.updated_at = utcnow()
            job.updated += 1
            log_event(db, actor=actor, action="recall.updated", entity_type="recall", entity_id=number,
                      details={"job": job.number, "changes": changes})

    _finish(job, t0, JobStatus.PARTIAL if job.rejected else JobStatus.SUCCEEDED)
    log_event(db, actor=actor, action="integration.sync_completed", entity_type="ingestion_job",
              entity_id=job.number, details={
                  "integration": system.code, "source": source.name, "trigger": trigger,
                  "status": job.status, "fetched": job.fetched, "inserted": job.inserted,
                  "updated": job.updated, "unchanged": job.unchanged, "rejected": job.rejected,
              })

    system.last_heartbeat_at = job.finished_at  # for an integration: last completed sync
    threshold = settings.fda_rejection_threshold
    if job.rejection_rate > threshold:
        apply_status(db, system, SystemStatus.DEGRADED,
                     f"{job.rejected} of {job.fetched} records rejected ({job.rejection_rate:.0%}) "
                     f"in {job.number}, above the {threshold:.0%} limit")
    else:
        accepted = job.inserted + job.updated + job.unchanged
        apply_status(db, system, SystemStatus.OPERATIONAL,
                     f"Last sync {job.number}: {accepted} accepted, {job.rejected} rejected")
    return job


def check_staleness(db: Session, now: datetime | None = None) -> bool:
    """Degrade the integration when scheduled syncs stop succeeding. Returns True if it degraded it."""
    if not settings.fda_sync_enabled:
        return False
    system = db.scalars(select(System).where(System.code == INTEGRATION_CODE)).first()
    last = as_utc(system.last_heartbeat_at) if system else None
    if system is None or last is None or system.status != SystemStatus.OPERATIONAL:
        return False
    now = as_utc(now) if now else utcnow()
    allowed = timedelta(minutes=2 * settings.fda_sync_interval_minutes + 10)
    if now - last <= allowed:
        return False
    hours = (now - last).total_seconds() / 3600
    apply_status(db, system, SystemStatus.DEGRADED, f"No successful sync for {hours:.1f} h")
    return True
