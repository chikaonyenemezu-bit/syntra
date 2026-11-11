
import { useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import { can } from "../permissions";

import type {
  ChainCheck,
  Incident,
  Summary,
  System,
  User,
} from "../types";

import { SystemCard } from "../components/monitoring/SystemCard";
import { SystemDetailsDrawer } from "../components/monitoring/SystemDetailsDrawer";

import { IncidentTable } from "../components/incidents/IncidentTable";
import { IncidentDrawer } from "../components/incidents/IncidentDrawer";
import { NewIncidentForm } from "../components/incidents/NewIncidentForm";

const POLL_MS = 5000;

type Filter = "active" | "resolved" | "all";

export function OperationsCenter({ user }: { user: User }) {
  // --------------------------------------------------
  // State
  // --------------------------------------------------

  const [systems, setSystems] = useState<System[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);

  const [selected, setSelected] = useState<Incident | null>(null);

  // Selected system for the System Details Drawer
  const [selectedSystemCode, setSelectedSystemCode] =
    useState<string | null>(null);

  const [filter, setFilter] = useState<Filter>("active");
  const [creating, setCreating] = useState(false);

  const [chain, setChain] = useState<ChainCheck | null>(null);

  const [tick, setTick] = useState(0);

  const [loading, setLoading] = useState(true);
  const [refreshError, setRefreshError] = useState<string | null>(
    null
  );

  // --------------------------------------------------
  // Fetch latest operational data
  // --------------------------------------------------

  const refresh = useCallback(async () => {
    try {
      const [s, i, sum] = await Promise.all([
        api.systems(),
        api.incidents(),
        api.summary(),
      ]);

      setSystems(s);
      setIncidents(i);
      setSummary(sum);

      // Keep the selected incident synchronized
      // with the latest backend data.
      setSelected((current) => {
        if (!current) return null;

        return (
          i.find((incident) => incident.id === current.id) ??
          current
        );
      });

      setTick((current) => current + 1);

      setRefreshError(null);
    } catch (error) {
      console.error("Operations Center refresh failed:", error);

      setRefreshError(
        "Unable to retrieve the latest operational data."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // --------------------------------------------------
  // Poll systems and incidents every 5 seconds
  // --------------------------------------------------

  useEffect(() => {
    void refresh();

    const intervalId = window.setInterval(() => {
      void refresh();
    }, POLL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [refresh]);

  // --------------------------------------------------
  // Selected system
  // --------------------------------------------------

  const selectedSystem =
    systems.find(
      (system) => system.code === selectedSystemCode
    ) ?? null;

  // --------------------------------------------------
  // Incident filtering
  // --------------------------------------------------

  const shown = incidents.filter((incident) => {
    if (filter === "all") {
      return true;
    }

    if (filter === "active") {
      return (
        incident.status === "open" ||
        incident.status === "acknowledged"
      );
    }

    return incident.status === "resolved";
  });

  // --------------------------------------------------
  // Sort systems
  // Keep integrations after ERP, LIMS and MES
  // --------------------------------------------------

  const sortedSystems = [...systems].sort(
    (a, b) =>
      Number(a.system_type === "INTEGRATION") -
      Number(b.system_type === "INTEGRATION")
  );

  // --------------------------------------------------
  // Audit trail verification
  // --------------------------------------------------

  const verifyAuditTrail = async () => {
    try {
      setChain(null);

      const result = await api.verifyAudit();

      setChain(result);
    } catch (error) {
      console.error("Audit verification failed:", error);

      setRefreshError(
        "Audit verification failed. Please try again."
      );
    }
  };

  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <div className="page operations-page">
      <header className="page-head operations-head">
        <div>
          <p className="operations-breadcrumb">Workspace / Operations Center</p>
          <h1>Operations Center</h1>
          <p className="muted operations-subtitle">
            Connected systems and incident management overview
          </p>
        </div>

        {can.verifyAudit(user) && (
          <div className="verify">
            <button type="button" onClick={() => { void verifyAuditTrail(); }}>
              Verify audit trail
            </button>
            {chain && (
              <span className={`small ${chain.valid ? "ok-text" : "error"}`}>
                {chain.valid
                  ? `Intact: ${chain.records_checked} records verified`
                  : `Broken at record ${chain.first_broken_id}: ${chain.reason}`}
              </span>
            )}
          </div>
        )}
      </header>

      {refreshError && (
        <div className="card" role="alert">
          <p className="error">{refreshError}</p>
          <button type="button" onClick={() => { void refresh(); }}>Retry</button>
        </div>
      )}

      {loading && !summary && <p className="muted">Loading operational systems...</p>}

      {summary && (
        <section className="kpis operations-kpis" aria-label="Summary">
          <div className="kpi">
            <span>Systems operational</span>
            <strong>{summary.systems_by_status.operational ?? 0} / {summary.systems_total}</strong>
          </div>
          <div className="kpi">
            <span>Active incidents</span>
            <strong>{summary.incidents_active}</strong>
          </div>
          <div className={`kpi ${summary.incidents_critical_active ? "kpi-bad" : ""}`}>
            <span>Critical incidents</span>
            <strong>{summary.incidents_critical_active}</strong>
          </div>
          <div className="kpi">
            <span>Awaiting closure</span>
            <strong>{summary.incidents_awaiting_closure}</strong>
          </div>
        </section>
      )}

      <section className="card operations-panel" aria-labelledby="system-overview-heading">
        <div className="section-head operations-section-head">
          <h2 id="system-overview-heading">Connected systems</h2>
          <span className="small muted">{systems.length} monitored systems</span>
        </div>
        <div className="table-wrap operations-table-wrap">
          <table className="systems-table">
            <thead>
              <tr>
                <th scope="col">System</th>
                <th scope="col">Status</th>
                <th scope="col">GxP</th>
                <th scope="col">Latency</th>
                <th scope="col">Last update</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedSystems.map((system) => (
                <SystemCard
                  key={system.code}
                  compact
                  system={system}
                  tick={tick}
                  canInjectFault={can.injectFault(user)}
                  onFaultChanged={() => { void refresh(); }}
                  onViewDetails={() => { setSelectedSystemCode(system.code); }}
                />
              ))}
              {!loading && sortedSystems.length === 0 && (
                <tr><td colSpan={6} className="empty">No monitored systems found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card operations-panel operations-incidents" aria-labelledby="incident-register-heading">
        <div className="section-head operations-section-head">
          <h2 id="incident-register-heading">Incident register</h2>
          <div className="row">
            <div className="segmented" role="group" aria-label="Filter incidents">
              {(["active", "resolved", "all"] as Filter[]).map((currentFilter) => (
                <button key={currentFilter} type="button"
                        aria-pressed={filter === currentFilter}
                        onClick={() => setFilter(currentFilter)}>
                  {currentFilter === "resolved"
                    ? "Resolved"
                    : currentFilter.charAt(0).toUpperCase() + currentFilter.slice(1)}
                </button>
              ))}
            </div>
            {can.createIncident(user) && !creating && (
              <button type="button" className="primary" onClick={() => setCreating(true)}>
                Report incident
              </button>
            )}
          </div>
        </div>

        {creating && (
          <NewIncidentForm
            systems={systems}
            onCancel={() => setCreating(false)}
            onCreated={(incident) => {
              setCreating(false);
              setSelected(incident);
              void refresh();
            }}
          />
        )}
        <div className="operations-incident-scroll">
          <IncidentTable
            incidents={shown}
            onOpen={(incident) => {
              setSelectedSystemCode(null);
              setSelected(incident);
            }}
          />
        </div>
      </section>

      {selectedSystem && (
        <SystemDetailsDrawer
          system={selectedSystem}
          incidents={incidents}
          onClose={() => { setSelectedSystemCode(null); }}
          onOpenIncident={(incident) => {
            setSelectedSystemCode(null);
            setSelected(incident);
          }}
        />
      )}

      {selected && (
        <IncidentDrawer
          incident={selected}
          user={user}
          onClose={() => { setSelected(null); }}
          onChanged={(updatedIncident) => {
            setSelected(updatedIncident);
            void refresh();
          }}
        />
      )}
    </div>
  );
}
