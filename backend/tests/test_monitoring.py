from datetime import timedelta

from sqlalchemy import select

from app.models.incident import Incident, Severity
from app.models.system import System, SystemStatus
from app.services.health_monitor import Heartbeat, check_timeouts, evaluate, record_heartbeat
from app.worker.jobs import simulate_and_monitor

OK = Heartbeat("up", latency_ms=200, error_rate=0.0, message="ok")
SLOW = Heartbeat("up", latency_ms=3000, error_rate=0.10, message="slow")
DOWN = Heartbeat("down", latency_ms=0, error_rate=1.0, message="EBR service not reachable")


def mes(db) -> System:
    return db.scalars(select(System).where(System.code == "MES-01")).one()


def incidents(db, system) -> list[Incident]:
    return list(db.scalars(select(Incident).where(Incident.system_id == system.id)))


def test_evaluate_thresholds():
    assert evaluate(OK)[0] == SystemStatus.OPERATIONAL
    status, reason = evaluate(SLOW)
    assert status == SystemStatus.DEGRADED and "latency" in reason and "error rate" in reason
    assert evaluate(DOWN)[0] == SystemStatus.DOWN


def test_degradation_opens_one_incident_not_duplicates(db):
    s = mes(db)
    record_heartbeat(db, s, OK)
    for _ in range(5):
        record_heartbeat(db, s, SLOW)
    db.commit()
    assert s.status == SystemStatus.DEGRADED
    incs = incidents(db, s)
    assert len(incs) == 1
    assert incs[0].severity == Severity.MEDIUM and incs[0].source == "monitor"
    assert incs[0].gxp_impact is True


def test_down_on_gxp_system_is_critical_and_escalates(db):
    s = mes(db)
    record_heartbeat(db, s, SLOW)   # opens a medium incident
    record_heartbeat(db, s, DOWN)   # same outage gets worse
    db.commit()
    incs = incidents(db, s)
    assert len(incs) == 1
    assert incs[0].severity == Severity.CRITICAL


def test_recovery_marks_incident_but_does_not_close_it(db):
    s = mes(db)
    record_heartbeat(db, s, DOWN)
    record_heartbeat(db, s, OK)
    db.commit()
    inc = incidents(db, s)[0]
    assert s.status == SystemStatus.OPERATIONAL
    assert inc.recovered_at is not None
    assert inc.status == "open"  # a human still has to resolve and close it


def test_missing_heartbeat_marks_system_down(db):
    s = mes(db)
    record_heartbeat(db, s, OK)
    s.last_heartbeat_at = s.last_heartbeat_at - timedelta(minutes=5)
    check_timeouts(db)
    db.commit()
    assert s.status == SystemStatus.DOWN
    assert "No heartbeat" in s.status_reason
    assert len(incidents(db, s)) == 1


def test_worker_cycle_with_injected_fault(db):
    s = mes(db)
    s.simulated_fault = "down"
    simulate_and_monitor(db)
    db.commit()
    assert s.status == SystemStatus.DOWN
    others = db.scalars(select(System).where(System.code != "MES-01")).all()
    assert all(o.status == SystemStatus.OPERATIONAL for o in others)


def test_summary_and_fault_api(client, login):
    ops = login("it.ops")
    r = client.post("/api/monitoring/simulators/LIMS-01/fault", json={"mode": "degraded"}, headers=ops)
    assert r.status_code == 200 and r.json()["simulated_fault"] == "degraded"
    r = client.get("/api/monitoring/summary", headers=ops)
    assert r.status_code == 200 and r.json()["systems_total"] == 3
