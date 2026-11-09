
import { useEffect, useState } from "react";
import { useEscape } from "../shared/useEscape";
import {
  api,
  ApiError,
  type Investigation,
  type InvestigationSubmit,
} from "../../services/api";
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

const emptyInvestigation: InvestigationSubmit = {
  root_cause: "",
  gxp_impact_assessment: "",
  corrective_actions: "",
  recovery_verification: "",
  evidence_references: "",
};

const investigationFields: {
  key: keyof InvestigationSubmit;
  title: string;
  placeholder: string;
  minimum: number;
}[] = [
  {
    key: "root_cause",
    title: "Root cause",
    placeholder: "Describe the cause of the incident...",
    minimum: 20,
  },
  {
    key: "gxp_impact_assessment",
    title: "GxP impact assessment",
    placeholder: "Describe the impact on GxP operations...",
    minimum: 20,
  },
  {
    key: "corrective_actions",
    title: "Corrective actions",
    placeholder: "Describe the actions taken...",
    minimum: 20,
  },
  {
    key: "recovery_verification",
    title: "Recovery verification",
    placeholder: "Explain how recovery was verified...",
    minimum: 20,
  },
  {
    key: "evidence_references",
    title: "Evidence references",
    placeholder: "Enter relevant log IDs or evidence references...",
    minimum: 10,
  },
];

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Action failed. Please try again.";
}

export function IncidentDrawer({
  incident: inc,
  user,
  onClose,
  onChanged,
}: Props) {
  useEscape(onClose);

  const [history, setHistory] = useState<AuditEvent[]>([]);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);

  const [note, setNote] = useState("");

  const [investigationForm, setInvestigationForm] =
    useState<InvestigationSubmit>({ ...emptyInvestigation });

  const [qaDecision, setQaDecision] =
    useState<"approved" | "returned">("approved");

  const [qaJustification, setQaJustification] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [loadingInvestigations, setLoadingInvestigations] =
    useState(true);

  // --------------------------------------------------
  // Load investigations
  // --------------------------------------------------

  useEffect(() => {
    let active = true;

    setLoadingInvestigations(true);
    setInvestigations([]);

    api.investigations(inc.number)
      .then((items) => {
        if (active) {
          setInvestigations(items);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setError(errorMessage(error));
        }
      })
      .finally(() => {
        if (active) {
          setLoadingInvestigations(false);
        }
      });

    return () => {
      active = false;
    };
  }, [inc.number]);

  // --------------------------------------------------
  // Load audit history
  // --------------------------------------------------

  useEffect(() => {
    if (!can.viewAudit(user)) return;

    let active = true;

    api.audit({
      entity_type: "incident",
      entity_id: inc.number,
    })
      .then((items) => {
        if (active) {
          setHistory([...items].reverse());
        }
      })
      .catch(() => undefined);

    return () => {
      active = false;
    };
  }, [inc.number, inc.status, inc.recovered_at, user]);

  async function refreshAudit() {
    if (!can.viewAudit(user)) return;

    try {
      const items = await api.audit({
        entity_type: "incident",
        entity_id: inc.number,
      });

      setHistory([...items].reverse());
    } catch {
      // Audit history does not block incident actions.
    }
  }

  // --------------------------------------------------
  // Existing incident actions
  // --------------------------------------------------

  async function act(fn: () => Promise<Incident>) {
    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      const updated = await fn();

      onChanged(updated);
      setNote("");

      await refreshAudit();
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  // --------------------------------------------------
  // Investigation submission
  // --------------------------------------------------

  function updateInvestigation(
    field: keyof InvestigationSubmit,
    value: string
  ) {
    setInvestigationForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  const investigationValid = investigationFields.every(
    (field) =>
      investigationForm[field.key].trim().length >= field.minimum
  );

  async function submitInvestigation() {
    if (!investigationValid || busy) return;

    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      const result = await api.submitInvestigation(
        inc.number,
        investigationForm
      );

      const updated = await api.investigations(inc.number);

      setInvestigations(updated);
      setInvestigationForm({ ...emptyInvestigation });

      setMessage(
        `Investigation revision ${result.revision} submitted successfully.`
      );

      await refreshAudit();
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  // --------------------------------------------------
  // QA review
  // --------------------------------------------------

  async function submitQAReview() {
    if (qaJustification.trim().length < 20 || busy) return;

    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      const result = await api.submitQAReview(
        inc.number,
        qaDecision,
        qaJustification
      );

      setQaJustification("");

      setMessage(
        result.decision === "approved"
          ? "QA review approved. The incident is eligible for closure."
          : "Investigation returned for correction."
      );

      await refreshAudit();
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  // --------------------------------------------------
  // Permissions and visibility
  // --------------------------------------------------

  const blocked = closeBlockedReason(user, inc);

  const latestInvestigation = investigations[0];

  const canSubmitInvestigation =
    user.role === "it_ops" &&
    inc.gxp_impact &&
    inc.status !== "closed";

  const canReview =
    user.role === "qa" &&
    inc.gxp_impact &&
    inc.status === "resolved" &&
    !!latestInvestigation;

  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}

        <header className="drawer-head">
          <div>
            <div className="system-code">
              {inc.number} · {inc.system_code ?? "No system"}
            </div>

            <h2 id="drawer-title">{inc.title}</h2>
          </div>

          <button
            className="icon-btn"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </header>

        {/* Incident details */}

        <div className="tags">
          <StatusBadge value={inc.status} />
          <StatusBadge value={inc.severity} />

          {inc.gxp_impact && (
            <span className="tag">GxP impact</span>
          )}

          <span className="tag">
            Source: {inc.source}
          </span>
        </div>

        <p>{inc.description}</p>

        {inc.recovered_at && inc.status !== "closed" && (
          <p className="callout callout-ok">
            System recovered at {fmtTime(inc.recovered_at)}.
            The incident stays open until it is resolved
            and formally closed.
          </p>
        )}

        <a
          className="card-link small"
          onClick={onClose}
          href={`#/assistant?q=${encodeURIComponent(
            `What should I do about ${inc.number} (${inc.system_code ?? "no system"})?`
          )}`}
        >
          Ask the Knowledge Assistant about this incident →
        </a>

        {inc.resolution_note && (
          <div className="callout">
            <strong>
              Resolution ({inc.resolved_by}):
            </strong>{" "}
            {inc.resolution_note}
          </div>
        )}

        {/* ---------------------------------------
            Investigation history
        --------------------------------------- */}

        {inc.gxp_impact && (
          <section>
            <h3>Investigation</h3>

            {loadingInvestigations && (
              <p className="small muted">
                Loading investigation history...
              </p>
            )}

            {!loadingInvestigations &&
              investigations.length === 0 && (
                <p className="small muted">
                  No investigation has been submitted.
                </p>
              )}

            {investigations.map((item) => (
              <div
                key={item.id}
                className="callout"
              >
                <div className="timeline-head">
                  <strong>
                    Revision {item.revision}
                  </strong>

                  <span className="small muted">
                    {fmtTime(item.submitted_at)}
                  </span>
                </div>

                <p className="small muted">
                  Submitted by {item.submitted_by}
                </p>

                <p>
                  <strong>Root cause</strong>
                </p>
                <p>{item.root_cause}</p>

                <p>
                  <strong>GxP impact assessment</strong>
                </p>
                <p>{item.gxp_impact_assessment}</p>

                <p>
                  <strong>Corrective actions</strong>
                </p>
                <p>{item.corrective_actions}</p>

                <p>
                  <strong>Recovery verification</strong>
                </p>
                <p>{item.recovery_verification}</p>

                <p>
                  <strong>Evidence references</strong>
                </p>
                <p>{item.evidence_references}</p>
              </div>
            ))}
          </section>
        )}

        {/* ---------------------------------------
            IT Operations investigation form
        --------------------------------------- */}

        {canSubmitInvestigation && (
          <section className="actions">
            <h3>Submit investigation</h3>

            <p className="small muted">
              Complete the investigation fields below.
              Each submission creates a new revision.
            </p>

            <div className="resolve">
              {investigationFields.map((field) => (
                <div key={field.key}>
                  <label
                    htmlFor={`investigation-${field.key}`}
                  >
                    {field.title}
                  </label>

                  <textarea
                    id={`investigation-${field.key}`}
                    rows={3}
                    value={investigationForm[field.key]}
                    onChange={(e) =>
                      updateInvestigation(
                        field.key,
                        e.target.value
                      )
                    }
                    placeholder={field.placeholder}
                    disabled={busy}
                  />
                </div>
              ))}

              <button
                className="primary"
                disabled={busy || !investigationValid}
                onClick={submitInvestigation}
              >
                {busy
                  ? "Processing..."
                  : "Submit investigation"}
              </button>
            </div>
          </section>
        )}

        {/* ---------------------------------------
            Existing incident actions
        --------------------------------------- */}

        <section className="actions">
          {can.acknowledge(user, inc) && (
            <button
              disabled={busy}
              onClick={() =>
                act(() => api.acknowledge(inc.number))
              }
            >
              Acknowledge
            </button>
          )}

          {can.resolve(user, inc) && (
            <div className="resolve">
              <label htmlFor="note">
                Resolution note (root cause and action taken)
              </label>

              <textarea
                id="note"
                rows={3}
                value={note}
                onChange={(e) =>
                  setNote(e.target.value)
                }
                placeholder="e.g. Restarted EBR application service; terminals reconnected. Root cause: …"
                disabled={busy}
              />

              <button
                disabled={
                  busy || note.trim().length < 10
                }
                onClick={() =>
                  act(() =>
                    api.resolve(inc.number, note)
                  )
                }
              >
                Resolve
              </button>
            </div>
          )}
        </section>

        {/* ---------------------------------------
            QA review form
        --------------------------------------- */}

        {canReview && (
          <section className="actions">
            <h3>QA review</h3>

            <p className="small muted">
              Review investigation revision{" "}
              {latestInvestigation.revision}
              {" "}and record your decision.
            </p>

            <div className="resolve">
              <label htmlFor="qa-decision">
                QA decision
              </label>

              <select
                id="qa-decision"
                value={qaDecision}
                onChange={(e) =>
                  setQaDecision(
                    e.target.value as
                      | "approved"
                      | "returned"
                  )
                }
                disabled={busy}
              >
                <option value="approved">
                  Approve investigation
                </option>

                <option value="returned">
                  Return for correction
                </option>
              </select>

              <label htmlFor="qa-justification">
                QA justification
              </label>

              <textarea
                id="qa-justification"
                rows={3}
                value={qaJustification}
                onChange={(e) =>
                  setQaJustification(e.target.value)
                }
                placeholder="Explain the QA review decision..."
                disabled={busy}
              />

              <button
                className="primary"
                disabled={
                  busy ||
                  qaJustification.trim().length < 20
                }
                onClick={submitQAReview}
              >
                {busy
                  ? "Processing..."
                  : qaDecision === "approved"
                    ? "Approve investigation"
                    : "Return investigation"}
              </button>
            </div>
          </section>
        )}

        {/* ---------------------------------------
            Incident closure
        --------------------------------------- */}

        <section className="actions">
          {can.close(user, inc) && (
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                act(() => api.close(inc.number))
              }
            >
              Close incident
              {inc.gxp_impact
                ? " (QA approval)"
                : ""}
            </button>
          )}

          {blocked && (
            <p className="small muted">
              {blocked}
            </p>
          )}

          {message && (
            <p
              className="callout callout-ok"
              role="status"
            >
              {message}
            </p>
          )}

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </section>

        {/* ---------------------------------------
            Audit history
        --------------------------------------- */}

        {can.viewAudit(user) && (
          <section>
            <h3>Audit history</h3>

            <ol className="timeline">
              {history.map((event) => (
                <li key={event.id}>
                  <div className="timeline-head">
                    <strong>
                      {label(
                        event.action.replace(
                          "incident.",
                          ""
                        )
                      )}
                    </strong>

                    <span className="muted small">
                      {fmtTime(event.occurred_at)}
                      {" · "}
                      {event.actor}
                    </span>
                  </div>

                  <code
                    className="hash"
                    title={event.hash}
                  >
                    #{event.hash.slice(0, 12)}
                  </code>
                </li>
              ))}
            </ol>
          </section>
        )}
      </aside>
    </div>
  );
}
