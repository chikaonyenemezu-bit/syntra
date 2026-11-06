export function fmtTime(iso: string | null): string {
  if (!iso) return "–";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return d.toLocaleString(undefined, {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

export function ago(iso: string | null): string {
  if (!iso) return "never";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  const s = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  return `${Math.round(s / 3600)} h ago`;
}

export const label = (s: string) => s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

export function fmtDate(iso: string | null): string {
  if (!iso) return "–";
  return new Date(iso.length === 10 ? iso + "T00:00:00" : iso).toLocaleDateString(undefined, {
    day: "2-digit", month: "2-digit", year: "numeric",
  });
}

export const ROLE_LABEL: Record<string, string> = {
  system_owner: "System Owner", qa: "QA", it_ops: "IT Operations", admin: "Administrator", viewer: "Viewer",
};
