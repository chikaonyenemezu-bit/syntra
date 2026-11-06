import { useState } from "react";
import { api } from "../../services/api";
import type { AssistantAnswer } from "../../types";
import { RichText } from "./RichText";

const TOOL_LABEL: Record<string, string> = {
  search_knowledge: "Searched documents",
  get_system_status: "System status",
  list_incidents: "Incidents",
  get_incident: "Incident details",
  list_change_requests: "Change requests",
  search_recalls: "FDA recalls",
};

interface Props {
  a: AssistantAnswer;
  mine: boolean;
  onOpenRef: (ref: string) => void;
  onUpdated: (a: AssistantAnswer) => void;
}

export function AnswerCard({ a, mine, onOpenRef, onUpdated }: Props) {
  const [showTools, setShowTools] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [comment, setComment] = useState("");
  const valid = new Set(a.citations.filter((c) => c.valid).map((c) => c.ref));
  const invalid = a.citations.filter((c) => !c.valid);
  const liveData = a.tool_calls.filter((t) => t.name !== "search_knowledge");

  async function rate(rating: "helpful" | "incorrect") {
    onUpdated(await api.rateAnswer(a.number, rating, rating === "incorrect" ? comment : ""));
    setReporting(false);
  }

  return (
    <article className="qa">
      <div className="qa-question">{a.question}</div>
      <div className="card qa-answer">
        {a.mode === "llm" && a.answer ? (
          <>
            <div className="qa-head">
              {a.grounded
                ? <span className="badge badge-ok">{valid.size ? `${valid.size} verified source${valid.size > 1 ? "s" : ""}` : "From live data"}</span>
                : <span className="badge badge-warn">No verified source</span>}
              {liveData.length > 0 && <span className="badge badge-info">Live data: {liveData.length} lookup{liveData.length > 1 ? "s" : ""}</span>}
            </div>
            <RichText text={a.answer} validRefs={valid} onCite={onOpenRef} />
            {invalid.length > 0 && (
              <p className="callout callout-warn small">
                Unverified reference{invalid.length > 1 ? "s" : ""}: {invalid.map((c) => c.ref).join(", ")}. The
                assistant cited a section it was not given; check the document before relying on this part.
              </p>
            )}
            {a.citations.filter((c) => c.valid).length > 0 && (
              <div className="sources">
                <div className="small muted">Sources</div>
                {a.citations.filter((c) => c.valid).map((c) => (
                  <button key={c.ref} className="source" onClick={() => onOpenRef(c.ref)}>
                    <span className="source-ref">{c.ref}</span>
                    <span className="source-title">{c.title}: {c.heading}</span>
                    <span className="small muted">version {c.version}</span>
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            <div className="qa-head"><span className="badge badge-muted">Retrieval only</span></div>
            {a.error
              ? <p className="callout callout-warn small">The language model could not be used: {a.error}</p>
              : <p className="small muted">No language model is configured, so these are the most relevant sections, not a written answer.</p>}
            {a.passages.length === 0
              ? <p>No section of the Syntra knowledge base matches this question.</p>
              : (
                <div className="sources">
                  {a.passages.map((p) => (
                    <button key={p.ref} className="source" onClick={() => onOpenRef(p.ref)}>
                      <span className="source-ref">{p.ref}</span>
                      <span className="source-title">{p.title}: {p.heading}</span>
                      <span className="small">{p.excerpt}</span>
                    </button>
                  ))}
                </div>
              )}
          </>
        )}

        {a.tool_calls.length > 0 && (
          <div className="tools">
            <button className="link small" aria-expanded={showTools} onClick={() => setShowTools(!showTools)}>
              {showTools ? "Hide" : "Show"} what the assistant looked up ({a.tool_calls.length})
            </button>
            {showTools && (
              <ul className="tool-list">
                {a.tool_calls.map((t, i) => (
                  <li key={i} className={t.ok ? undefined : "tool-failed"}>
                    <strong>{TOOL_LABEL[t.name] ?? t.name}</strong> <span className="muted">{t.summary}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <footer className="qa-foot small muted">
          <span>{a.number}{a.model ? ` · ${a.model}` : ""} · {(a.latency_ms / 1000).toFixed(1)} s
            {a.input_tokens + a.output_tokens > 0 && ` · ${a.input_tokens + a.output_tokens} tokens`}</span>
          {mine && a.mode === "llm" && a.answer && (
            a.feedback
              ? <span>Rated: {a.feedback === "helpful" ? "helpful" : "incorrect"}</span>
              : <span className="row">
                  <button className="link small" onClick={() => rate("helpful")}>Helpful</button>
                  <button className="link small" onClick={() => setReporting(true)}>Report incorrect answer</button>
                </span>
          )}
        </footer>
        {reporting && (
          <form className="report" onSubmit={(e) => { e.preventDefault(); rate("incorrect"); }}>
            <label htmlFor={`rep-${a.number}`} className="small">What was wrong? (optional, recorded with {a.number})</label>
            <textarea id={`rep-${a.number}`} rows={2} value={comment} onChange={(e) => setComment(e.target.value)} />
            <div className="row">
              <button type="submit">Send report</button>
              <button type="button" className="link small" onClick={() => setReporting(false)}>Cancel</button>
            </div>
          </form>
        )}
      </div>
    </article>
  );
}
