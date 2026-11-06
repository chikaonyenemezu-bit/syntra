import { useState } from "react";
import { api, ApiError } from "../../services/api";
import { ago, fmtTime } from "../../format";
import type { IngestionJobDetail, Integration, SyncSource } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

interface Props {
  integration: Integration;
  canSync: boolean;
  onSynced: (job: IngestionJobDetail) => void;
}

const SOURCES: { source: SyncSource; label: string; hint: string }[] = [
  { source: "live", label: "Sync from openFDA", hint: "Live API, needs internet" },
  { source: "sample", label: "Load sample data", hint: "12 valid records, offline" },
  { source: "sample_with_errors", label: "Load sample with errors", hint: "6 of 14 records invalid" },
];

export function IntegrationCard({ integration: i, canSync, onSynced }: Props) {
  const [busy, setBusy] = useState<SyncSource | null>(null);
  const [error, setError] = useState<string | null>(null);
  const job = i.last_job;
  const accepted = job ? job.inserted + job.updated + job.unchanged : 0;

  async function sync(source: SyncSource) {
    setBusy(source); setError(null);
    try { onSynced(await api.sync(i.system.code, source)); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Sync failed"); }
    finally { setBusy(null); }
  }

  return (
    <article className={`card integration-card system-card status-${i.system.status}`}>
      <header className="system-head">
        <div>
          <div className="system-code">{i.system.code}</div>
          <h2>{i.system.name}</h2>
        </div>
        <StatusBadge value={i.system.status} />
      </header>
      <p className="muted small">{i.system.description}</p>
      <div className="tags">
        {i.system.gxp_relevant && <span className="tag">GxP</span>}
        {i.system.gamp_category && <span className="tag">GAMP {i.system.gamp_category}</span>}
        <span className="tag">Owner: {i.system.owner}</span>
        <span className="tag">
          {i.sync_enabled ? `Scheduled every ${Math.round(i.sync_interval_minutes / 60)} h` : "Schedule off"}
          {" · "}last {i.lookback_days} days
        </span>
      </div>

      <dl className="metrics metrics-4">
        <div><dt>Last sync</dt><dd title={fmtTime(job?.finished_at ?? null)}>{job ? ago(job.finished_at) : "never"}</dd></div>
        <div><dt>Accepted</dt><dd>{job ? accepted : "–"}</dd></div>
        <div><dt>Rejected</dt><dd className={job?.rejected ? "warn-text" : undefined}>{job ? job.rejected : "–"}</dd></div>
        <div><dt>Recalls stored</dt><dd>{i.recalls_total}</dd></div>
      </dl>
      <p className="small status-reason">{i.system.status_reason || "Waiting for the first sync."}</p>
      <p className="small muted">
        Degrades when more than {Math.round(i.rejection_threshold * 100)} % of a run is rejected,
        goes down when the source cannot be reached.
      </p>

      {canSync && (
        <div className="sync-actions">
          {SOURCES.map((s) => (
            <button key={s.source} className={s.source === "live" ? "primary" : undefined}
                    disabled={busy !== null} onClick={() => sync(s.source)} title={s.hint}>
              {busy === s.source ? "Running…" : s.label}
            </button>
          ))}
          <p className="small muted">Sample data is synthetic, in openFDA format, for offline demos.</p>
        </div>
      )}
      {error && <p className="error" role="alert">{error}</p>}
    </article>
  );
}
