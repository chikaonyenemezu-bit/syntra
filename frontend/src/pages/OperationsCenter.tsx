import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";
import { can } from "../permissions";
import type { ChainCheck, Incident, Summary, System, User } from "../types";
import { SystemCard } from "../components/monitoring/SystemCard";
import { IncidentTable } from "../components/incidents/IncidentTable";
import { IncidentDrawer } from "../components/incidents/IncidentDrawer";
import { NewIncidentForm } from "../components/incidents/NewIncidentForm";

const POLL_MS = 5000;
type Filter = "active" | "resolved" | "all";

export function OperationsCenter({ user }: { user: User }) {
  const [systems, setSystems] = useState<System[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [filter, setFilter] = useState<Filter>("active");
  const [creating, setCreating] = useState(false);
  const [chain, setChain] = useState<ChainCheck | null>(null);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(async () => {
    const [s, i, sum] = await Promise.all([api.systems(), api.incidents(), api.summary()]);
    setSystems(s); setIncidents(i); setSummary(sum);
    setSelected((cur) => (cur ? i.find((x) => x.id === cur.id) ?? cur : null));
    setTick((t) => t + 1);
  }, []);

  useEffect(() => {
    refresh().catch(() => undefined);
    const id = setInterval(() => refresh().catch(() => undefined), POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const shown = incidents.filter((i) =>
    filter === "all" ? true
      : filter === "active" ? i.status === "open" || i.status === "acknowledged"
      : i.status === "resolved");

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Operations Center</h1>
          <p className="muted">Live status of the GxP system landscape. Refreshes every {POLL_MS / 1000} s.</p>
        </div>
        {can.verifyAudit(user) && (
          <div className="verify">
            <button onClick={async () => setChain(await api.verifyAudit())}>Verify audit trail</button>
            {chain && (
              <span className={`small ${chain.valid ? "ok-text" : "error"}`}>
                {chain.valid ? `Intact: ${chain.records_checked} records verified`
                  : `Broken at record ${chain.first_broken_id}: ${chain.reason}`}
              </span>
            )}
          </div>
        )}
      </header>

      {summary && (
        <section className="kpis" aria-label="Summary">
          <div className="kpi"><span>Systems operational</span>
            <strong>{summary.systems_by_status.operational ?? 0} / {summary.systems_total}</strong></div>
          <div className="kpi"><span>Active incidents</span><strong>{summary.incidents_active}</strong></div>
          <div className={`kpi ${summary.incidents_critical_active ? "kpi-bad" : ""}`}>
            <span>Critical</span><strong>{summary.incidents_critical_active}</strong></div>
          <div className="kpi"><span>Awaiting closure</span><strong>{summary.incidents_awaiting_closure}</strong></div>
        </section>
      )}

      <section className="systems">
        {systems.map((s) => (
          <SystemCard key={s.code} system={s} tick={tick} canInjectFault={can.injectFault(user)}
                      onFaultChanged={() => refresh().catch(() => undefined)} />
        ))}
      </section>

      <section className="card">
        <div className="section-head">
          <h2>Incidents</h2>
          <div className="row">
            <div className="segmented" role="group" aria-label="Filter incidents">
              {(["active", "resolved", "all"] as Filter[]).map((f) => (
                <button key={f} aria-pressed={filter === f} onClick={() => setFilter(f)}>
                  {f === "resolved" ? "Awaiting closure" : f[0].toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
            {can.createIncident(user) && !creating && (
              <button className="primary" onClick={() => setCreating(true)}>Report incident</button>
            )}
          </div>
        </div>
        {creating && (
          <NewIncidentForm systems={systems} onCancel={() => setCreating(false)}
                           onCreated={(i) => { setCreating(false); setSelected(i); refresh(); }} />
        )}
        <IncidentTable incidents={shown} onOpen={setSelected} />
      </section>

      {selected && (
        <IncidentDrawer incident={selected} user={user} onClose={() => setSelected(null)}
                        onChanged={(i) => { setSelected(i); refresh().catch(() => undefined); }} />
      )}
    </div>
  );
}
