"""Load the controlled documents from disk into the database, one chunk per numbered section.

Documents are Markdown files with a small front matter block (doc_id, title, type, version, …).
A document is re-indexed only when its content changes; every new or changed document is recorded in
the audit trail with its version, so it is always known which version an answer was based on.
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge import DOCS_DIR
from app.models._time import utcnow
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.audit_logger import log_event

HEADING = re.compile(r"^##\s+(\d+(?:\.\d+)*)\s+(.+?)\s*$")
REQUIRED_META = ("doc_id", "title", "type", "version")


class DocumentFormatError(ValueError):
    pass


@dataclass
class ParsedDocument:
    meta: dict
    sections: list[tuple[str, str, str]]  # (section, heading, text)
    content_hash: str


def parse_document(text: str, name: str = "") -> ParsedDocument:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise DocumentFormatError(f"{name}: missing front matter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise DocumentFormatError(f"{name}: front matter is not closed")
    meta = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    missing = [k for k in REQUIRED_META if not meta.get(k)]
    if missing:
        raise DocumentFormatError(f"{name}: missing front matter fields {missing}")

    sections, current, body = [], None, []
    for line in lines[end + 1:]:
        m = HEADING.match(line)
        if m:
            if current:
                sections.append((*current, "\n".join(body).strip()))
            current, body = (m.group(1), m.group(2)), []
        elif current:
            body.append(line)
    if current:
        sections.append((*current, "\n".join(body).strip()))
    if not sections:
        raise DocumentFormatError(f"{name}: no numbered sections ('## 1 Heading')")
    return ParsedDocument(meta, sections, hashlib.sha256(text.encode("utf-8")).hexdigest())


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def index_documents(db: Session, docs_dir: Path = DOCS_DIR) -> dict[str, int]:
    """Index all *.md files. Returns counts of new, updated and unchanged documents."""
    counts = {"new": 0, "updated": 0, "unchanged": 0}
    existing = {d.doc_id: d for d in db.scalars(select(KnowledgeDocument))}
    for path in sorted(docs_dir.glob("*.md")):
        parsed = parse_document(path.read_text(encoding="utf-8"), path.name)
        m = parsed.meta
        doc = existing.get(m["doc_id"])
        if doc and doc.content_hash == parsed.content_hash:
            counts["unchanged"] += 1
            continue
        if doc is None:
            doc = KnowledgeDocument(doc_id=m["doc_id"])
            db.add(doc)
            action, old_version = "knowledge.document_indexed", None
            counts["new"] += 1
        else:
            action, old_version = "knowledge.document_updated", doc.version
            doc.chunks.clear()
            db.flush()
            counts["updated"] += 1
        doc.title, doc.doc_type, doc.version = m["title"], m["type"], m["version"]
        doc.effective, doc.owner, doc.source = _date(m.get("effective")), m.get("owner", ""), m.get("source")
        doc.content_hash, doc.indexed_at = parsed.content_hash, utcnow()
        doc.chunks = [KnowledgeChunk(position=i, section=s, heading=h, text=t)
                      for i, (s, h, t) in enumerate(parsed.sections)]
        db.flush()
        log_event(db, actor="system", action=action, entity_type="document", entity_id=doc.doc_id,
                  details={"title": doc.title, "version": doc.version, "previous_version": old_version,
                           "sections": len(parsed.sections), "sha256": parsed.content_hash})
    db.commit()
    return counts
