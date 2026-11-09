
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
    <div className="page">
      {/* Page header */}

      <header className="page-head">
        <div>
          <h1>Operations Center</h1>

          <p className="muted">
            Live status of the GxP system landscape.
            Refreshes every {POLL_MS / 1000} s.
          </p>
        </div>

        {/* Audit verification */}

        {can.verifyAudit(user) && (
          <div className="verify">
            <button
              type="button"
              onClick={() => {
                void verifyAuditTrail();
              }}
            >
              Verify audit trail
            </button>

            {chain && (
              <span
                className={`small ${
                  chain.valid ? "ok-text" : "error"
                }`}
              >
                {chain.valid
                  ? `Intact: ${chain.records_checked} records verified`
                  : `Broken at record ${chain.first_broken_id}: ${chain.reason}`}
              </span>
            )}
          </div>
        )}
      </header>

      {/* Refresh error */}

      {refreshError && (
        <div className="card" role="alert">
          <p className="error">{refreshError}</p>

          <button
            type="button"
            onClick={() => {
              void refresh();
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Initial loading state */}

      {loading && !summary && (
        <p className="muted">
          Loading operational systems...
        </p>
      )}

      {/* --------------------------------------------------
          KPI Summary
      -------------------------------------------------- */}

      {summary && (
        <section className="kpis" aria-label="Summary">
          <div className="kpi">
            <span>Systems operational</span>

            <strong>
              {summary.systems_by_status.operational ?? 0}
              {" / "}
              {summary.systems_total}
            </strong>
          </div>

          <div className="kpi">
            <span>Active incidents</span>

            <strong>{summary.incidents_active}</strong>
          </div>

          <div
            className={`kpi ${
              summary.incidents_critical_active
                ? "kpi-bad"
                : ""
            }`}
          >
            <span>Critical</span>

            <strong>
              {summary.incidents_critical_active}
            </strong>
          </div>

          <div className="kpi">
            <span>Awaiting closure</span>

            <strong>
              {summary.incidents_awaiting_closure}
            </strong>
          </div>
        </section>
      )}

      {/* --------------------------------------------------
          System Monitoring Cards
      -------------------------------------------------- */}

      <section className="systems">
        {sortedSystems.map((system) => (
          <SystemCard
            key={system.code}
            system={system}
            tick={tick}
            canInjectFault={can.injectFault(user)}
            onFaultChanged={() => {
              void refresh();
            }}
            onViewDetails={() => {
              setSelectedSystemCode(system.code);
            }}
          />
        ))}
      </section>

      {/* --------------------------------------------------
          Incident Management
      -------------------------------------------------- */}

      <section className="card">
        <div className="section-head">
          <h2>Incidents</h2>

          <div className="row">
            {/* Incident filters */}

            <div
              className="segmented"
              role="group"
              aria-label="Filter incidents"
            >
              {(
                ["active", "resolved", "all"] as Filter[]
              ).map((currentFilter) => (
                <button
                  key={currentFilter}
                  type="button"
                  aria-pressed={
                    filter === currentFilter
                  }
                  onClick={() =>
                    setFilter(currentFilter)
                  }
                >
                  {currentFilter === "resolved"
                    ? "Resolved"
                    : currentFilter
                        .charAt(0)
                        .toUpperCase() +
                      currentFilter.slice(1)}
                </button>
              ))}
            </div>

            {/* Manual incident reporting */}

            {can.createIncident(user) && !creating && (
              <button
                type="button"
                className="primary"
                onClick={() => setCreating(true)}
              >
                Report incident
              </button>
            )}
          </div>
        </div>

        {/* New incident form */}

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

        {/* Incident table */}

        <IncidentTable
          incidents={shown}
          onOpen={(incident) => {
            setSelectedSystemCode(null);
            setSelected(incident);
          }}
        />
      </section>

      {/* --------------------------------------------------
          System Details Drawer
      -------------------------------------------------- */}

      {selectedSystem && (
        <SystemDetailsDrawer
          system={selectedSystem}
          incidents={incidents}
          onClose={() => {
            setSelectedSystemCode(null);
          }}
          onOpenIncident={(incident) => {
            setSelectedSystemCode(null);
            setSelected(incident);
          }}
        />
      )}

      {/* --------------------------------------------------
          Incident Investigation Drawer
      -------------------------------------------------- */}

      {selected && (
        <IncidentDrawer
          incident={selected}
          user={user}
          onClose={() => {
            setSelected(null);
          }}
          onChanged={(updatedIncident) => {
            setSelected(updatedIncident);
            void refresh();
          }}
        />
      )}
    </div>
  );
}
