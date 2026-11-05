import { useEffect, useState } from "react";
import { api, ApiError } from "../../services/api";
import { can, closeBlockedReason } from "../../permissions";
import { fmtTime, label } from "../../format";
import type { AuditEvent, Incident, User } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

interface Props {
  incident: Incident;
  user: User;
  onClose: () => void;
  onChanged: (i: Incident) => void;
}

export function IncidentDrawer({ incident: inc, user, onClose, onChanged }: Props) {
  const [history, setHistory] = useState<AuditEvent[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!can.viewAudit(user)) return;
    api.audit({ entity_type: "incident", entity_id: inc.number })
      .then((h) => setHistory([...h].reverse()))
      .catch(() => undefined);
  }, [inc.number, inc.status, inc.recovered_at, user]);

  async function act(fn: () => Promise<Incident>) {
    setBusy(true); setError(null);
    try { onChanged(await fn()); setNote(""); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Action failed"); }
    finally { setBusy(false); }
  }

  const blocked = closeBlockedReason(user, inc);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title"
             onClick={(e) => e.stopPropagation()}>
        <header className="drawer-head">
          <div>
            <div className="system-code">{inc.number} · {inc.system_code ?? "No system"}</div>
            <h2 id="drawer-title">{inc.title}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">×</button>
        </header>

        <div className="tags">
          <StatusBadge value={inc.status} />
          <StatusBadge value={inc.severity} />
          {inc.gxp_impact && <span className="tag">GxP impact</span>}
          <span className="tag">Source: {inc.source}</span>
        </div>

        <p>{inc.description}</p>
        {inc.recovered_at && inc.status !== "closed" && (
          <p className="callout callout-ok">
            System recovered at {fmtTime(inc.recovered_at)}. The incident stays open until it is
            resolved and formally closed.
          </p>
        )}
        {inc.resolution_note && (
          <div className="callout"><strong>Resolution ({inc.resolved_by}):</strong> {inc.resolution_note}</div>
        )}

        <section className="actions">
          {can.acknowledge(user, inc) && (
            <button disabled={busy} onClick={() => act(() => api.acknowledge(inc.number))}>Acknowledge</button>
          )}
          {can.resolve(user, inc) && (
            <div className="resolve">
              <label htmlFor="note">Resolution note (root cause and action taken)</label>
              <textarea id="note" rows={3} value={note} onChange={(e) => setNote(e.target.value)}
                        placeholder="e.g. Restarted EBR application service; terminals reconnected. Root cause: …" />
              <button disabled={busy || note.trim().length < 10}
                      onClick={() => act(() => api.resolve(inc.number, note))}>Resolve</button>
            </div>
          )}
          {can.close(user, inc) && (
            <button className="primary" disabled={busy} onClick={() => act(() => api.close(inc.number))}>
              Close incident{inc.gxp_impact ? " (QA approval)" : ""}
            </button>
          )}
          {blocked && <p className="small muted">{blocked}</p>}
          {error && <p className="error" role="alert">{error}</p>}
        </section>

        {can.viewAudit(user) && (
          <section>
            <h3>Audit history</h3>
            <ol className="timeline">
              {history.map((e) => (
                <li key={e.id}>
                  <div className="timeline-head">
                    <strong>{label(e.action.replace("incident.", ""))}</strong>
                    <span className="muted small">{fmtTime(e.occurred_at)} · {e.actor}</span>
                  </div>
                  <code className="hash" title={e.hash}>#{e.hash.slice(0, 12)}</code>
                </li>
              ))}
            </ol>
          </section>
        )}
      </aside>
    </div>
  );
}
