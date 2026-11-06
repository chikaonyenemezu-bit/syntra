"""Electronic signatures (21 CFR Part 11 §11.50/§11.70, EU GMP Annex 11 §14).

A signature is executed by re-entering the password and states its meaning. It is stored with the
signer's printed name, role, date/time and meaning, linked to the record it signs, and is append-only
like the audit trail.
"""
from datetime import datetime

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._time import utcnow


class ESignature(Base):
    __tablename__ = "esignatures"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)  # change_request | periodic_review
    entity_id: Mapped[str] = mapped_column(String(32), index=True)    # CR-000001, PR-000001
    signer: Mapped[str] = mapped_column(String(64))
    signer_name: Mapped[str] = mapped_column(String(128))
    signer_role: Mapped[str] = mapped_column(String(32))
    meaning: Mapped[str] = mapped_column(String(64))   # e.g. "Approved (QA)", "Verified (QA)"
    comment: Mapped[str] = mapped_column(Text, default="")
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


_PG_GUARD = """
CREATE OR REPLACE FUNCTION esignatures_block_changes() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'esignatures is append-only: %% is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS esignatures_no_change ON esignatures;
CREATE TRIGGER esignatures_no_change BEFORE UPDATE OR DELETE ON esignatures
  FOR EACH ROW EXECUTE FUNCTION esignatures_block_changes();
"""

_SQLITE_GUARD = [
    """CREATE TRIGGER IF NOT EXISTS esignatures_no_update BEFORE UPDATE ON esignatures
       BEGIN SELECT RAISE(ABORT, 'esignatures is append-only: UPDATE is not allowed'); END;""",
    """CREATE TRIGGER IF NOT EXISTS esignatures_no_delete BEFORE DELETE ON esignatures
       BEGIN SELECT RAISE(ABORT, 'esignatures is append-only: DELETE is not allowed'); END;""",
]


def install_esignature_guard(bind: Engine) -> None:
    with bind.begin() as conn:
        if bind.dialect.name == "postgresql":
            conn.exec_driver_sql(_PG_GUARD)
        elif bind.dialect.name == "sqlite":
            for stmt in _SQLITE_GUARD:
                conn.execute(text(stmt))
