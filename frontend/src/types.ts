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
