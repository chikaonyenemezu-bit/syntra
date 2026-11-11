
from sqlalchemy import select

from app.models.system import System
from app.services.health_monitor import Heartbeat, record_heartbeat


def open_mes_incident(SessionTest) -> str:
    with SessionTest() as db:
        system = db.scalars(
            select(System).where(System.code == "MES-01")
        ).one()

        record_heartbeat(
            db,
            system,
            Heartbeat("down", 0, 1.0, "test outage"),
        )
        db.commit()

    return "INC-000001"


NOTE = "Restarted EBR application service; terminals reconnected."


INVESTIGATION = {
    "root_cause": (
        "The EBR application service stopped responding "
        "following an unexpected process failure."
    ),
    "gxp_impact_assessment": (
        "The outage interrupted access to electronic batch "
        "records. No confirmed loss of batch data was identified."
    ),
    "corrective_actions": (
        "Restarted the application service and checked "
        "system connectivity and operational status."
    ),
    "recovery_verification": (
        "Verified that the application was accessible "
        "and that connected terminals responded normally."
    ),
    "evidence_references": (
        "TEST-INC-001; TEST-RECOVERY-001"
    ),
}


QA_APPROVAL = {
    "decision": "approved",
    "justification": (
        "Investigation and recovery evidence reviewed. "
        "The documented corrective actions are acceptable."
    ),
}


def submit_investigation(client, number, headers):
    response = client.post(
        f"/api/incidents/{number}/investigations",
        json=INVESTIGATION,
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["revision"] == 1

    return response.json()


def approve_investigation(client, number, headers):
    response = client.post(
        f"/api/incidents/{number}/qa-review",
        json=QA_APPROVAL,
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["decision"] == "approved"
    assert response.json()["reviewed_by"] == "qa.lead"

    return response.json()


def test_full_gxp_workflow(client, login, SessionTest):
    num = open_mes_incident(SessionTest)
    ops, qa = login("it.ops"), login("qa.lead")

    response = client.post(
        f"/api/incidents/{num}/acknowledge",
        headers=ops,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "acknowledged"

    submit_investigation(client, num, ops)

    response = client.post(
        f"/api/incidents/{num}/resolve",
        json={"note": NOTE},
        headers=ops,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "resolved"
    assert response.json()["resolved_by"] == "it.ops"

    approve_investigation(client, num, qa)

    response = client.post(
        f"/api/incidents/{num}/close",
        headers=qa,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "closed"
    assert response.json()["closed_by"] == "qa.lead"


def test_gxp_incident_cannot_be_closed_by_it_ops(
    client, login, SessionTest
):
    num = open_mes_incident(SessionTest)
    ops = login("it.ops")
    ops2 = login("it.ops2")
    qa = login("qa.lead")

    submit_investigation(client, num, ops)

    response = client.post(
        f"/api/incidents/{num}/resolve",
        json={"note": NOTE},
        headers=ops,
    )
    assert response.status_code == 200, response.text

    approve_investigation(client, num, qa)

    response = client.post(
        f"/api/incidents/{num}/close",
        headers=ops2,
    )

    assert response.status_code == 403
    assert "QA" in response.json()["detail"]


def test_four_eyes_on_non_gxp_incident(client, login):
    ops, ops2 = login("it.ops"), login("it.ops2")

    response = client.post(
        "/api/incidents",
        json={
            "title": "Printer queue stuck in office",
            "severity": "low",
        },
        headers=ops,
    )

    num = response.json()["number"]
    assert response.json()["gxp_impact"] is False

    response = client.post(
        f"/api/incidents/{num}/resolve",
        json={"note": "Cleared queue, restarted spooler."},
        headers=ops,
    )
    assert response.status_code == 200, response.text

    assert client.post(
        f"/api/incidents/{num}/close",
        headers=ops,
    ).status_code == 403

    assert client.post(
        f"/api/incidents/{num}/close",
        headers=ops2,
    ).status_code == 200


def test_resolution_note_required(client, login, SessionTest):
    num = open_mes_incident(SessionTest)

    response = client.post(
        f"/api/incidents/{num}/resolve",
        json={"note": "fixed"},
        headers=login("it.ops"),
    )

    assert response.status_code == 422


def test_invalid_transition_rejected(client, login, SessionTest):
    num = open_mes_incident(SessionTest)

    response = client.post(
        f"/api/incidents/{num}/close",
        headers=login("qa.lead"),
    )

    assert response.status_code == 409


def test_every_transition_is_audited(
    client, login, SessionTest
):
    num = open_mes_incident(SessionTest)
    ops, qa = login("it.ops"), login("qa.lead")

    response = client.post(
        f"/api/incidents/{num}/acknowledge",
        headers=ops,
    )
    assert response.status_code == 200, response.text

    submit_investigation(client, num, ops)

    response = client.post(
        f"/api/incidents/{num}/resolve",
        json={"note": NOTE},
        headers=ops,
    )
    assert response.status_code == 200, response.text

    approve_investigation(client, num, qa)

    response = client.post(
        f"/api/incidents/{num}/close",
        headers=qa,
    )
    assert response.status_code == 200, response.text

    response = client.get(
        "/api/audit",
        params={
            "entity_type": "incident",
            "entity_id": num,
        },
        headers=qa,
    )
    assert response.status_code == 200, response.text

    events = list(reversed(response.json()))
    actions = [event["action"] for event in events]

    expected = [
        "incident.opened",
        "incident.acknowledged",
        "incident.investigation_submitted",
        "incident.resolved",
        "incident.closed",
    ]

    # Verify the documented lifecycle events in order.
    known_actions = [
        action for action in actions if action in expected
    ]
    assert known_actions == expected

    # QA review must also have an audit event between
    # technical resolution and controlled closure.
    resolved_index = actions.index("incident.resolved")
    closed_index = actions.index("incident.closed")

    assert any(
        event["actor"] == "qa.lead"
        for event in events[resolved_index + 1:closed_index]
    ), "Missing QA review audit event"
