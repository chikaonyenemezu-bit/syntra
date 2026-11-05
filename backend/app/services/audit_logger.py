import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models._time import as_utc, utcnow
from app.models.audit_event import AuditEvent

GENESIS_HASH = "0" * 64
_PG_LOCK_KEY = 815_001  # serialises writers so the chain never forks


def _canonical(details: dict[str, Any]) -> str:
    return json.dumps(details, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(prev_hash: str, occurred_at, actor: str, action: str,
                 entity_type: str, entity_id: str, details_json: str) -> str:
    payload = "|".join([
        prev_hash, as_utc(occurred_at).isoformat(), actor, action,
        entity_type, entity_id, details_json,
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_event(db: Session, *, actor: str, action: str, entity_type: str,
              entity_id: str | int, details: dict[str, Any] | None = None) -> AuditEvent:
    """Append one audit record. Call inside the same transaction as the change it records,
    so the change and its audit record are committed together or not at all."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _PG_LOCK_KEY})

    last = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1)).first()
    prev_hash = last.hash if last else GENESIS_HASH
    occurred_at = utcnow()
    details_json = _canonical(details or {})
    event = AuditEvent(
        occurred_at=occurred_at, actor=actor, action=action,
        entity_type=entity_type, entity_id=str(entity_id), details=details_json,
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, occurred_at, actor, action, entity_type,
                          str(entity_id), details_json),
    )
    db.add(event)
    db.flush()
    return event


@dataclass
class ChainCheck:
    valid: bool
    records_checked: int
    first_broken_id: int | None = None
    reason: str | None = None


def verify_chain(db: Session) -> ChainCheck:
    """Recompute every hash and check the links. Used by QA and by the tests."""
    prev_hash = GENESIS_HASH
    count = 0
    for ev in db.scalars(select(AuditEvent).order_by(AuditEvent.id)):
        count += 1
        if ev.prev_hash != prev_hash:
            return ChainCheck(False, count, ev.id, "link to previous record is broken")
        expected = compute_hash(ev.prev_hash, ev.occurred_at, ev.actor, ev.action,
                                ev.entity_type, ev.entity_id, ev.details)
        if ev.hash != expected:
            return ChainCheck(False, count, ev.id, "record content does not match its hash")
        prev_hash = ev.hash
    return ChainCheck(True, count)
