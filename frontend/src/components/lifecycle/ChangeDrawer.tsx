import { useEffect, useState } from "react";
import { api, ApiError } from "../../services/api";
import { can } from "../../permissions";
import { fmtTime, label, ROLE_LABEL } from "../../format";
import type { AuditEvent, ChangeRequest, User } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";
import { SignatureDialog } from "../shared/SignatureDialog";
import { SignatureLine } from "./SignatureLine";

type Dialog = "approve" | "reject" | "verify" | null;

interface Props {
  number: string;
  user: User;
  onClose: () => void;
  onChanged: () => void;
}

export function ChangeDrawer({ number, user, onClose, onChanged }: Props) {
  const [cr, setCr] = useState<ChangeRequest | null>(null);
  const [history, setHistory] = useState<AuditEvent[]>([]);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.change(number).then(setCr).catch(() => setCr(null)); }, [number]);
  useEffect(() => {
    if (!can.viewAudit(user)) return;
    api.audit({ entity_type: "change_request", entity_id: number })
      .then((h) => setHistory([...h].reverse())).catch(() => undefined);
  }, [number, cr?.status, cr?.signatures.length, user]);

  if (!cr) return null;

  const update = (c: ChangeRequest) => { setCr(c); setDialog(null); onChanged(); };
  async function act(fn: () => Promise<ChangeRequest>) {
    setBusy(true); setError(null);
    try { update(await fn()); setNote(""); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Action failed"); }
    finally { setBusy(false); }
  }

  const qaCannotVerify = cr.status === "implemented" && user.role === "qa" && !can.verifyChange(user, cr);
  const draftOfSomeoneElse = cr.status === "draft" && user.username !== cr.requested_by;
  const hasActions = can.submitChange(user, cr) || can.approveChange(user, cr) || can.rejectChange(user, cr)
    || can.implementChange(user, cr) || can.verifyChange(user, cr) || qaCannotVerify || draftOfSomeoneElse || !!error;

  const signedBy = (role: string) =>
    cr.signatures.find((s) => s.meaning.startsWith("Approved") && s.signer_role === role);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="cr-title" onClick={(e) => e.stopPropagation()}>
        <header className="drawer-head">
          <div>
            <div className="system-code">{cr.number} · {cr.system_code}</div>
            <h2 id="cr-title">{cr.title}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">×</button>
        </header>
        <div className="tags">
          <StatusBadge value={cr.status} />
          <span className="tag">{cr.category === "major" ? "Major change" : "Minor change"}</span>
          <StatusBadge value={cr.risk} text={`Risk: ${cr.risk}`} />
          {cr.requires_revalidation && <span className="tag">Requires revalidation</span>}
          {cr.target_version && <span className="tag">Target version {cr.target_version}</span>}
        </div>

        <dl className="cr-text">
          <div><dt>Description</dt><dd>{cr.description || "–"}</dd></div>
          <div><dt>Justification</dt><dd>{cr.justification || "–"}</dd></div>
          <div><dt>Impact assessment</dt><dd>{cr.impact_assessment || "–"}</dd></div>
          {cr.implementation_note && <div><dt>Implementation ({cr.implemented_by})</dt><dd>{cr.implementation_note}</dd></div>}
          {cr.verification_evidence && <div><dt>Verification evidence ({cr.verified_by})</dt><dd>{cr.verification_evidence}</dd></div>}
          {cr.rejection_reason && <div><dt>Rejection reason ({cr.rejected_by})</dt><dd>{cr.rejection_reason}</dd></div>}
        </dl>

        <section>
          <h3>Required approvals</h3>
          <ul className="approvals">
            {cr.required_approvals.map((role) => {
              const s = signedBy(role);
              return (
                <li key={role} className={s ? "approved" : undefined}>
                  <span>{ROLE_LABEL[role] ?? role}</span>
                  {s ? <span className="small ok-text">Signed by {s.signer_name}</span>
                     : <span className="small muted">{cr.status === "draft" ? "After submission" : cr.status === "in_review" ? "Pending" : "Not signed"}</span>}
                </li>
              );
            })}
          </ul>
        </section>

        {hasActions && <section className="actions">
          {can.submitChange(user, cr) && (
            <button className="primary" disabled={busy} onClick={() => act(() => api.submitChange(cr.number))}>
              Submit for approval
            </button>
          )}
          {(can.approveChange(user, cr) || can.rejectChange(user, cr)) && (
            <div className="row">
              {can.approveChange(user, cr) && <button className="primary" onClick={() => setDialog("approve")}>Approve…</button>}
              {can.rejectChange(user, cr) && <button onClick={() => setDialog("reject")}>Reject…</button>}
            </div>
          )}
          {can.implementChange(user, cr) && (
            <div className="resolve">
              <label htmlFor="impl">Implementation note (what was deployed, when, how it was checked)</label>
              <textarea id="impl" rows={3} value={note} onChange={(e) => setNote(e.target.value)}
                        placeholder="e.g. Deployed 3.3.0 in the Saturday maintenance window; installation checks passed." />
              <button disabled={busy || note.trim().length < 10} onClick={() => act(() => api.implementChange(cr.number, note))}>
                Mark as implemented
              </button>
            </div>
          )}
          {can.verifyChange(user, cr) && <button className="primary" onClick={() => setDialog("verify")}>Verify…</button>}
          {draftOfSomeoneElse && <p className="small muted">Draft: only {cr.requested_by} can submit it.</p>}
          {qaCannotVerify &&
            <p className="small muted">You requested or implemented this change; another QA member must verify it.</p>}
          {error && <p className="error" role="alert">{error}</p>}
        </section>}

        {cr.signatures.length > 0 && (
          <section>
            <h3>Electronic signatures</h3>
            <div className="signatures">{cr.signatures.map((s) => <SignatureLine key={s.id} sig={s} />)}</div>
          </section>
        )}

        {can.viewAudit(user) && history.length > 0 && (
          <section>
            <h3>Audit history</h3>
            <ol className="timeline">
              {history.map((e) => (
                <li key={e.id}>
                  <div className="timeline-head">
                    <strong>{label(e.action.replace("change.", "").replace("esign.", "signature "))}</strong>
                    <span className="muted small">{fmtTime(e.occurred_at)} · {e.actor}</span>
                  </div>
                  <code className="hash" title={e.hash}>#{e.hash.slice(0, 12)}</code>
                </li>
              ))}
            </ol>
          </section>
        )}

        {dialog === "approve" && (
          <SignatureDialog user={user} title={`Approve ${cr.number}`}
            meaning={`Approved (${ROLE_LABEL[user.role]})`} textLabel="Comment" textMin={0}
            onCancel={() => setDialog(null)}
            onSign={async (pw, comment) => update(await api.approveChange(cr.number, pw, comment))} />
        )}
        {dialog === "reject" && (
          <SignatureDialog user={user} title={`Reject ${cr.number}`}
            meaning={`Rejected (${ROLE_LABEL[user.role]})`} textLabel="Reason for rejection" textMin={10}
            onCancel={() => setDialog(null)}
            onSign={async (pw, reason) => update(await api.rejectChange(cr.number, pw, reason))} />
        )}
        {dialog === "verify" && (
          <SignatureDialog user={user} title={`Verify ${cr.number}`}
            meaning="Verified (QA)" textLabel="Verification evidence" textMin={10}
            textPlaceholder="e.g. Test protocol TP-2026-031 executed, all test cases passed; deviations: none."
            onCancel={() => setDialog(null)}
            onSign={async (pw, evidence) => update(await api.verifyChange(cr.number, pw, evidence))} />
        )}
      </aside>
    </div>
  );
}
