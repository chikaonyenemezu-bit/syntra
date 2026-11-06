from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.incident import Severity


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    username: str
    full_name: str
    role: str


class SystemOut(ORM):
    id: int
    code: str
    name: str
    system_type: str
    description: str
    gxp_relevant: bool
    gamp_category: int | None
    owner: str
    status: str
    status_reason: str
    last_heartbeat_at: datetime | None
    simulated_fault: str | None


class TelemetryOut(ORM):
    received_at: datetime
    reported_status: str
    latency_ms: int
    error_rate: float
    message: str


class IncidentOut(ORM):
    id: int
    number: str
    system_code: str | None = None
    title: str
    description: str
    severity: str
    status: str
    source: str
    gxp_impact: bool
    opened_at: datetime
    opened_by: str
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None
    resolved_by: str | None
    resolution_note: str | None
    closed_at: datetime | None
    closed_by: str | None
    recovered_at: datetime | None


class IncidentCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(default="", max_length=4000)
    severity: Severity = Severity.MEDIUM
    system_code: str | None = None


class ResolveRequest(BaseModel):
    note: str = Field(min_length=10, max_length=4000)


class FaultRequest(BaseModel):
    mode: Literal["degraded", "down", "silent"] | None = None


class AuditEventOut(ORM):
    id: int
    occurred_at: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    details: str
    prev_hash: str
    hash: str


class ChainCheckOut(BaseModel):
    valid: bool
    records_checked: int
    first_broken_id: int | None
    reason: str | None


class MonitoringSummary(BaseModel):
    systems_total: int
    systems_by_status: dict[str, int]
    incidents_active: int
    incidents_critical_active: int
    incidents_awaiting_closure: int


# --- Integrations (step 3) -------------------------------------------------

class IngestionJobOut(ORM):
    id: int
    number: str
    trigger: str
    source: str
    source_detail: str
    triggered_by: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    fetched: int
    inserted: int
    updated: int
    unchanged: int
    rejected: int
    error_message: str | None


class RejectedRecordOut(BaseModel):
    id: int
    record_key: str
    reasons: list[str]
    payload: dict | list | str
    rejected_at: datetime


class IngestionJobDetail(IngestionJobOut):
    rejected_records: list[RejectedRecordOut] = []


class IntegrationOut(BaseModel):
    system: SystemOut
    last_job: IngestionJobOut | None
    sync_enabled: bool
    sync_interval_minutes: int
    lookback_days: int
    rejection_threshold: float
    recalls_total: int


class SyncRequest(BaseModel):
    source: Literal["live", "sample", "sample_with_errors"] = "live"


class RecallOut(ORM):
    recall_number: str
    event_id: str | None
    classification: str
    status: str
    product_type: str
    product_description: str
    reason_for_recall: str
    recalling_firm: str
    city: str | None
    state: str | None
    country: str | None
    distribution_pattern: str | None
    code_info: str | None
    product_quantity: str | None
    voluntary_mandated: str | None
    recall_initiation_date: date | None
    report_date: date
    termination_date: date | None
    source: str
    first_seen_at: datetime
    updated_at: datetime


class RecallPage(BaseModel):
    total: int
    items: list[RecallOut]


# --- GxP lifecycle (step 4) --------------------------------------------------

class ESignatureOut(ORM):
    id: int
    signer: str
    signer_name: str
    signer_role: str
    meaning: str
    comment: str
    signed_at: datetime


class LifecycleOut(BaseModel):
    system: SystemOut
    risk_class: str
    current_version: str
    validated_version: str | None
    validation_status: str
    validated_on: date | None
    validation_report: str | None
    periodic_review_months: int
    last_review_on: date | None
    last_review_outcome: str | None
    next_review_due: date | None
    review_state: str
    open_changes: int


class PeriodicReviewOut(ORM):
    number: str
    reviewed_on: date
    outcome: str
    summary: str
    reviewer: str
    signature: ESignatureOut | None = None


class LifecycleDetail(LifecycleOut):
    reviews: list[PeriodicReviewOut] = []


class PeriodicReviewCreate(BaseModel):
    outcome: Literal["remains_validated", "remediation_required"]
    summary: str = Field(min_length=20, max_length=4000)
    password: str = Field(min_length=1, max_length=200)


class ChangeFields(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(default="", max_length=8000)
    justification: str = Field(default="", max_length=4000)
    impact_assessment: str = Field(default="", max_length=8000)
    category: Literal["minor", "major"] = "minor"
    risk: Literal["low", "medium", "high"] = "low"
    requires_revalidation: bool | None = None
    target_version: str | None = Field(default=None, max_length=32)


class ChangeCreate(ChangeFields):
    system_code: str


class ChangeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    justification: str | None = Field(default=None, max_length=4000)
    impact_assessment: str | None = Field(default=None, max_length=8000)
    category: Literal["minor", "major"] | None = None
    risk: Literal["low", "medium", "high"] | None = None
    requires_revalidation: bool | None = None
    target_version: str | None = Field(default=None, max_length=32)


class ChangeOut(ORM):
    id: int
    number: str
    system_code: str = ""
    title: str
    description: str
    justification: str
    impact_assessment: str
    category: str
    risk: str
    requires_revalidation: bool
    target_version: str | None
    status: str
    requested_by: str
    created_at: datetime
    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    rejected_by: str | None
    rejection_reason: str | None
    implemented_at: datetime | None
    implemented_by: str | None
    implementation_note: str | None
    verified_at: datetime | None
    verified_by: str | None
    verification_evidence: str | None
    required_approvals: list[str] = []
    pending_approvals: list[str] = []
    signatures: list[ESignatureOut] = []


class SignRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    comment: str = Field(default="", max_length=4000)


class RejectRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=10, max_length=4000)


class ImplementRequest(BaseModel):
    note: str = Field(min_length=10, max_length=4000)


class VerifyRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    evidence: str = Field(min_length=10, max_length=4000)


# --- Knowledge Assistant (step 5) --------------------------------------------

class AssistantStatusOut(BaseModel):
    mode: str            # llm | retrieval
    provider: str | None
    model: str | None
    documents: int
    sections: int


class HistoryTurn(BaseModel):
    question: str = Field(max_length=2000)
    answer: str = Field(max_length=8000)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=4)


class CitationOut(BaseModel):
    ref: str
    doc_id: str
    section: str
    valid: bool
    title: str | None
    heading: str | None
    version: str | None
    excerpt: str | None


class PassageOut(BaseModel):
    ref: str
    doc_id: str
    section: str
    title: str
    heading: str
    version: str
    excerpt: str
    score: float


class ToolCallOut(BaseModel):
    name: str
    input: dict
    summary: str
    ok: bool


class AssistantAnswerOut(BaseModel):
    number: str
    asked_by: str
    asked_at: datetime
    question: str
    mode: str
    provider: str | None
    model: str | None
    answer: str | None
    citations: list[CitationOut]
    tool_calls: list[ToolCallOut]
    passages: list[PassageOut]
    grounded: bool
    latency_ms: int
    input_tokens: int
    output_tokens: int
    error: str | None
    feedback: str | None
    feedback_comment: str | None


class FeedbackRequest(BaseModel):
    rating: Literal["helpful", "incorrect"]
    comment: str = Field(default="", max_length=2000)


class KnowledgeSectionOut(BaseModel):
    section: str
    heading: str
    text: str


class KnowledgeDocOut(BaseModel):
    doc_id: str
    title: str
    doc_type: str
    version: str
    effective: date | None
    owner: str
    source: str | None
    indexed_at: datetime
    section_count: int


class KnowledgeDocDetail(KnowledgeDocOut):
    sections: list[KnowledgeSectionOut]
