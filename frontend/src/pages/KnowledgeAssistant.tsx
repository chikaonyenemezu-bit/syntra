import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../services/api";
import type { AssistantAnswer, KnowledgeDoc, User } from "../types";
import { AnswerCard } from "../components/assistant/AnswerCard";
import { DocumentViewer } from "../components/assistant/DocumentViewer";

const SUGGESTIONS = [
  "MES-01 is down. What do I do?",
  "Who must approve a change to a GxP system?",
  "Which periodic reviews are overdue?",
  "Why were records rejected in the last openFDA import?",
];

const TYPE_LABEL = {
  sop: "SOPs",
  runbook: "Runbooks",
  regulation: "Regulatory notes",
};

type ChatSession = {
  id: string;
  title: string;
  answerNumbers: string[];
  updatedAt: string;
};

// Syntra already stores answers on the server. Only the grouping of
// those answers into chats is kept locally, scoped to the signed-in user.
const sessionKey = (username: string) => `syntra_chat_sessions_v1:${username}`;

function readSessions(username: string): ChatSession[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(sessionKey(username)) ?? "[]");
    if (!Array.isArray(value)) return [];
    return value.filter((item): item is ChatSession =>
      item !== null && typeof item === "object" &&
      typeof item.id === "string" && typeof item.title === "string" &&
      Array.isArray(item.answerNumbers) &&
      item.answerNumbers.every((n: unknown) => typeof n === "string") &&
      typeof item.updatedAt === "string"
    );
  } catch {
    return [];
  }
}

function writeSessions(username: string, sessions: ChatSession[]) {
  try {
    localStorage.setItem(sessionKey(username), JSON.stringify(sessions));
  } catch {
    // Chat grouping cannot be saved if browser storage is unavailable.
  }
}

function numberOrder(number: string): number {
  return Number(number.replace(/\D/g, "")) || 0;
}

function chatTitle(question: string): string {
  const text = question.trim();
  return text.length > 62 ? `${text.slice(0, 59)}…` : text;
}

function newChatId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `chat-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function KnowledgeAssistant({
  user,
  initialQuestion,
}: {
  user: User;
  initialQuestion: string | null;
}) {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [answers, setAnswers] = useState<AssistantAnswer[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>(() => readSessions(user.username));

  // Always start on a blank chat, even when the page is refreshed.
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState(initialQuestion ?? "");
  const [busy, setBusy] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [viewer, setViewer] = useState<{ docId: string; section: string | null } | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    api.documents().then((items) => {
      if (!cancelled) setDocs(items);
    }).catch(() => undefined);

    api.myQueries()
      .then((items) => {
        if (cancelled) return;
        const mine = items
          .filter((item) => item.asked_by === user.username)
          .sort((a, b) => numberOrder(a.number) - numberOrder(b.number));
        setAnswers((current) => {
          const combined = new Map(current.map((answer) => [answer.number, answer]));
          mine.forEach((answer) => combined.set(answer.number, answer));
          return [...combined.values()].sort((a, b) => numberOrder(a.number) - numberOrder(b.number));
        });

        // Existing individual questions remain accessible. Older questions
        // that predate chat grouping are displayed as one-question chats.
        setSessions((current) => {
          const assigned = new Set(current.flatMap((s) => s.answerNumbers));
          const previous = mine.filter((answer) => !assigned.has(answer.number)).map((answer) => ({
            id: `earlier-${answer.number}`,
            title: chatTitle(answer.question),
            answerNumbers: [answer.number],
            updatedAt: answer.asked_at,
          }));
          return [...current, ...previous];
        });
      })
      .catch(() => {
        if (!cancelled) setError("Previous conversations could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });

    return () => { cancelled = true; };
  }, [user.username]);

  useEffect(() => {
    writeSessions(user.username, sessions);
  }, [sessions, user.username]);

  useEffect(() => {
    if (initialQuestion) setQuestion(initialQuestion);
  }, [initialQuestion]);

  const savedChats = [...sessions]
    .filter((session) => session.answerNumbers.length > 0)
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

  const activeSession = sessions.find((session) => session.id === activeSessionId);
  const answersByNumber = new Map(answers.map((answer) => [answer.number, answer]));
  const shown = (activeSession?.answerNumbers ?? [])
    .map((number) => answersByNumber.get(number))
    .filter((answer): answer is AssistantAnswer => answer !== undefined);

  useEffect(() => {
    if (shown.length > 0) end.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [shown.length, busy, activeSessionId]);

  function newConversation() {
    setActiveSessionId(null);
    setQuestion("");
    setError(null);
    setLibraryOpen(false);
  }

  function openConversation(id: string) {
    setActiveSessionId(id);
    setQuestion("");
    setError(null);
    setLibraryOpen(false);
  }

  async function ask(rawQuestion: string) {
    const text = rawQuestion.trim();
    if (text.length < 3 || busy || loadingHistory) return;

    setBusy(true);
    setError(null);
    const history = shown
      .filter((answer) => answer.answer)
      .slice(-4)
      .map((answer) => ({ question: answer.question, answer: answer.answer! }));

    try {
      const answer = await api.ask(text, history);
      const sessionId = activeSessionId ?? newChatId();
      const now = new Date().toISOString();

      setAnswers((current) => [...current, answer]);
      setSessions((current) => {
        const exists = current.some((session) => session.id === sessionId);
        if (!exists) {
          return [...current, {
            id: sessionId,
            title: chatTitle(text),
            answerNumbers: [answer.number],
            updatedAt: now,
          }];
        }
        return current.map((session) => session.id === sessionId
          ? { ...session, answerNumbers: [...session.answerNumbers, answer.number], updatedAt: now }
          : session);
      });
      setActiveSessionId(sessionId);
      setQuestion("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The assistant could not answer.");
    } finally {
      setBusy(false);
    }
  }

  function openRef(ref: string) {
    const [docId, section] = ref.split(" §");
    setViewer({ docId, section: section ?? null });
  }

  const byType = (type: KnowledgeDoc["doc_type"]) =>
    docs.filter((doc) => doc.doc_type === type);

  return (
    <div className="page assistant-page chat-page">
      <div className="chat-layout">
        <aside className="chat-history" aria-label="Previous conversations">
          <div className="chat-history-header">
            <h2>Conversations</h2>
            <button type="button" className="chat-new" onClick={newConversation}>
              + New conversation
            </button>
          </div>
          <div className="chat-history-list">
            <div className="chat-history-label">Previous chats</div>
            {loadingHistory && <p className="small muted">Loading history…</p>}
            {!loadingHistory && savedChats.length === 0 && (
              <p className="small muted">Your previous conversations will appear here.</p>
            )}
            {savedChats.map((session) => (
              <button
                key={session.id}
                type="button"
                title={session.title}
                className={`chat-history-item${activeSessionId === session.id ? " active" : ""}`}
                aria-pressed={activeSessionId === session.id}
                onClick={() => openConversation(session.id)}
              >
                <span className="chat-history-icon" aria-hidden="true">▤</span>
                <span className="chat-history-title">{session.title}</span>
              </button>
            ))}
          </div>
        </aside>

        <section className="chat-workspace" aria-label="Knowledge Assistant">
          <header className="chat-topbar">
            <h1>Knowledge Assistant</h1>
            <button
              type="button"
              className="chat-doc-button"
              aria-expanded={libraryOpen}
              onClick={() => setLibraryOpen((current) => !current)}
            >
              Documents
            </button>
          </header>

          <div className="chat-scroll">
            {shown.length === 0 && !busy && (
              <div className="chat-welcome">
                <div
                  className="chat-welcome-mark"
                  aria-label="Syntra"
                  role="img"
                  style={{
                    width: 64,
                    height: 64,
                    padding: 0,
                    background: "transparent",
                    border: 0,
                    borderRadius: 0,
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <svg
                    viewBox="0 0 80 72"
                    width="64"
                    height="64"
                    fill="none"
                    aria-hidden="true"
                    style={{ display: "block" }}
                  >
                    <path
                      d="M15 16H65L40 59Z"
                      stroke="#7585DB"
                      strokeWidth="4"
                      strokeLinejoin="round"
                    />
                    <circle cx="15" cy="16" r="7" fill="#7585DB" />
                    <circle cx="65" cy="16" r="7" fill="#7585DB" />
                    <circle cx="40" cy="59" r="7" fill="#7585DB" />
                  </svg>
                </div>
                <h2>How can I help?</h2>
                <p>Ask about connected systems, incidents, SOPs, recalls, and GxP workflows.</p>
                <div className="chat-suggestions">
                  {SUGGESTIONS.map((suggestion) => (
                    <button key={suggestion} type="button" disabled={loadingHistory}
                      onClick={() => void ask(suggestion)}>
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {shown.length > 0 && (
              <div className="chat-messages">
                {shown.map((answer) => (
                  <AnswerCard
                    key={answer.number}
                    a={answer}
                    mine={answer.asked_by === user.username}
                    onOpenRef={openRef}
                    onUpdated={(updated) => setAnswers((current) =>
                      current.map((answerItem) => answerItem.number === updated.number ? updated : answerItem)
                    )}
                  />
                ))}
              </div>
            )}
            {busy && <div className="chat-thinking" role="status">Searching documents and live data…</div>}
            {error && <p className="error chat-error" role="alert">{error}</p>}
            <div ref={end} />
          </div>

          <div className="chat-compose">
            <form className="chat-input-form" onSubmit={(event) => {
              event.preventDefault();
              void ask(question);
            }}>
              <label htmlFor="ask" className="visually-hidden">Your question</label>
              <textarea
                id="ask"
                rows={2}
                value={question}
                placeholder="Ask Syntra a question…"
                disabled={busy || loadingHistory}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void ask(question);
                  }
                }}
              />
              <button type="submit" className="primary"
                disabled={busy || loadingHistory || question.trim().length < 3}>
                Send
              </button>
            </form>
            <p className="chat-disclaimer">
              Answers are guidance. Check the cited controlled documents before acting. Questions and answers are recorded.
            </p>
          </div>

          {libraryOpen && (
            <aside className="chat-library" aria-label="Document library">
              <div className="chat-library-header">
                <h2>Knowledge base</h2>
                <button type="button" onClick={() => setLibraryOpen(false)} aria-label="Close documents">×</button>
              </div>
              {(["sop", "runbook", "regulation"] as const).map((type) => byType(type).length > 0 && (
                <div key={type} className="chat-library-group">
                  <h3>{TYPE_LABEL[type]}</h3>
                  <ul>
                    {byType(type).map((doc) => (
                      <li key={doc.doc_id}>
                        <button type="button" className="link"
                          onClick={() => setViewer({ docId: doc.doc_id, section: null })}>
                          {doc.doc_id}
                        </button>
                        <span className="small"> {doc.title}</span>
                        <span className="small muted"> · v{doc.version}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </aside>
          )}
        </section>
      </div>

      {viewer && (
        <DocumentViewer
          docId={viewer.docId}
          section={viewer.section}
          onClose={() => setViewer(null)}
        />
      )}
    </div>
  );
}
