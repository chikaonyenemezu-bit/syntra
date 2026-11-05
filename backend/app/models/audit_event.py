"""Audit trail table.

GxP design notes (ALCOA+, EU GMP Annex 11 §9, 21 CFR Part 11 §11.10(e)):
- Every record says who did what, to which record, when (UTC), and the details.
- Records are append-only: the database itself rejects UPDATE and DELETE.
- Each record stores the hash of the previous one (hash chain), so any change
  made around the database guard (e.g. by a superuser) is detectable.
"""
from datetime import datetime

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._time import utcnow


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(64), index=True)       # username or "system"
    action: Mapped[str] = mapped_column(String(64), index=True)      # e.g. incident.acknowledged
    entity_type: Mapped[str] = mapped_column(String(32), index=True)  # e.g. incident
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[str] = mapped_column(Text, default="{}")         # canonical JSON
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


_PG_GUARD = """
CREATE OR REPLACE FUNCTION audit_events_block_changes() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_events is append-only: %% is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events;
CREATE TRIGGER audit_events_no_update BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW EXECUTE FUNCTION audit_events_block_changes();

DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events;
CREATE TRIGGER audit_events_no_truncate BEFORE TRUNCATE ON audit_events
  FOR EACH STATEMENT EXECUTE FUNCTION audit_events_block_changes();
"""

_SQLITE_GUARD = [
    """CREATE TRIGGER IF NOT EXISTS audit_events_no_update BEFORE UPDATE ON audit_events
       BEGIN SELECT RAISE(ABORT, 'audit_events is append-only: UPDATE is not allowed'); END;""",
    """CREATE TRIGGER IF NOT EXISTS audit_events_no_delete BEFORE DELETE ON audit_events
       BEGIN SELECT RAISE(ABORT, 'audit_events is append-only: DELETE is not allowed'); END;""",
]


def install_append_only_guard(bind: Engine) -> None:
    with bind.begin() as conn:
        if bind.dialect.name == "postgresql":
            conn.exec_driver_sql(_PG_GUARD)
        elif bind.dialect.name == "sqlite":
            for stmt in _SQLITE_GUARD:
                conn.execute(text(stmt))
