from sqlalchemy import select

from app.models.system import System
from app.services.health_monitor import Heartbeat, record_heartbeat


def open_mes_incident(SessionTest) -> str:
    with SessionTest() as db:
        s = db.scalars(select(System).where(System.code == "MES-01")).one()
        record_heartbeat(db, s, Heartbeat("down", 0, 1.0, "test outage"))
        db.commit()
    return "INC-000001"


NOTE = "Restarted EBR application service; terminals reconnected."


def test_full_gxp_workflow(client, login, SessionTest):
    num = open_mes_incident(SessionTest)
    ops, qa = login("it.ops"), login("qa.lead")

    assert client.post(f"/api/incidents/{num}/acknowledge", headers=ops).json()["status"] == "acknowledged"
    r = client.post(f"/api/incidents/{num}/resolve", json={"note": NOTE}, headers=ops)
    assert r.json()["status"] == "resolved" and r.json()["resolved_by"] == "it.ops"
    r = client.post(f"/api/incidents/{num}/close", headers=qa)
    assert r.status_code == 200 and r.json()["status"] == "closed" and r.json()["closed_by"] == "qa.lead"


def test_gxp_incident_cannot_be_closed_by_it_ops(client, login, SessionTest):
    num = open_mes_incident(SessionTest)
    ops, ops2 = login("it.ops"), login("it.ops2")
    client.post(f"/api/incidents/{num}/resolve", json={"note": NOTE}, headers=ops)
    r = client.post(f"/api/incidents/{num}/close", headers=ops2)
    assert r.status_code == 403
    assert "QA" in r.json()["detail"]


def test_four_eyes_on_non_gxp_incident(client, login):
    ops, ops2 = login("it.ops"), login("it.ops2")
    r = client.post("/api/incidents", json={"title": "Printer queue stuck in office", "severity": "low"},
                    headers=ops)
    num = r.json()["number"]
    assert r.json()["gxp_impact"] is False
    client.post(f"/api/incidents/{num}/resolve", json={"note": "Cleared queue, restarted spooler."}, headers=ops)
    assert client.post(f"/api/incidents/{num}/close", headers=ops).status_code == 403  # same person
    assert client.post(f"/api/incidents/{num}/close", headers=ops2).status_code == 200


def test_resolution_note_required(client, login, SessionTest):
    num = open_mes_incident(SessionTest)
    r = client.post(f"/api/incidents/{num}/resolve", json={"note": "fixed"}, headers=login("it.ops"))
    assert r.status_code == 422


def test_invalid_transition_rejected(client, login, SessionTest):
    num = open_mes_incident(SessionTest)
    r = client.post(f"/api/incidents/{num}/close", headers=login("qa.lead"))
    assert r.status_code == 409


def test_every_transition_is_audited(client, login, SessionTest):
    num = open_mes_incident(SessionTest)
    ops, qa = login("it.ops"), login("qa.lead")
    client.post(f"/api/incidents/{num}/acknowledge", headers=ops)
    client.post(f"/api/incidents/{num}/resolve", json={"note": NOTE}, headers=ops)
    client.post(f"/api/incidents/{num}/close", headers=qa)
    events = client.get("/api/audit", params={"entity_type": "incident", "entity_id": num}, headers=qa).json()
    actions = [e["action"] for e in reversed(events)]
    assert actions == ["incident.opened", "incident.acknowledged", "incident.resolved", "incident.closed"]
