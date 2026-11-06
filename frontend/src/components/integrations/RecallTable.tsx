import { Fragment, useEffect, useState } from "react";
import { api } from "../../services/api";
import type { RecallPage } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

const PAGE = 25;
const CLASSES = ["", "Class I", "Class II", "Class III"];

const fmtDate = (d: string | null) => (d ? new Date(d + "T00:00:00").toLocaleDateString() : "–");

export function RecallTable({ refreshKey }: { refreshKey: number }) {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [classification, setClassification] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<RecallPage | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    const params: Record<string, string> = { limit: String(PAGE), offset: String(offset) };
    if (query) params.q = query;
    if (classification) params.classification = classification;
    api.recalls(params).then(setData).catch(() => setData(null));
  }, [query, classification, offset, refreshKey]);

  return (
    <>
      <form className="recall-filters" role="search"
            onSubmit={(e) => { e.preventDefault(); setOffset(0); setQuery(q.trim()); }}>
        <label className="grow">Search product, firm, reason, recall or lot number
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. metformin, NDMA, D-0904-2026" />
        </label>
        <label>Classification
          <select value={classification} onChange={(e) => { setOffset(0); setClassification(e.target.value); }}>
            {CLASSES.map((c) => <option key={c} value={c}>{c || "All"}</option>)}
          </select>
        </label>
        <button type="submit">Search</button>
      </form>

      {!data || data.items.length === 0 ? (
        <p className="muted empty">{query || classification ? "No recalls match." : "No recalls stored yet. Run a sync above."}</p>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Recall</th><th>Class</th><th>Product</th><th>Reason</th><th>Firm</th><th>Reported</th><th>Status</th></tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <Fragment key={r.recall_number}>
                    <tr>
                      <td className="nowrap">
                        <button className="link" aria-expanded={open === r.recall_number}
                                onClick={() => setOpen(open === r.recall_number ? null : r.recall_number)}>
                          {r.recall_number}
                        </button>
                        {r.source === "sample" && <span className="tag tag-sample">sample</span>}
                      </td>
                      <td><StatusBadge value={r.classification} /></td>
                      <td className="wide"><div className="clamp">{r.product_description}</div></td>
                      <td className="wide"><div className="clamp">{r.reason_for_recall}</div></td>
                      <td>{r.recalling_firm}</td>
                      <td className="nowrap">{fmtDate(r.report_date)}</td>
                      <td>{r.status}</td>
                    </tr>
                    {open === r.recall_number && (
                      <tr className="detail-row">
                        <td colSpan={7}>
                          <dl className="recall-detail">
                            <div><dt>Product</dt><dd>{r.product_description}</dd></div>
                            <div><dt>Reason</dt><dd>{r.reason_for_recall}</dd></div>
                            <div><dt>Lots / codes</dt><dd>{r.code_info ?? "–"}</dd></div>
                            <div><dt>Quantity</dt><dd>{r.product_quantity ?? "–"}</dd></div>
                            <div><dt>Distribution</dt><dd>{r.distribution_pattern ?? "–"}</dd></div>
                            <div><dt>Firm</dt><dd>{[r.recalling_firm, r.city, r.state, r.country].filter(Boolean).join(", ")}</dd></div>
                            <div><dt>Initiated</dt><dd>{fmtDate(r.recall_initiation_date)}</dd></div>
                            <div><dt>Terminated</dt><dd>{fmtDate(r.termination_date)}</dd></div>
                            <div><dt>Type</dt><dd>{r.voluntary_mandated ?? "–"}</dd></div>
                          </dl>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pager">
            <span className="small muted">
              {offset + 1}–{offset + data.items.length} of {data.total}
            </span>
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
            <button disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>Next</button>
          </div>
        </>
      )}
    </>
  );
}
