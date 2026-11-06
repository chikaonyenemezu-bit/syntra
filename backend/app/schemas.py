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
