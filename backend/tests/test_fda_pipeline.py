import json
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import select

from app.integrations.openfda import FixtureSource, OpenFDASource, SourceError, get_source
from app.models.audit_event import AuditEvent
from app.models.incident import Incident, Severity
from app.models.ingestion_job import JobStatus, RejectedRecord
from app.models.recall import Recall
from app.models.system import SystemStatus
from app.services import fda_pipeline
from app.services.audit_logger import verify_chain

TODAY = date(2026, 11, 6)


class BrokenSource:
    name = "live"
    detail = "https://api.fda.gov/drug/enforcement.json"

    def fetch(self):
        raise SourceError("Could not reach openFDA: ConnectError: network unreachable")


def sync(db, source_name="sample", **kw):
    job = fda_pipeline.run_sync(db, get_source(source_name), trigger="manual", actor="it.ops", today=TODAY, **kw)
    db.commit()
    return job


def integration(db):
    return fda_pipeline.get_integration(db)


def incidents(db):
    return list(db.scalars(select(Incident).where(Incident.system_id == integration(db).id)))


def test_clean_sample_imports_everything(db):
    job = sync(db)
    assert job.number == "ING-000001"
    assert (job.status, job.fetched, job.inserted, job.rejected) == (JobStatus.SUCCEEDED, 12, 12, 0)
    assert db.scalar(select(Recall).where(Recall.recall_number == "D-0901-2026")).classification == "Class II"
    assert integration(db).status == SystemStatus.OPERATIONAL
    assert integration(db).last_heartbeat_at is not None
    assert incidents(db) == []


def test_second_run_is_idempotent(db):
    sync(db)
    job = sync(db)
    assert (job.inserted, job.updated, job.unchanged) == (0, 0, 12)
    assert db.query(Recall).count() == 12


def test_invalid_records_are_quarantined_with_reasons(db):
    sync(db)
    job = sync(db, "sample_with_errors")
    assert job.status == JobStatus.PARTIAL
    assert (job.fetched, job.rejected) == (14, 6)
    assert (job.inserted, job.updated, job.unchanged) == (1, 1, 6)
    rejected = db.scalars(select(RejectedRecord).where(RejectedRecord.job_id == job.id)).all()
    reasons = [r for rec in rejected for r in json.loads(rec.reasons)]
    assert any("Missing required field 'classification'" in r for r in reasons)
    assert any("Duplicate recall number within this batch" in r for r in reasons)
    assert all(json.loads(rec.payload) for rec in rejected)  # original record kept
    # rejected records never reach the recall table
    assert db.scalar(select(Recall).where(Recall.classification == "Class IV")) is None


def test_high_rejection_rate_degrades_integration_and_opens_incident(db):
    job = sync(db, "sample_with_errors")
    system = integration(db)
    assert system.status == SystemStatus.DEGRADED
    assert "6 of 14 records rejected" in system.status_reason and job.number in system.status_reason
    (inc,) = incidents(db)
    assert inc.severity == Severity.MEDIUM and inc.gxp_impact

    sync(db)  # clean run: system recovers, incident stays open for review
    assert integration(db).status == SystemStatus.OPERATIONAL
    (inc,) = incidents(db)
    assert inc.recovered_at is not None and inc.status == "open"


def test_changed_recall_is_updated_and_audited(db):
    sync(db)
    sync(db, "sample_with_errors")
    recall = db.scalar(select(Recall).where(Recall.recall_number == "D-0901-2026"))
    assert recall.status == "Terminated" and recall.termination_date == date(2026, 11, 5)
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "recall.updated",
                                               AuditEvent.entity_id == "D-0901-2026"))
    changes = json.loads(event.details)["changes"]
    assert changes["status"] == {"from": "Ongoing", "to": "Terminated"}
    assert verify_chain(db).valid


def test_failed_fetch_marks_job_failed_and_opens_critical_incident(db):
    job = fda_pipeline.run_sync(db, BrokenSource(), trigger="scheduled", actor="system", today=TODAY)
    db.commit()
    assert job.status == JobStatus.FAILED and "network unreachable" in job.error_message
    assert integration(db).status == SystemStatus.DOWN
    (inc,) = incidents(db)
    assert inc.severity == Severity.CRITICAL
    assert db.query(Recall).count() == 0


def test_staleness_degrades_integration(db):
    sync(db)
    system = integration(db)
    assert not fda_pipeline.check_staleness(db)
    later = system.last_heartbeat_at + timedelta(days=2)
    assert fda_pipeline.check_staleness(db, now=later)
    assert system.status == SystemStatus.DEGRADED and "No successful sync" in system.status_reason


# --- openFDA client against a fake server -------------------------------------------------------

def fake_openfda(pages: list[list[dict]], total: int):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        skip = int(request.url.params["skip"])
        idx = skip // 2
        if idx >= len(pages):
            return httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": "No matches found!"}})
        return httpx.Response(200, json={"meta": {"results": {"total": total}}, "results": pages[idx]})

    return httpx.MockTransport(handler), calls


def test_client_pages_through_results():
    sample = FixtureSource("sample", get_source("sample").file).fetch()
    transport, calls = fake_openfda([sample[0:2], sample[2:4], sample[4:5]], total=5)
    src = OpenFDASource(page_size=2, max_records=50, lookback_days=30, today=TODAY, transport=transport)
    assert len(src.fetch()) == 5
    assert len(calls) == 3
    assert "report_date:[20261007+TO+20261106]" in calls[0].replace("%5B", "[").replace("%5D", "]")


def test_client_treats_404_as_empty_result():
    transport, _ = fake_openfda([], total=0)
    assert OpenFDASource(today=TODAY, transport=transport).fetch() == []


def test_client_raises_source_error_on_server_error():
    transport = httpx.MockTransport(lambda r: httpx.Response(500, text="upstream timeout"))
    with pytest.raises(SourceError, match="HTTP 500"):
        OpenFDASource(today=TODAY, transport=transport).fetch()


def test_client_raises_source_error_on_network_error():
    def boom(request):
        raise httpx.ConnectError("network unreachable")
    with pytest.raises(SourceError, match="Could not reach openFDA"):
        OpenFDASource(today=TODAY, transport=httpx.MockTransport(boom)).fetch()
