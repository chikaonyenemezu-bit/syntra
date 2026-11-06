// Mirrors the backend rules so buttons only appear when the action is allowed.
// The backend still enforces every rule; this is only for a clearer UI.
import type { ChangeRequest, Incident, Lifecycle, User } from "./types";

export const can = {
  acknowledge: (u: User, i: Incident) => u.role === "it_ops" && i.status === "open",
  resolve: (u: User, i: Incident) => u.role === "it_ops" && (i.status === "open" || i.status === "acknowledged"),
  close: (u: User, i: Incident) =>
    i.status === "resolved" &&
    u.username !== i.resolved_by &&
    (i.gxp_impact ? u.role === "qa" : u.role === "it_ops" || u.role === "qa"),
  createIncident: (u: User) => ["it_ops", "system_owner", "qa"].includes(u.role),
  injectFault: (u: User) => u.role === "it_ops" || u.role === "admin",
  viewAudit: (u: User) => ["qa", "admin", "it_ops"].includes(u.role),
  verifyAudit: (u: User) => u.role === "qa" || u.role === "admin",
  syncIntegration: (u: User) => u.role === "it_ops" || u.role === "admin",
  createChange: (u: User) => ["it_ops", "system_owner", "qa"].includes(u.role),
  submitChange: (u: User, c: ChangeRequest) => c.status === "draft" && u.username === c.requested_by,
  approveChange: (u: User, c: ChangeRequest) =>
    c.status === "in_review" && c.pending_approvals.includes(u.role) && u.username !== c.requested_by,
  rejectChange: (u: User, c: ChangeRequest) =>
    c.status === "in_review" && c.required_approvals.includes(u.role) && u.username !== c.requested_by,
  implementChange: (u: User, c: ChangeRequest) => c.status === "approved" && u.role === "it_ops",
  verifyChange: (u: User, c: ChangeRequest) =>
    c.status === "implemented" && u.role === "qa" && u.username !== c.implemented_by && u.username !== c.requested_by,
  periodicReview: (u: User, l: Lifecycle) => u.role === "qa" && l.validation_status === "validated",
};

export function closeBlockedReason(u: User, i: Incident): string | null {
  if (i.status !== "resolved") return null;
  if (u.username === i.resolved_by) return "You resolved this incident; someone else must close it (four-eyes).";
  if (i.gxp_impact && u.role !== "qa") return "GxP incident: closure by QA required.";
  return null;
}

/** True when this user can move the change request forward right now. */
export function needsMyAction(u: User, c: ChangeRequest): boolean {
  return can.submitChange(u, c) || can.approveChange(u, c) || can.implementChange(u, c) || can.verifyChange(u, c);
}
