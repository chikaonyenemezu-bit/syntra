import { useEffect, useState } from "react";
import { useEscape } from "../shared/useEscape";
import { api } from "../../services/api";
import { can } from "../../permissions";
import { fmtDate } from "../../format";
import type { ChangeRequest, LifecycleDetail, User } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";
import { SignatureDialog } from "../shared/SignatureDialog";
import { REVIEW_TEXT } from "./SystemInventory";
import { SignatureLine } from "./SignatureLine";

interface Props {
  code: string;
  user: User;
  changes: ChangeRequest[];
  onClose: () => void;
  onChanged: () => void;
  onOpenChange: (number: string) => void;
}

export function SystemPanel({ code, user, changes, onClose, onChanged, onOpenChange }: Props) {
  const [lc, setLc] = useState<LifecycleDetail | null>(null);
  const [outcome, setOutcome] = useState<"remains_validated" | "remediation_required">("remains_validated");
  const [signing, setSigning] = useState(false);
  useEscape(onClose, !signing);

  useEffect(() => { api.lifecycleDetail(code).then(setLc).catch(() => setLc(null)); }, [code]);
  if (!lc) return null;
  const systemChanges = changes.filter((c) => c.system_code === code);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="sys-title" onClick={(e) => e.stopPropagation()}>
        <header className="drawer-head">
          <div>
            <div className="system-code">{lc.system.code} · GAMP {lc.system.gamp_category ?? "–"}</div>
            <h2 id="sys-title">{lc.system.name}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">×</button>
        </header>
        <div className="tags">
          <StatusBadge value={lc.validation_status} />
          <StatusBadge value={lc.review_state} text={`Review: ${REVIEW_TEXT[lc.review_state]}`} />
          <span className="tag">Risk: {lc.risk_class}</span>
          <span className="tag">Owner: {lc.system.owner}</span>
        </div>
        <p className="muted small">{lc.system.description}</p>

        <dl className="facts">
          <div><dt>Running version</dt><dd>{lc.current_version}</dd></div>
          <div><dt>Validated version</dt>
            <dd className={lc.validated_version !== lc.current_version ? "warn-text" : undefined}>{lc.validated_version ?? "none"}</dd></div>
          <div><dt>Validated on</dt><dd>{fmtDate(lc.validated_on)}</dd></div>
          <div><dt>Validation reference</dt><dd>{lc.validation_report ?? "–"}</dd></div>
          <div><dt>Review interval</dt><dd>{lc.periodic_review_months} months</dd></div>
          <div><dt>Last periodic review</dt><dd>{fmtDate(lc.last_review_on)}</dd></div>
          <div><dt>Next review due</dt><dd>{fmtDate(lc.next_review_due)}</dd></div>
        </dl>
        <p className="small muted">
          The validation state changes only through a verified change request or a signed periodic review.
        </p>

        {can.periodicReview(user, lc) && (
          <section className="actions">
            <h3>Record periodic review</h3>
            <label>Outcome
              <select value={outcome} onChange={(e) => setOutcome(e.target.value as typeof outcome)}>
                <option value="remains_validated">System remains in a validated state</option>
                <option value="remediation_required">Remediation required</option>
              </select>
            </label>
            <button className="primary" onClick={() => setSigning(true)}>Sign periodic review…</button>
          </section>
        )}

        <section>
          <h3>Periodic reviews</h3>
          {lc.reviews.length === 0 ? <p className="small muted">No periodic review recorded in Syntra yet.</p> : (
            <ul className="plain-list">
              {lc.reviews.map((r) => (
                <li key={r.number}>
                  <div className="row"><code>{r.number}</code><span className="small muted">{fmtDate(r.reviewed_on)}</span></div>
                  <p className="small">{r.summary}</p>
                  {r.signature && <SignatureLine sig={r.signature} showComment={false} />}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h3>Change requests</h3>
          {systemChanges.length === 0 ? <p className="small muted">None.</p> : (
            <ul className="plain-list">
              {systemChanges.map((c) => (
                <li key={c.number} className="row">
                  <button className="link" onClick={() => onOpenChange(c.number)}>{c.number}</button>
                  <span className="grow-text">{c.title}</span>
                  <StatusBadge value={c.status} />
                </li>
              ))}
            </ul>
          )}
        </section>

        {signing && (
          <SignatureDialog
            user={user}
            title={`Periodic review of ${lc.system.code}`}
            meaning={outcome === "remains_validated" ? "Reviewed (QA): remains validated" : "Reviewed (QA): remediation required"}
            textLabel="Review summary (scope and findings)" textMin={20}
            textPlaceholder="e.g. Reviewed user access, audit trail, backup/restore, incidents and changes since last review; no findings."
            onCancel={() => setSigning(false)}
            onSign={async (password, summary) => {
              setLc(await api.recordReview(code, { outcome, summary, password }));
              setSigning(false);
              onChanged();
            }}
          />
        )}
      </aside>
    </div>
  );
}
