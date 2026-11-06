import { label } from "../../format";

const TONE: Record<string, string> = {
  operational: "ok", resolved: "ok", closed: "muted",
  degraded: "warn", medium: "warn", acknowledged: "info",
  down: "bad", critical: "bad", high: "bad", open: "bad",
  unknown: "muted", low: "muted",
  succeeded: "ok", partial: "warn", failed: "bad", running: "info",
  "Class I": "bad", "Class II": "warn", "Class III": "muted",
  validated: "ok", in_validation: "info", not_validated: "warn", retired: "muted",
  ok: "ok", due_soon: "warn", overdue: "bad", not_applicable: "muted",
  draft: "muted", in_review: "info", approved: "info", implemented: "warn", verified: "ok", rejected: "bad",
};

export function StatusBadge({ value, text }: { value: string; text?: string }) {
  return <span className={`badge badge-${TONE[value] ?? "muted"}`}>{text ?? label(value)}</span>;
}
