import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from app.services.audit_logger import log_event, verify_chain


def test_chain_is_valid_after_normal_use(db):
    for i in range(5):
        log_event(db, actor="it.ops", action="test.event", entity_type="test", entity_id=i, details={"i": i})
    db.commit()
    result = verify_chain(db)
    assert result.valid and result.records_checked >= 5


def test_update_is_blocked_by_database(db):
    log_event(db, actor="it.ops", action="test.event", entity_type="test", entity_id=1)
    db.commit()
    with pytest.raises(DatabaseError, match="append-only"):
        db.execute(text("UPDATE audit_events SET actor = 'someone.else'"))
    db.rollback()


def test_delete_is_blocked_by_database(db):
    with pytest.raises(DatabaseError, match="append-only"):
        db.execute(text("DELETE FROM audit_events"))
    db.rollback()


def test_tampering_around_the_guard_is_detected(db):
    """Simulates a privileged user disabling the trigger and editing history."""
    log_event(db, actor="it.ops", action="incident.closed", entity_type="incident", entity_id="INC-000009")
    log_event(db, actor="qa.lead", action="test.after", entity_type="test", entity_id=1)
    db.commit()
    db.execute(text("DROP TRIGGER audit_events_no_update"))
    db.execute(text("UPDATE audit_events SET actor = 'qa.lead' WHERE action = 'incident.closed'"))
    db.commit()
    result = verify_chain(db)
    assert not result.valid
    assert result.reason == "record content does not match its hash"


def test_audit_api_and_verify_endpoint(client, login):
    qa = login("qa.lead")
    events = client.get("/api/audit", headers=qa).json()
    assert any(e["action"] == "system.registered" for e in events)
    assert client.get("/api/audit/verify", headers=qa).json()["valid"] is True
