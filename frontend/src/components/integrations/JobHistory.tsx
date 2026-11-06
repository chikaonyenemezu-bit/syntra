import { useEffect, useState } from "react";
import { api } from "../../services/api";
import { fmtTime } from "../../format";
import type { IngestionJob, IngestionJobDetail } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

const SOURCE_LABEL: Record<string, string> = {
  live: "openFDA", sample: "Sample", sample_with_errors: "Sample with errors",
};

interface Props {
  jobs: IngestionJob[];
  selected: string | null;
  onSelect: (number: string) => void;
}

export function JobHistory({ jobs, selected, onSelect }: Props) {
  if (!jobs.length) return <p className="muted empty">No sync has run yet.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Job</th><th>Started</th><th>Source</th><th>Trigger</th>
            <th className="num">Fetched</th><th className="num">New</th><th className="num">Changed</th>
            <th className="num">Rejected</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.id} className={j.number === selected ? "row-selected" : undefined}>
              <td className="nowrap"><button className="link" onClick={() => onSelect(j.number)}
                          aria-pressed={j.number === selected}>{j.number}</button></td>
              <td className="nowrap">{fmtTime(j.started_at)}</td>
              <td>{SOURCE_LABEL[j.source] ?? j.source}</td>
              <td>{j.trigger === "manual" ? `Manual (${j.triggered_by})` : "Scheduled"}</td>
              <td className="num">{j.fetched}</td>
              <td className="num">{j.inserted}</td>
              <td className="num">{j.updated}</td>
              <td className={`num ${j.rejected ? "warn-text" : ""}`}>{j.rejected}</td>
              <td><StatusBadge value={j.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function JobDetail({ number, refreshKey }: { number: string; refreshKey: number }) {
  const [job, setJob] = useState<IngestionJobDetail | null>(null);
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => {
    setOpen(null);
    api.job(number).then(setJob).catch(() => setJob(null));
  }, [number, refreshKey]);

  if (!job) return null;
  return (
    <section className="job-detail" aria-label={`Details of ${job.number}`}>
      <div className="section-head">
        <h3>{job.number}: {job.rejected ? `${job.rejected} rejected record${job.rejected > 1 ? "s" : ""} in quarantine` : "no rejected records"}</h3>
        <span className="small muted">{job.source_detail}{job.duration_ms != null && ` · ${job.duration_ms} ms`}</span>
      </div>
      {job.error_message && <p className="callout callout-bad">{job.error_message}</p>}
      {job.rejected_records.length > 0 && (
        <ul className="rejected-list">
          {job.rejected_records.map((r) => (
            <li key={r.id}>
              <div className="rejected-head">
                <code>{r.record_key}</code>
                <button className="link small" aria-expanded={open === r.id}
                        onClick={() => setOpen(open === r.id ? null : r.id)}>
                  {open === r.id ? "Hide record" : "Show record"}
                </button>
              </div>
              <ul className="reasons">
                {r.reasons.map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
              {open === r.id && <pre className="payload">{JSON.stringify(r.payload, null, 2)}</pre>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
