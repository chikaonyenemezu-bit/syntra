import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models._time import utcnow
from app.models.knowledge import AssistantQuery, KnowledgeChunk, KnowledgeDocument
from app.models.user import User
from app.schemas import (AskRequest, AssistantAnswerOut, AssistantStatusOut, FeedbackRequest, KnowledgeDocDetail,
                         KnowledgeDocOut, KnowledgeSectionOut)
from app.security import get_current_user
from app.services import assistant
from app.services.audit_logger import log_event

router = APIRouter(prefix="/api/assistant", tags=["knowledge assistant"])
knowledge_router = APIRouter(prefix="/api/knowledge", tags=["knowledge assistant"])


def to_out(q: AssistantQuery) -> AssistantAnswerOut:
    return AssistantAnswerOut(
        number=q.number, asked_by=q.asked_by, asked_at=q.asked_at, question=q.question, mode=q.mode,
        provider=q.provider, model=q.model, answer=q.answer, citations=json.loads(q.citations),
        tool_calls=json.loads(q.tool_calls), passages=json.loads(q.passages), grounded=q.grounded,
        latency_ms=q.latency_ms, input_tokens=q.input_tokens, output_tokens=q.output_tokens, error=q.error,
        feedback=q.feedback, feedback_comment=q.feedback_comment)


@router.get("/status", response_model=AssistantStatusOut)
def get_status(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return AssistantStatusOut(**assistant.status(),
                              documents=db.scalar(select(func.count()).select_from(KnowledgeDocument)) or 0,
                              sections=db.scalar(select(func.count()).select_from(KnowledgeChunk)) or 0)


@router.post("/ask", response_model=AssistantAnswerOut)
def ask(body: AskRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = assistant.ask(db, user, body.question, [t.model_dump() for t in body.history])
    db.commit()
    return to_out(q)


@router.get("/queries", response_model=list[AssistantAnswerOut])
def my_queries(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    rows = db.scalars(select(AssistantQuery).where(AssistantQuery.asked_by == user.username)
                      .order_by(AssistantQuery.id.desc()).limit(limit)).all()
    return [to_out(q) for q in reversed(rows)]


@router.post("/queries/{number}/feedback", response_model=AssistantAnswerOut)
def feedback(number: str, body: FeedbackRequest, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    q = db.scalars(select(AssistantQuery).where(AssistantQuery.number == number)).first()
    if q is None:
        raise HTTPException(status_code=404, detail=f"{number} not found")
    if q.asked_by != user.username:
        raise HTTPException(status_code=403, detail="Only the person who asked can rate an answer")
    q.feedback, q.feedback_comment, q.feedback_at = body.rating, body.comment.strip() or None, utcnow()
    log_event(db, actor=user.username, action="assistant.feedback", entity_type="assistant_query", entity_id=number,
              details={"rating": body.rating, "comment": q.feedback_comment})
    db.commit()
    return to_out(q)


def _doc_out(d: KnowledgeDocument, cls=KnowledgeDocOut, **extra):
    return cls(doc_id=d.doc_id, title=d.title, doc_type=d.doc_type, version=d.version, effective=d.effective,
               owner=d.owner, source=d.source, indexed_at=d.indexed_at, section_count=len(d.chunks), **extra)


@knowledge_router.get("/documents", response_model=list[KnowledgeDocOut])
def list_documents(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    docs = db.scalars(select(KnowledgeDocument).options(selectinload(KnowledgeDocument.chunks))
                      .order_by(KnowledgeDocument.doc_type.desc(), KnowledgeDocument.doc_id)).all()
    return [_doc_out(d) for d in docs]


@knowledge_router.get("/documents/{doc_id}", response_model=KnowledgeDocDetail)
def get_document(doc_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    d = db.scalars(select(KnowledgeDocument).options(selectinload(KnowledgeDocument.chunks))
                   .where(KnowledgeDocument.doc_id == doc_id)).first()
    if d is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return _doc_out(d, KnowledgeDocDetail, sections=[KnowledgeSectionOut(section=c.section, heading=c.heading,
                                                                         text=c.text) for c in d.chunks])
