import { useEffect, useState } from "react";
import { api } from "../../services/api";
import { ago } from "../../format";
import type { FaultMode, System, Telemetry } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";
import { LatencySparkline } from "./LatencySparkline";

const LATENCY_THRESHOLD_MS = 1500;
const FAULTS: { value: FaultMode; text: string }[] = [
  { value: null, text: "Normal" },
  { value: "degraded", text: "Degraded" },
  { value: "down", text: "Down" },
  { value: "silent", text: "Silent (no heartbeat)" },
];

interface Props {
  system: System;
  tick: number;
  canInjectFault: boolean;
  onFaultChanged: () => void;
}

export function SystemCard({ system, tick, canInjectFault, onFaultChanged }: Props) {
  const [telemetry, setTelemetry] = useState<Telemetry[]>([]);
  const [busy, setBusy] = useState(false);

  const isIntegration = system.system_type === "INTEGRATION";

  useEffect(() => {
    if (isIntegration) return;
    api.telemetry(system.code).then(setTelemetry).catch(() => undefined);
  }, [system.code, tick, isIntegration]);

  const last = telemetry[telemetry.length - 1];

  async function setFault(mode: FaultMode) {
    setBusy(true);
    try { await api.setFault(system.code, mode); onFaultChanged(); } finally { setBusy(false); }
  }

  return (
    <article className={`card system-card status-${system.status}`}>
      <header className="system-head">
        <div>
          <div className="system-code">{system.code}</div>
          <h3>{system.name}</h3>
        </div>
        <StatusBadge value={system.status} />
      </header>

      <p className="muted small">{system.description}</p>
      <div className="tags">
        {system.gxp_relevant && <span className="tag">GxP</span>}
        {system.gamp_category && <span className="tag">GAMP {system.gamp_category}</span>}
        <span className="tag">Owner: {system.owner}</span>
      </div>

      {isIntegration ? (
        <>
          <dl className="metrics">
            <div><dt>Monitored by</dt><dd>Import runs</dd></div>
            <div><dt>Last sync</dt><dd>{ago(system.last_heartbeat_at)}</dd></div>
          </dl>
          <p className="small status-reason">{system.status_reason || "Waiting for the first sync."}</p>
          <a className="card-link small" href="#/integrations">Open integration →</a>
        </>
      ) : (<>
      <LatencySparkline points={telemetry} threshold={LATENCY_THRESHOLD_MS} />

      <dl className="metrics">
        <div><dt>Latency</dt><dd>{last ? `${last.latency_ms} ms` : "–"}</dd></div>
        <div><dt>Error rate</dt><dd>{last ? `${(last.error_rate * 100).toFixed(1)} %` : "–"}</dd></div>
        <div><dt>Heartbeat</dt><dd>{ago(system.last_heartbeat_at)}</dd></div>
      </dl>
      <p className="small status-reason">{system.status_reason}</p>
      {last && <p className="small muted activity">{last.message}</p>}

      {canInjectFault && (
        <div className="fault">
          <label htmlFor={`fault-${system.code}`} className="small">Simulator fault (demo)</label>
          <select id={`fault-${system.code}`} disabled={busy} value={system.simulated_fault ?? ""}
                  onChange={(e) => setFault((e.target.value || null) as FaultMode)}>
            {FAULTS.map((f) => <option key={f.text} value={f.value ?? ""}>{f.text}</option>)}
          </select>
        </div>
      )}
      </>)}
    </article>
  );
}
