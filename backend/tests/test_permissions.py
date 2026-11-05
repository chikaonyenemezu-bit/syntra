import pytest

from tests.test_incidents import open_mes_incident


def test_requires_login(client):
    assert client.get("/api/systems").status_code == 401


def test_wrong_password_rejected_and_audited(client, login):
    r = client.post("/api/auth/login", data={"username": "it.ops", "password": "wrong"})
    assert r.status_code == 401
    events = client.get("/api/audit", params={"action": None, "entity_id": "it.ops"},
                        headers=login("qa.lead")).json()
    assert any(e["action"] == "auth.login_failed" for e in events)


def test_viewer_is_read_only(client, login, SessionTest):
    num = open_mes_incident(SessionTest)
    v = login("viewer")
    assert client.get("/api/systems", headers=v).status_code == 200
    assert client.post(f"/api/incidents/{num}/acknowledge", headers=v).status_code == 403
    assert client.post("/api/incidents", json={"title": "Should fail"}, headers=v).status_code == 403
    assert client.get("/api/audit", headers=v).status_code == 403
    assert client.post("/api/monitoring/simulators/MES-01/fault", json={"mode": "down"},
                       headers=v).status_code == 403


@pytest.mark.parametrize("user,expected", [("qa.lead", 403), ("system.owner", 403), ("it.ops", 200)])
def test_only_it_ops_acknowledges(client, login, SessionTest, user, expected):
    num = open_mes_incident(SessionTest)
    assert client.post(f"/api/incidents/{num}/acknowledge", headers=login(user)).status_code == expected
