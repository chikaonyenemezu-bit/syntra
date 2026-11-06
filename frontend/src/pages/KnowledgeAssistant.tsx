import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../services/api";
import type { AssistantAnswer, AssistantStatus, KnowledgeDoc, User } from "../types";
import { AnswerCard } from "../components/assistant/AnswerCard";
import { DocumentViewer } from "../components/assistant/DocumentViewer";

const SUGGESTIONS = [
  "MES-01 is down. What do I do?",
  "Who must approve a change to a GxP system?",
  "Which periodic reviews are overdue?",
  "Why were records rejected in the last openFDA import?",
  "Are there any Class I recalls?",
  "What must an audit trail record under 21 CFR Part 11?",
];

const PROVIDER = { anthropic: "Claude", openai: "OpenAI" };
const TYPE_LABEL = { sop: "SOPs", runbook: "Runbooks", regulation: "Regulatory notes" };

export function KnowledgeAssistant({ user, initialQuestion }: { user: User; initialQuestion: string | null }) {
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [answers, setAnswers] = useState<AssistantAnswer[]>([]);
  const [question, setQuestion] = useState(initialQuestion ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewer, setViewer] = useState<{ docId: string; section: string | null } | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.assistantStatus().then(setStatus).catch(() => undefined);
    api.documents().then(setDocs).catch(() => undefined);
    api.myQueries().then(setAnswers).catch(() => undefined);
  }, []);
  useEffect(() => { if (initialQuestion) setQuestion(initialQuestion); }, [initialQuestion]);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [answers.length, busy]);

  async function ask(q: string) {
    const text = q.trim();
    if (text.length < 3 || busy) return;
    setBusy(true); setError(null);
    const history = answers.filter((a) => a.answer).slice(-4).map((a) => ({ question: a.question, answer: a.answer! }));
    try {
      const a = await api.ask(text, history);
      setAnswers((xs) => [...xs, a]);
      setQuestion("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The assistant could not answer.");
    } finally {
      setBusy(false);
    }
  }

  const openRef = (ref: string) => {
    const [docId, section] = ref.split(" §");
    setViewer({ docId, section: section ?? null });
  };

  const byType = (t: KnowledgeDoc["doc_type"]) => docs.filter((d) => d.doc_type === t);

  return (
    <div className="page assistant-page">
      <header className="page-head">
        <div>
          <h1>Knowledge Assistant</h1>
          <p className="muted">
            Answers from Syntra's controlled SOPs, runbooks and regulatory notes, combined with live system data.
            Every answer shows its sources.
          </p>
        </div>
        {status && (
          <div className={`mode-banner ${status.mode === "llm" ? "mode-llm" : "mode-retrieval"}`}>
            {status.mode === "llm"
              ? <><strong>{PROVIDER[status.provider!]}</strong> <span className="small">{status.model}</span></>
              : <><strong>Retrieval only</strong><span className="small">Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env for written answers</span></>}
            <span className="small muted">{status.documents} documents · {status.sections} sections</span>
          </div>
        )}
      </header>

      <div className="assistant-layout">
        <section className="conversation" aria-label="Conversation">
          {answers.length === 0 && !busy && (
            <div className="card empty-chat">
              <h2>Ask about procedures, systems or recalls</h2>
              <p className="muted small">The assistant reads documents and live data, but it cannot change anything in Syntra.</p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => <button key={s} onClick={() => ask(s)}>{s}</button>)}
              </div>
            </div>
          )}
          {answers.map((a) => (
            <AnswerCard key={a.number} a={a} mine={a.asked_by === user.username} onOpenRef={openRef}
                        onUpdated={(u) => setAnswers((xs) => xs.map((x) => (x.number === u.number ? u : x)))} />
          ))}
          {busy && <div className="card thinking" role="status">Searching documents and live data…</div>}
          {error && <p className="error" role="alert">{error}</p>}
          <div ref={end} />

          <form className="ask-form" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
            <label htmlFor="ask" className="visually-hidden">Your question</label>
            <textarea id="ask" rows={2} value={question} placeholder="Ask a question…" disabled={busy}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(question); } }} />
            <button type="submit" className="primary" disabled={busy || question.trim().length < 3}>Ask</button>
          </form>
          <p className="small muted disclaimer">
            Answers are guidance. The controlled document is authoritative; open the cited section before acting.
            Questions and answers are recorded.
          </p>
        </section>

        <aside className="card library" aria-label="Document library">
          <h2>Knowledge base</h2>
          {(["sop", "runbook", "regulation"] as const).map((t) => byType(t).length > 0 && (
            <div key={t} className="library-group">
              <div className="small muted">{TYPE_LABEL[t]}</div>
              <ul>
                {byType(t).map((d) => (
                  <li key={d.doc_id}>
                    <button className="link" onClick={() => setViewer({ docId: d.doc_id, section: null })}>{d.doc_id}</button>
                    <span className="small"> {d.title}</span>
                    <span className="small muted"> · v{d.version}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </aside>
      </div>

      {viewer && <DocumentViewer docId={viewer.docId} section={viewer.section} onClose={() => setViewer(null)} />}
    </div>
  );
}
