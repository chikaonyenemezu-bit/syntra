import { label } from "../../format";

const TONE: Record<string, string> = {
  operational: "ok", resolved: "ok", closed: "muted",
  degraded: "warn", medium: "warn", acknowledged: "info",
  down: "bad", critical: "bad", high: "bad", open: "bad",
  unknown: "muted", low: "muted",
  succeeded: "ok", partial: "warn", failed: "bad", running: "info",
  "Class I": "bad", "Class II": "warn", "Class III": "muted",
};

export function StatusBadge({ value }: { value: string }) {
  return <span className={`badge badge-${TONE[value] ?? "muted"}`}>{label(value)}</span>;
}
