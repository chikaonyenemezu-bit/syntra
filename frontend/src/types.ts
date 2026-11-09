export type Role = "viewer" | "it_ops" | "system_owner" | "qa" | "admin";
export type SystemStatus = "operational" | "degraded" | "down" | "unknown";
export type IncidentStatus = "open" | "acknowledged" | "resolved" | "closed";
export type Severity = "low" | "medium" | "high" | "critical";
export type FaultMode = "degraded" | "down" | "silent" | null;

export interface User {
  username: string;
  full_name: string;
  role: Role;
}

export interface System {
  id: number;
  code: string;
  name: string;
  system_type: string;
  description: string;
  gxp_relevant: boolean;
  gamp_category: number | null;
  owner: string;
  status: SystemStatus;
  status_reason: string;
  last_heartbeat_at: string | null;
  simulated_fault: FaultMode;
}

export interface Telemetry {
  received_at: string;
  reported_status: string;
  latency_ms: number;
  error_rate: number;
  message: string;
}

export interface Incident {
  id: number;
  number: string;
  system_code: string | null;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  source: string;
  gxp_impact: boolean;
  opened_at: string;
  opened_by: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
  closed_at: string | null;
  closed_by: string | null;
  recovered_at: string | null;
}

export interface AuditEvent {
  id: number;
  occurred_at: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details: string;
  prev_hash: string;
  hash: string;
}

export interface Summary {
  systems_total: number;
  systems_by_status: Record<string, number>;
  incidents_active: number;
  incidents_critical_active: number;
  incidents_awaiting_closure: number;
}

export interface ChainCheck {
  valid: boolean;
  records_checked: number;
  first_broken_id: number | null;
  reason: string | null;
}

// --- Integrations (step 3) ---------------------------------------------------

export type SyncSource = "live" | "sample" | "sample_with_errors";
export type JobStatus = "running" | "succeeded" | "partial" | "failed";

export interface IngestionJob {
  id: number;
  number: string;
  trigger: string;
  source: SyncSource;
  source_detail: string;
  triggered_by: string;
  status: JobStatus;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  fetched: number;
  inserted: number;
  updated: number;
  unchanged: number;
  rejected: number;
  error_message: string | null;
}

export interface RejectedRecord {
  id: number;
  record_key: string;
  reasons: string[];
  payload: Record<string, unknown> | unknown[] | string;
  rejected_at: string;
}

export interface IngestionJobDetail extends IngestionJob {
  rejected_records: RejectedRecord[];
}

export interface Integration {
  system: System;
  last_job: IngestionJob | null;
  sync_enabled: boolean;
  sync_interval_minutes: number;
  lookback_days: number;
  rejection_threshold: number;
  recalls_total: number;
}

export interface Recall {
  recall_number: string;
  event_id: string | null;
  classification: "Class I" | "Class II" | "Class III";
  status: string;
  product_type: string;
  product_description: string;
  reason_for_recall: string;
  recalling_firm: string;
  city: string | null;
  state: string | null;
  country: string | null;
  distribution_pattern: string | null;
  code_info: string | null;
  product_quantity: string | null;
  voluntary_mandated: string | null;
  recall_initiation_date: string | null;
  report_date: string;
  termination_date: string | null;
  source: string;
  first_seen_at: string;
  updated_at: string;
}

export interface RecallPage {
  total: number;
  items: Recall[];
}

// --- GxP lifecycle (step 4) ----------------------------------------------------

export type ValidationStatus = "not_validated" | "in_validation" | "validated" | "retired";
export type ReviewState = "ok" | "due_soon" | "overdue" | "not_applicable";
export type ChangeStatus = "draft" | "in_review" | "approved" | "implemented" | "verified" | "rejected";

export interface ESignature {
  id: number;
  signer: string;
  signer_name: string;
  signer_role: string;
  meaning: string;
  comment: string;
  signed_at: string;
}

export interface Lifecycle {
  system: System;
  risk_class: "high" | "medium" | "low";
  current_version: string;
  validated_version: string | null;
  validation_status: ValidationStatus;
  validated_on: string | null;
  validation_report: string | null;
  periodic_review_months: number;
  last_review_on: string | null;
  last_review_outcome: string | null;
  next_review_due: string | null;
  review_state: ReviewState;
  open_changes: number;
}

export interface PeriodicReview {
  number: string;
  reviewed_on: string;
  outcome: "remains_validated" | "remediation_required";
  summary: string;
  reviewer: string;
  signature: ESignature | null;
}

export interface LifecycleDetail extends Lifecycle {
  reviews: PeriodicReview[];
}

export interface ChangeRequest {
  id: number;
  number: string;
  system_code: string;
  title: string;
  description: string;
  justification: string;
  impact_assessment: string;
  category: "minor" | "major";
  risk: "low" | "medium" | "high";
  requires_revalidation: boolean;
  target_version: string | null;
  status: ChangeStatus;
  requested_by: string;
  created_at: string;
  submitted_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  rejected_by: string | null;
  rejection_reason: string | null;
  implemented_at: string | null;
  implemented_by: string | null;
  implementation_note: string | null;
  verified_at: string | null;
  verified_by: string | null;
  verification_evidence: string | null;
  required_approvals: string[];
  pending_approvals: string[];
  signatures: ESignature[];
}

export interface NewChange {
  system_code: string;
  title: string;
  description: string;
  justification: string;
  impact_assessment: string;
  category: "minor" | "major";
  risk: "low" | "medium" | "high";
  requires_revalidation: boolean;
  target_version: string | null;
}

// --- Knowledge Assistant (step 5) ----------------------------------------------

export interface AssistantStatus {
  mode: "llm" | "retrieval";
  provider: "anthropic" | "openai" | "groq" | null;
  model: string | null;
  documents: number;
  sections: number;
}

export interface Citation {
  ref: string;
  doc_id: string;
  section: string;
  valid: boolean;
  title: string | null;
  heading: string | null;
  version: string | null;
  excerpt: string | null;
}

export interface Passage {
  ref: string;
  doc_id: string;
  section: string;
  title: string;
  heading: string;
  version: string;
  excerpt: string;
  score: number;
}

export interface ToolCall {
  name: string;
  input: Record<string, unknown>;
  summary: string;
  ok: boolean;
}

export interface AssistantAnswer {
  number: string;
  asked_by: string;
  asked_at: string;
  question: string;
  mode: "llm" | "retrieval";
  provider: string | null;
  model: string | null;
  answer: string | null;
  citations: Citation[];
  tool_calls: ToolCall[];
  passages: Passage[];
  grounded: boolean;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  error: string | null;
  feedback: "helpful" | "incorrect" | null;
  feedback_comment: string | null;
}

export interface KnowledgeDoc {
  doc_id: string;
  title: string;
  doc_type: "sop" | "runbook" | "regulation";
  version: string;
  effective: string | null;
  owner: string;
  source: string | null;
  indexed_at: string;
  section_count: number;
}

export interface KnowledgeDocDetail extends KnowledgeDoc {
  sections: { section: string; heading: string; text: string }[];
}
