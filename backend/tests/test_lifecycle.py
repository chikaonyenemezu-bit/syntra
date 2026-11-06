from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DatabaseError

from app.models.esignature import ESignature
from app.models.lifecycle import SystemLifecycle
from app.models.system import System
from app.seed import DEMO_PASSWORD
from app.services.lifecycle_manager import add_months, review_state

TODAY = date(2026, 11, 6)
PW = DEMO_PASSWORD


def lifecycle(db, code) -> SystemLifecycle:
    return db.scalars(select(SystemLifecycle).join(SystemLifecycle.system).where(System.code == code)).one()


# --- periodic review status -------------------------------------------------------------------------

def test_add_months_clamps_to_month_end():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2024, 8, 19), 24) == date(2026, 8, 19)


def test_seeded_systems_show_every_review_state(db):
    assert review_state(lifecycle(db, "LIMS-01"), TODAY).state == "overdue"     # due 2026-08-19
    assert review_state(lifecycle(db, "ERP-01"), TODAY).state == "due_soon"     # due 2026-12-09
    assert review_state(lifecycle(db, "MES-01"), TODAY).state == "ok"           # due 2027-03-14
    assert review_state(lifecycle(db, "INT-FDA-01"), TODAY).state == "not_applicable"  # not validated yet


def test_lifecycle_api(client, login):
    rows = client.get("/api/lifecycle", headers=login("viewer")).json()
    assert [r["system"]["code"] for r in rows] == ["ERP-01", "INT-FDA-01", "LIMS-01", "MES-01"]
    lims = client.get("/api/lifecycle/LIMS-01", headers=login("viewer")).json()
    assert lims["validated_version"] == "8.1.0" and lims["next_review_due"] == "2026-08-19"
    assert client.get("/api/lifecycle/NOPE-01", headers=login("viewer")).status_code == 404


def test_periodic_review_by_qa_with_signature(client, login):
    qa = login("qa.lead")
    body = {"outcome": "remains_validated", "password": PW,
            "summary": "Access rights, audit trail, backups and open deviations reviewed; no findings."}
    r = client.post("/api/lifecycle/LIMS-01/reviews", json=body, headers=qa)
    assert r.status_code == 201, r.text
    lims = r.json()
    assert lims["last_review_outcome"] == "remains_validated" and lims["review_state"] == "ok"
    (review,) = lims["reviews"]
    assert review["number"] == "PR-000001"
    assert review["signature"]["meaning"] == "Reviewed (QA): remains validated"
    assert review["signature"]["signer_name"] == "QA Lead"


def test_periodic_review_rules(client, login):
    body = {"outcome": "remains_validated", "password": PW,
            "summary": "Access rights, audit trail, backups and open deviations reviewed; no findings."}
    assert client.post("/api/lifecycle/LIMS-01/reviews", json=body, headers=login("it.ops")).status_code == 403
    assert client.post("/api/lifecycle/INT-FDA-01/reviews", json=body, headers=login("qa.lead")).status_code == 409
    bad = client.post("/api/lifecycle/LIMS-01/reviews", json={**body, "password": "wrong"}, headers=login("qa.lead"))
    assert bad.status_code == 403 and "password" in bad.json()["detail"]
    assert client.get("/api/lifecycle/LIMS-01", headers=login("qa.lead")).json()["reviews"] == []


# --- change control ---------------------------------------------------------------------------------

MAJOR = {
    "system_code": "MES-01", "title": "Upgrade MES to 3.3.0 (new weighing interface)",
    "description": "Install MES release 3.3.0 with the new balance interface for dispensing.",
    "justification": "Vendor support for 3.2 ends; new interface removes manual transcription.",
    "impact_assessment": "Affects electronic batch record weighing steps; GxP impact; OQ/PQ needed.",
    "category": "major", "risk": "high", "target_version": "3.3.0",
}
MINOR = {
    "system_code": "ERP-01", "title": "Patch ERP to 6.0.5 (report fix)",
    "description": "Apply vendor hotfix 6.0.5 fixing a stock report layout issue.",
    "justification": "Report layout bug confuses warehouse staff.",
    "impact_assessment": "Reporting only; no GxP data or calculations affected.",
    "category": "minor", "risk": "low", "target_version": "6.0.5",
}
NOTE = "Deployed in maintenance window, smoke tests passed."
EVIDENCE = "Test protocol TP-2026-031 executed, all cases passed."


def raise_and_submit(client, login, data=MAJOR, requester="it.ops"):
    h = login(requester)
    cr = client.post("/api/changes", json=data, headers=h).json()
    assert cr["status"] == "draft", cr
    cr = client.post(f"/api/changes/{cr['number']}/submit", headers=h).json()
    assert cr["status"] == "in_review", cr
    return cr["number"]


def sign(client, login, user, number, action="approve", **extra):
    return client.post(f"/api/changes/{number}/{action}", json={"password": PW, **extra}, headers=login(user))


def test_full_major_change_revalidates_system(client, login, db):
    n = raise_and_submit(client, login)
    cr = client.get(f"/api/changes/{n}", headers=login("viewer")).json()
    assert cr["requires_revalidation"] is True                     # default for major changes
    assert cr["pending_approvals"] == ["system_owner", "qa"]

    cr = sign(client, login, "system.owner", n, comment="Business need confirmed").json()
    assert cr["status"] == "in_review" and cr["pending_approvals"] == ["qa"]
    cr = sign(client, login, "qa.lead", n).json()
    assert cr["status"] == "approved"

    cr = client.post(f"/api/changes/{n}/implement", json={"note": NOTE}, headers=login("it.ops2")).json()
    assert cr["status"] == "implemented"
    mes = client.get("/api/lifecycle/MES-01", headers=login("viewer")).json()
    assert (mes["current_version"], mes["validated_version"], mes["validation_status"]) == ("3.3.0", "3.2.1", "in_validation")

    cr = sign(client, login, "qa.reviewer", n, action="verify", evidence=EVIDENCE).json()
    assert cr["status"] == "verified"
    assert [s["meaning"] for s in cr["signatures"]] == ["Approved (System Owner)", "Approved (QA)", "Verified (QA)"]
    mes = client.get("/api/lifecycle/MES-01", headers=login("viewer")).json()
    assert (mes["validated_version"], mes["validation_status"], mes["validation_report"]) == ("3.3.0", "validated", n)
    assert mes["validated_on"] == date.today().isoformat()


def test_minor_change_keeps_validated_state(client, login):
    n = raise_and_submit(client, login, MINOR)
    sign(client, login, "system.owner", n)
    sign(client, login, "qa.lead", n)
    client.post(f"/api/changes/{n}/implement", json={"note": NOTE}, headers=login("it.ops"))
    erp = client.get("/api/lifecycle/ERP-01", headers=login("viewer")).json()
    assert erp["validation_status"] == "validated" and erp["current_version"] == "6.0.5"
    sign(client, login, "qa.lead", n, action="verify", evidence=EVIDENCE)
    erp = client.get("/api/lifecycle/ERP-01", headers=login("viewer")).json()
    assert erp["validated_version"] == "6.0.5" and erp["validated_on"] == "2023-11-27"  # no revalidation


def test_wrong_password_is_rejected_and_audited(client, login, db):
    n = raise_and_submit(client, login)
    r = client.post(f"/api/changes/{n}/approve", json={"password": "guess"}, headers=login("system.owner"))
    assert r.status_code == 403 and "password" in r.json()["detail"]
    cr = client.get(f"/api/changes/{n}", headers=login("viewer")).json()
    assert cr["signatures"] == [] and cr["status"] == "in_review"
    events = client.get("/api/audit", params={"entity_id": n}, headers=login("qa.lead")).json()
    assert any(e["action"] == "esign.failed" and e["actor"] == "system.owner" for e in events)


def test_segregation_of_duties(client, login):
    n = raise_and_submit(client, login, requester="qa.lead")
    assert sign(client, login, "qa.lead", n).status_code == 403          # own request
    assert sign(client, login, "it.ops", n).status_code == 403           # role not an approver
    assert sign(client, login, "admin", n).status_code == 403            # admin is not an approver either
    assert sign(client, login, "qa.reviewer", n).status_code == 200
    assert sign(client, login, "qa.reviewer", n).status_code == 409      # QA already approved
    assert sign(client, login, "system.owner", n).json()["status"] == "approved"
    assert client.post(f"/api/changes/{n}/implement", json={"note": NOTE},
                       headers=login("qa.reviewer")).status_code == 403  # only IT Ops implements
    client.post(f"/api/changes/{n}/implement", json={"note": NOTE}, headers=login("it.ops"))
    assert sign(client, login, "qa.lead", n, action="verify", evidence=EVIDENCE).status_code == 403  # requester
    assert sign(client, login, "it.ops", n, action="verify", evidence=EVIDENCE).status_code == 403   # not QA
    assert sign(client, login, "qa.reviewer", n, action="verify", evidence=EVIDENCE).status_code == 200


def test_draft_rules(client, login):
    ops = login("it.ops")
    assert client.post("/api/changes", json=MAJOR, headers=login("viewer")).status_code == 403
    thin = client.post("/api/changes", json={**MAJOR, "justification": ""}, headers=ops).json()
    n = thin["number"]
    assert client.post(f"/api/changes/{n}/submit", headers=ops).status_code == 409          # justification missing
    assert client.patch(f"/api/changes/{n}", json={"justification": "x" * 20},
                        headers=login("it.ops2")).status_code == 403                         # not the requester
    assert client.patch(f"/api/changes/{n}", json={"justification": "Vendor support ends."},
                        headers=ops).status_code == 200
    assert client.post(f"/api/changes/{n}/submit", headers=ops).status_code == 200
    assert client.patch(f"/api/changes/{n}", json={"title": "Changed after submit"},
                        headers=ops).status_code == 409                                      # no edits once submitted
    assert sign(client, login, "qa.lead", n, action="verify", evidence=EVIDENCE).status_code == 409  # wrong state


def test_rejection_is_final(client, login):
    n = raise_and_submit(client, login)
    r = sign(client, login, "qa.lead", n, action="reject", reason="Impact assessment misses data migration.")
    assert r.json()["status"] == "rejected" and r.json()["rejected_by"] == "qa.lead"
    assert sign(client, login, "system.owner", n).status_code == 409


def test_non_gxp_change_needs_system_owner_only(client, login, db):
    erp = db.scalars(select(System).where(System.code == "ERP-01")).one()
    erp.gxp_relevant = False
    db.commit()
    n = raise_and_submit(client, login, MINOR)
    cr = sign(client, login, "system.owner", n).json()
    assert cr["required_approvals"] == ["system_owner"] and cr["status"] == "approved"


def test_signatures_are_append_only(client, login, db):
    n = raise_and_submit(client, login)
    sign(client, login, "system.owner", n)
    with pytest.raises(DatabaseError, match="append-only"):
        db.execute(text("UPDATE esignatures SET meaning = 'Rejected (System Owner)'"))
    db.rollback()
    with pytest.raises(DatabaseError, match="append-only"):
        db.execute(text("DELETE FROM esignatures"))
    db.rollback()
    assert db.query(ESignature).count() == 1
