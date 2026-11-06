import { useEffect, useRef, useState } from "react";
import { api } from "../../services/api";
import { fmtDate } from "../../format";
import type { KnowledgeDocDetail } from "../../types";
import { RichText } from "./RichText";

const TYPE_LABEL = { sop: "SOP", runbook: "Runbook", regulation: "Regulatory notes" };

export function DocumentViewer({ docId, section, onClose }: { docId: string; section: string | null; onClose: () => void }) {
  const [doc, setDoc] = useState<KnowledgeDocDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const body = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setDoc(null); setError(null);
    api.document(docId).then(setDoc).catch(() => setError(`${docId} is not in the knowledge base.`));
  }, [docId]);

  useEffect(() => {
    if (!doc || !section) return;
    body.current?.querySelector(`[data-section="${section}"]`)?.scrollIntoView({ block: "start" });
  }, [doc, section]);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer doc-drawer" role="dialog" aria-modal="true" aria-labelledby="doc-title"
             onClick={(e) => e.stopPropagation()}>
        <header className="drawer-head">
          <div>
            <div className="system-code">{docId}{doc && ` · ${TYPE_LABEL[doc.doc_type]} · version ${doc.version}`}</div>
            <h2 id="doc-title">{doc?.title ?? docId}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">×</button>
        </header>
        {error && <p className="error">{error}</p>}
        {doc && (
          <>
            <div className="tags">
              <span className="tag">Effective {fmtDate(doc.effective)}</span>
              <span className="tag">Owner: {doc.owner}</span>
              {doc.source && <a className="tag" href={doc.source} target="_blank" rel="noreferrer">Official source ↗</a>}
            </div>
            <div ref={body} className="doc-body">
              {doc.sections.map((s) => (
                <section key={s.section} data-section={s.section} className={s.section === section ? "doc-section cited" : "doc-section"}>
                  <h3>{s.section} {s.heading}</h3>
                  <RichText text={s.text} />
                </section>
              ))}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
