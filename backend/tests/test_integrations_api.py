def test_integration_overview(client, login):
    r = client.get("/api/integrations", headers=login("viewer"))
    assert r.status_code == 200
    (i,) = r.json()
    assert i["system"]["code"] == "INT-FDA-01" and i["last_job"] is None and i["recalls_total"] == 0


def test_only_it_ops_and_admin_can_sync(client, login):
    for user in ("viewer", "qa.lead", "system.owner"):
        r = client.post("/api/integrations/INT-FDA-01/sync", json={"source": "sample"}, headers=login(user))
        assert r.status_code == 403, user
    r = client.post("/api/integrations/INT-FDA-01/sync", json={"source": "sample"}, headers=login("admin"))
    assert r.status_code == 200


def test_sync_job_detail_shows_rejected_records(client, login):
    ops = login("it.ops")
    r = client.post("/api/integrations/INT-FDA-01/sync", json={"source": "sample_with_errors"}, headers=ops)
    job = r.json()
    assert job["status"] == "partial" and job["rejected"] == 6 and job["triggered_by"] == "it.ops"
    assert len(job["rejected_records"]) == 6
    assert all(rec["reasons"] for rec in job["rejected_records"])

    detail = client.get(f"/api/integrations/jobs/{job['number']}", headers=login("viewer")).json()
    assert detail["rejected_records"][0]["payload"]["product_type"] == "Drugs"
    jobs = client.get("/api/integrations/jobs", headers=ops).json()
    assert [j["number"] for j in jobs] == [job["number"]]


def test_unknown_source_rejected(client, login):
    r = client.post("/api/integrations/INT-FDA-01/sync", json={"source": "ftp"}, headers=login("it.ops"))
    assert r.status_code == 422


def test_recall_search(client, login):
    ops = login("it.ops")
    client.post("/api/integrations/INT-FDA-01/sync", json={"source": "sample"}, headers=ops)
    page = client.get("/api/recalls", headers=ops).json()
    assert page["total"] == 12
    assert page["items"][0]["report_date"] >= page["items"][-1]["report_date"]  # newest first

    assert client.get("/api/recalls", params={"q": "metformin"}, headers=ops).json()["total"] == 1
    assert client.get("/api/recalls", params={"q": "A26000"}, headers=ops).json()["total"] == 1  # lot number
    class1 = client.get("/api/recalls", params={"classification": "Class I"}, headers=ops).json()
    assert class1["total"] == 2 and all(i["classification"] == "Class I" for i in class1["items"])

    r = client.get("/api/recalls/D-0904-2026", headers=ops)
    assert r.status_code == 200 and r.json()["classification"] == "Class I"
    assert client.get("/api/recalls/D-9999-2026", headers=ops).status_code == 404


def test_sync_is_audited(client, login):
    ops, qa = login("it.ops"), login("qa.lead")
    client.post("/api/integrations/INT-FDA-01/sync", json={"source": "sample"}, headers=ops)
    actions = [e["action"] for e in client.get("/api/audit", params={"actor": "it.ops"}, headers=qa).json()]
    assert "integration.sync_requested" in actions and "integration.sync_completed" in actions
