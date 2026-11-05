"""Smoke test against a real PostgreSQL (run in CI). Checks what SQLite tests can't fully prove:
the PostgreSQL append-only triggers and a valid hash chain across time zones."""
import sys

from sqlalchemy import select, text

from app.database import SessionLocal, init_db
from app.models.system import System, SystemStatus
from app.seed import seed
from app.services.audit_logger import verify_chain
from app.worker.jobs import simulate_and_monitor


def main() -> int:
    init_db()
    init_db()  # must be idempotent
    failures = []
    with SessionLocal() as db:
        seed(db)
        db.scalars(select(System).where(System.code == "ERP-01")).one().simulated_fault = "down"
        simulate_and_monitor(db)
        db.commit()
        if db.scalars(select(System).where(System.code == "ERP-01")).one().status != SystemStatus.DOWN:
            failures.append("ERP-01 should be down after fault injection")

        db.execute(text("SET TIME ZONE 'Europe/Berlin'"))
        if not verify_chain(db).valid:
            failures.append("audit hash chain invalid")

        for stmt in ("UPDATE audit_events SET actor = 'x'", "DELETE FROM audit_events", "TRUNCATE audit_events"):
            try:
                db.execute(text(stmt))
                failures.append(f"not blocked: {stmt}")
            except Exception:
                pass
            db.rollback()

    for f in failures:
        print("FAIL:", f)
    print("PostgreSQL smoke test:", "FAILED" if failures else "passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
