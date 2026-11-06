from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._time import utcnow


class KnowledgeDocument(Base):
    """A controlled document the assistant may answer from (SOP, runbook, regulatory notes)."""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)   # SOP-ITO-001
    title: Mapped[str] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(String(16))   # sop | runbook | regulation
    version: Mapped[str] = mapped_column(String(16))
    effective: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner: Mapped[str] = mapped_column(String(128), default="")
    source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", order_by="KnowledgeChunk.position", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    """One numbered section of a document: the unit that is retrieved and cited."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    section: Mapped[str] = mapped_column(String(16))    # "4" or "4.2"
    heading: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")

    @property
    def ref(self) -> str:
        return f"{self.document.doc_id} §{self.section}"


class AssistantQuery(Base):
    """Record of every question to the assistant: what was asked, what sources and live data were used,
    what was answered, by which model. Kept for review of AI use (GxP traceability of AI output)."""

    __tablename__ = "assistant_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True, index=True, default="")
    asked_by: Mapped[str] = mapped_column(String(64), index=True)
    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    question: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(16))          # llm | retrieval
    provider: Mapped[str | None] = mapped_column(String(16), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[str] = mapped_column(Text, default="[]")    # JSON
    tool_calls: Mapped[str] = mapped_column(Text, default="[]")   # JSON
    passages: Mapped[str] = mapped_column(Text, default="[]")     # JSON: sources the model was given
    grounded: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String(16), nullable=True)   # helpful | incorrect
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
