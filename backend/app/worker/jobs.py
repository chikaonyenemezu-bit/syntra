"""Background worker: runs the simulators, the health checks and the scheduled integration syncs.

Run with:  python -m app.worker.jobs
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db
from app.integrations.openfda import OpenFDASource
from app.models.system import System
from app.seed import seed
from app.services import fda_pipeline, health_monitor
from app.simulators import SIMULATORS

log = logging.getLogger("worker")


def simulate_and_monitor(db: Session) -> None:
    """One monitoring cycle: every simulated system sends a heartbeat, then timeouts are checked."""
    for system in db.scalars(select(System)):
        sim = SIMULATORS.get(system.system_type)
        if sim is None:
            continue  # not simulated (e.g. a real integration)
        hb = sim.heartbeat(system.simulated_fault)
        if hb is not None:
            health_monitor.record_heartbeat(db, system, hb)
    health_monitor.check_timeouts(db)
    fda_pipeline.check_staleness(db)


def tick() -> None:
    with SessionLocal() as db:
        try:
            simulate_and_monitor(db)
            db.commit()
        except Exception:
            db.rollback()
            log.exception("Monitoring cycle failed")


def fda_sync() -> None:
    """Scheduled live sync from openFDA."""
    with SessionLocal() as db:
        try:
            job = fda_pipeline.run_sync(db, OpenFDASource(), trigger="scheduled", actor="system")
            db.commit()
            log.info("openFDA sync %s %s: fetched %s, inserted %s, updated %s, unchanged %s, rejected %s%s",
                     job.number, job.status, job.fetched, job.inserted, job.updated, job.unchanged,
                     job.rejected, f" ({job.error_message})" if job.error_message else "")
        except Exception:
            db.rollback()
            log.exception("openFDA sync crashed")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("apscheduler").setLevel(logging.WARNING)  # no log line per tick
    init_db()
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed(db)
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(tick, "interval", seconds=settings.heartbeat_interval_seconds,
                      id="simulate_and_monitor", max_instances=1, coalesce=True)
    if settings.fda_sync_enabled:
        scheduler.add_job(fda_sync, "interval", minutes=settings.fda_sync_interval_minutes,
                          id="fda_sync", max_instances=1, coalesce=True,
                          next_run_time=datetime.now(timezone.utc))
    log.info("Worker started: heartbeat every %ss, timeout %ss; openFDA sync %s",
             settings.heartbeat_interval_seconds, settings.heartbeat_timeout_seconds,
             f"every {settings.fda_sync_interval_minutes} min" if settings.fda_sync_enabled else "disabled")
    tick()
    scheduler.start()


if __name__ == "__main__":
    main()
