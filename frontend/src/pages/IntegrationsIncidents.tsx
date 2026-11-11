import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";
import { can } from "../permissions";
import type { Incident, IngestionJob, Integration, User } from "../types";
import { IntegrationCard } from "../components/integrations/IntegrationCard";
import { JobDetail, JobHistory } from "../components/integrations/JobHistory";
import { RecallTable } from "../components/integrations/RecallTable";
import { IncidentTable } from "../components/incidents/IncidentTable";
import { IncidentDrawer } from "../components/incidents/IncidentDrawer";

const POLL_MS = 10000;

type Tab = "overview" | "imports" | "incidents" | "recalls";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "imports", label: "Import runs" },
  { key: "incidents", label: "Incidents" },
  { key: "recalls", label: "Drug recalls" },
];

export function IntegrationsIncidents({ user }: { user: User }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(async () => {
    const [ints, js, incs] = await Promise.all([
      api.integrations(),
      api.jobs(),
      api.incidents(),
    ]);
    const codes = new Set(ints.map((integration) => integration.system.code));
    setIntegrations(ints);
    setJobs(js);
    setIncidents(
      incs.filter((incident) => incident.system_code && codes.has(incident.system_code))
    );
    setSelectedJob((current) => current ?? js[0]?.number ?? null);
    setSelectedIncident((current) =>
      current ? incs.find((incident) => incident.id === current.id) ?? current : null
    );
  }, []);

  useEffect(() => {
    void refresh().catch(() => undefined);
    const id = window.setInterval(() => {
      void refresh().catch(() => undefined);
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  return (
    <div className="page integrations-page">
      <header className="page-head">
        <div>
          <h1>Integrations &amp; Incidents</h1>
          <p className="muted">
            External data feeds, import validation, incidents, and drug recalls.
          </p>
        </div>
      </header>

      <div className="integration-tabs" role="tablist" aria-label="Integrations and incidents sections">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            id={`integration-tab-${key}`}
            className="integration-tab"
            role="tab"
            aria-selected={tab === key}
            aria-controls="integration-tab-panel"
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        className="integration-tab-panel"
        id="integration-tab-panel"
        role="tabpanel"
        aria-labelledby={`integration-tab-${tab}`}
      >
        {tab === "overview" && (
          <section className="integration-overview" aria-label="Integration overview">
            {integrations.map((integration) => (
              <IntegrationCard
                key={integration.system.code}
                integration={integration}
                canSync={can.syncIntegration(user)}
                onSynced={(job) => {
                  setSelectedJob(job.number);
                  setRefreshKey((current) => current + 1);
                  void refresh().catch(() => undefined);
                }}
              />
            ))}
          </section>
        )}

        {tab === "imports" && (
          <section className="card integration-section">
            <div className="section-head">
              <h2>Import runs</h2>
              <span className="small muted">Import history and validation results</span>
            </div>
            <JobHistory
              jobs={jobs}
              selected={selectedJob}
              onSelect={setSelectedJob}
            />
            {selectedJob && (
              <JobDetail number={selectedJob} refreshKey={refreshKey} />
            )}
          </section>
        )}

        {tab === "incidents" && (
          <section className="card integration-section">
            <div className="section-head">
              <h2>Integration incidents</h2>
              <span className="small muted">
                Opened when a feed fails or delivers too many invalid records
              </span>
            </div>
            <IncidentTable incidents={incidents} onOpen={setSelectedIncident} />
          </section>
        )}

        {tab === "recalls" && (
          <section className="card integration-section">
            <div className="section-head">
              <h2>Drug recalls</h2>
              <span className="small muted">
                Validated records from openFDA drug enforcement reports
              </span>
            </div>
            <RecallTable refreshKey={refreshKey} />
          </section>
        )}
      </div>

      {selectedIncident && (
        <IncidentDrawer
          incident={selectedIncident}
          user={user}
          onClose={() => setSelectedIncident(null)}
          onChanged={(updated) => {
            setSelectedIncident(updated);
            void refresh().catch(() => undefined);
          }}
        />
      )}
    </div>
  );
}
