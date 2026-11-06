"""Smoke test against a real PostgreSQL (run in CI). Checks what SQLite tests can't fully prove:
the PostgreSQL append-only triggers (audit trail and e-signatures), a valid hash chain across time
zones, and the main flows (monitoring, openFDA import, change control) on the production database."""
import sys
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select, text

from app.bootstrap import prepare_database
from app.database import SessionLocal, init_db
from app.integrations.openfda import get_source
from app.models.system import System, SystemStatus
from app.models.user import User
from app.seed import DEMO_PASSWORD, seed
from app.services import fda_pipeline, lifecycle_manager
from app.services.audit_logger import verify_chain
from app.worker.jobs import simulate_and_monitor


def main() -> int:
    failures = []
    # API and worker prepare the database at the same moment on every start: must not collide.
    with ThreadPoolExecutor(max_workers=3) as pool:
        errors = [f.exception() for f in [pool.submit(prepare_database) for _ in range(3)]]
    failures += [f"concurrent startup failed: {e!r}" for e in errors if e]
    init_db()  # must be idempotent
    with SessionLocal() as db:
        seed(db)
        db.scalars(select(System).where(System.code == "ERP-01")).one().simulated_fault = "down"
        simulate_and_monitor(db)
        db.commit()
        if db.scalars(select(System).where(System.code == "ERP-01")).one().status != SystemStatus.DOWN:
            failures.append("ERP-01 should be down after fault injection")

        # openFDA integration with bundled sample data (no network needed)
        clean = fda_pipeline.run_sync(db, get_source("sample"), trigger="manual", actor="smoke")
        db.commit()
        dirty = fda_pipeline.run_sync(db, get_source("sample_with_errors"), trigger="manual", actor="smoke")
        db.commit()
        if (clean.inserted, dirty.rejected, dirty.updated) != (12, 6, 1):
            failures.append(f"unexpected sync counts: {clean.inserted=} {dirty.rejected=} {dirty.updated=}")
        if fda_pipeline.get_integration(db).status != SystemStatus.DEGRADED:
            failures.append("INT-FDA-01 should be degraded after the error sample")

        # GxP lifecycle: release the openFDA interface through change control (validates it)
        user = {u.username: u for u in db.scalars(select(User))}
        fda = fda_pipeline.get_integration(db)
        cr = lifecycle_manager.create_change(db, user["it.ops"], fda, {
            "title": "Release openFDA interface for GxP use", "category": "major", "risk": "medium",
            "description": "Put INT-FDA-01 0.2.0 into validated operation.",
            "justification": "Recall data is used in quality decisions.",
            "impact_assessment": "New GxP data source; validation required."})
        lifecycle_manager.submit(db, cr, user["it.ops"])
        lifecycle_manager.approve(db, cr, user["system.owner"], DEMO_PASSWORD)
        lifecycle_manager.approve(db, cr, user["qa.lead"], DEMO_PASSWORD)
        lifecycle_manager.implement(db, cr, user["it.ops2"], "Configured schedule and thresholds.")
        lifecycle_manager.verify(db, cr, user["qa.reviewer"], DEMO_PASSWORD, "Smoke test protocol executed.")
        db.commit()
        lc = lifecycle_manager.lifecycle_for(db, fda)
        if (cr.status, lc.validation_status, lc.validated_version) != ("verified", "validated", "0.2.0"):
            failures.append(f"change control did not validate INT-FDA-01: {cr.status=} {lc.validation_status=}")
        for stmt in ("UPDATE esignatures SET meaning = 'x'", "DELETE FROM esignatures"):
            try:
                db.execute(text(stmt))
                failures.append(f"not blocked: {stmt}")
            except Exception:
                pass
            db.rollback()

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
