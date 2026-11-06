// Mirrors the backend rules so buttons only appear when the action is allowed.
// The backend still enforces every rule; this is only for a clearer UI.
import type { Incident, User } from "./types";

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
};

export function closeBlockedReason(u: User, i: Incident): string | null {
  if (i.status !== "resolved") return null;
  if (u.username === i.resolved_by) return "You resolved this incident; someone else must close it (four-eyes).";
  if (i.gxp_impact && u.role !== "qa") return "GxP incident: closure by QA required.";
  return null;
}
