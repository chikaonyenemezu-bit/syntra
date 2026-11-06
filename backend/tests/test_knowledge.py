import csv
import json
import shutil

import pytest
from sqlalchemy import select

from app.knowledge import DOCS_DIR, EVALUATION_FILE
from app.models.audit_event import AuditEvent
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.knowledge_index import DocumentFormatError, index_documents, parse_document
from app.services.retrieval import get_index


def test_all_documents_indexed_once(db):
    assert db.query(KnowledgeDocument).count() == len(list(DOCS_DIR.glob("*.md"))) == 11
    assert db.query(KnowledgeChunk).count() > 60
    assert index_documents(db) == {"new": 0, "updated": 0, "unchanged": 11}


def test_changed_document_is_reindexed_and_audited(db, tmp_path):
    for f in DOCS_DIR.glob("*.md"):
        shutil.copy(f, tmp_path / f.name)
    path = tmp_path / "SOP-ITO-001.md"
    path.write_text(path.read_text().replace('version: "2.0"', 'version: "2.1"')
                    .replace("within 15 minutes", "within 10 minutes"))
    assert index_documents(db, tmp_path) == {"new": 0, "updated": 1, "unchanged": 10}
    doc = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.doc_id == "SOP-ITO-001")).one()
    assert doc.version == "2.1" and any("10 minutes" in c.text for c in doc.chunks)
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "knowledge.document_updated")).one()
    details = json.loads(event.details)
    assert (details["previous_version"], details["version"]) == ("2.0", "2.1")


@pytest.mark.parametrize("text,error", [
    ("# no front matter", "missing front matter"),
    ("---\ndoc_id: X\n---\n## 1 A\ntext", "missing front matter fields"),
    ("---\ndoc_id: X\ntitle: T\ntype: sop\nversion: 1\n---\nno sections", "no numbered sections"),
])
def test_malformed_documents_are_rejected(text, error):
    with pytest.raises(DocumentFormatError, match=error):
        parse_document(text)


def test_retrieval_evaluation(db):
    """Validation of the retrieval step against app/knowledge/evaluation.csv (runs in CI)."""
    idx = get_index(db)
    rows = list(csv.DictReader(EVALUATION_FILE.open()))
    in_scope = [r for r in rows if r["expected_doc"]]
    doc_hits = section_hits = 0
    misses = []
    for r in in_scope:
        top = idx.search(r["question"], k=3)
        if any(p.doc_id == r["expected_doc"] for p in top):
            doc_hits += 1
        else:
            misses.append((r["id"], [p.ref for p in top]))
        section_hits += any(p.doc_id == r["expected_doc"] and p.section == r["expected_section"] for p in top)
    assert doc_hits / len(in_scope) >= 0.9, misses
    assert section_hits / len(in_scope) >= 0.8
    for r in rows:
        if not r["expected_doc"]:
            assert idx.search(r["question"], k=3) == [], r["question"]


def test_knowledge_api(client, login):
    v = login("viewer")
    docs = client.get("/api/knowledge/documents", headers=v).json()
    assert {d["doc_type"] for d in docs} == {"sop", "runbook", "regulation"}
    sop = client.get("/api/knowledge/documents/SOP-ITO-002", headers=v).json()
    assert sop["version"] == "3.1" and sop["sections"][4]["heading"] == "Approval"
    assert client.get("/api/knowledge/documents/SOP-XXX-001", headers=v).status_code == 404
