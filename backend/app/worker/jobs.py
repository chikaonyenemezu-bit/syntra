"""Background worker: runs the simulators and the health checks on a schedule.

Run with:  python -m app.worker.jobs
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db
from app.models.system import System
from app.seed import seed
from app.services import health_monitor
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


def tick() -> None:
    with SessionLocal() as db:
        try:
            simulate_and_monitor(db)
            db.commit()
        except Exception:
            db.rollback()
            log.exception("Monitoring cycle failed")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed(db)
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(tick, "interval", seconds=settings.heartbeat_interval_seconds,
                      id="simulate_and_monitor", max_instances=1, coalesce=True)
    log.info("Worker started: heartbeat every %ss, timeout %ss",
             settings.heartbeat_interval_seconds, settings.heartbeat_timeout_seconds)
    tick()
    scheduler.start()


if __name__ == "__main__":
    main()
