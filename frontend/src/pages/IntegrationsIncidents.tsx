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

export function IntegrationsIncidents({ user }: { user: User }) {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(async () => {
    const [ints, js, incs] = await Promise.all([api.integrations(), api.jobs(), api.incidents()]);
    const codes = new Set(ints.map((i) => i.system.code));
    setIntegrations(ints);
    setJobs(js);
    setIncidents(incs.filter((i) => i.system_code && codes.has(i.system_code)));
    setSelectedJob((cur) => cur ?? js[0]?.number ?? null);
    setSelectedIncident((cur) => (cur ? incs.find((x) => x.id === cur.id) ?? cur : null));
  }, []);

  useEffect(() => {
    refresh().catch(() => undefined);
    const id = setInterval(() => refresh().catch(() => undefined), POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Integrations & Incidents</h1>
          <p className="muted">
            External data feeds, every import run with its validation results, and the incidents they raised.
          </p>
        </div>
      </header>

      {integrations.map((i) => (
        <IntegrationCard key={i.system.code} integration={i} canSync={can.syncIntegration(user)}
                         onSynced={(job) => {
                           setSelectedJob(job.number);
                           setRefreshKey((k) => k + 1);
                           refresh().catch(() => undefined);
                         }} />
      ))}

      <section className="card">
        <div className="section-head"><h2>Import runs</h2></div>
        <JobHistory jobs={jobs} selected={selectedJob} onSelect={setSelectedJob} />
        {selectedJob && <JobDetail number={selectedJob} refreshKey={refreshKey} />}
      </section>

      <section className="card">
        <div className="section-head">
          <h2>Integration incidents</h2>
          <span className="small muted">Opened automatically when a feed fails or delivers too many invalid records</span>
        </div>
        <IncidentTable incidents={incidents} onOpen={setSelectedIncident} />
      </section>

      <section className="card">
        <div className="section-head">
          <h2>Drug recalls</h2>
          <span className="small muted">Validated records from openFDA drug enforcement reports</span>
        </div>
        <RecallTable refreshKey={refreshKey} />
      </section>

      {selectedIncident && (
        <IncidentDrawer incident={selectedIncident} user={user} onClose={() => setSelectedIncident(null)}
                        onChanged={(i) => { setSelectedIncident(i); refresh().catch(() => undefined); }} />
      )}
    </div>
  );
}
