
import { useEffect } from "react";

import type { Incident, System } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

interface Props {
  system: System;
  incidents: Incident[];
  onClose: () => void;
  onOpenIncident: (incident: Incident) => void;
}

function belongsToSystem(
  incident: Incident,
  system: System
): boolean {
  const record = incident as unknown as Record<string, unknown>;
  const systemRecord = system as unknown as Record<string, unknown>;

  if (
    record.system_code === system.code ||
    record.source_system_code === system.code
  ) {
    return true;
  }

  const incidentSystemId =
    record.system_id ?? record.source_system_id;

  return (
    systemRecord.id != null &&
    incidentSystemId != null &&
    String(systemRecord.id) === String(incidentSystemId)
  );
}

export function SystemDetailsDrawer({
  system,
  incidents,
  onClose,
  onOpenIncident,
}: Props) {
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [onClose]);

  const relatedIncidents = incidents.filter((incident) =>
    belongsToSystem(incident, system)
  );

  const activeIncidents = relatedIncidents.filter(
    (incident) =>
      incident.status === "open" ||
      incident.status === "acknowledged"
  );

  return (
    <div
      className="drawer-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="system-details-title"
      >
        {/* Header */}

        <header className="drawer-head">
          <div>
            <div className="system-code">{system.code}</div>
            <h2 id="system-details-title">System Details</h2>
          </div>

          <button type="button" onClick={onClose}>
            Close
          </button>
        </header>

        {/* System information */}

        <section className="card">
          <h3>{system.name}</h3>

          <p className="muted small">{system.description}</p>

          <div className="tags">
            {system.gxp_relevant && (
              <span className="tag">GxP</span>
            )}

            {system.gamp_category && (
              <span className="tag">
                GAMP {system.gamp_category}
              </span>
            )}

            <span className="tag">Owner: {system.owner}</span>
          </div>
        </section>

        {/* Operational status */}

        <section className="card">
          <h3>Operational Status</h3>

          <div style={{ marginTop: 12 }}>
            <StatusBadge value={system.status} />
          </div>

          <p className="small" style={{ marginTop: 12 }}>
            {system.status_reason ||
              "No additional status information."}
          </p>
        </section>

        {/* Incident summary */}

        <section className="card">
          <h3>Incident Summary</h3>

          <dl className="metrics">
            <div>
              <dt>Total incidents</dt>
              <dd>{relatedIncidents.length}</dd>
            </div>

            <div>
              <dt>Active incidents</dt>
              <dd>{activeIncidents.length}</dd>
            </div>
          </dl>
        </section>

        {/* Compact associated incident cards */}

        <section className="card">
          <div className="section-head">
            <h3>Associated Incidents</h3>
            <span className="tag">
              {relatedIncidents.length} incident
              {relatedIncidents.length !== 1 ? "s" : ""}
            </span>
          </div>

          {relatedIncidents.length === 0 ? (
            <p className="muted small">
              No associated incidents found for this system.
            </p>
          ) : (
            <div className="system-incident-list">
              {relatedIncidents.map((incident) => {
                const record = incident as unknown as Record<
                  string,
                  unknown
                >;

                const number = String(
                  record.number ?? record.incident_number ??
                    `#${incident.id}`
                );

                const title = String(
                  record.title ?? "Untitled incident"
                );

                const severity = String(
                  record.severity ?? "unknown"
                );

                const status = String(incident.status);

                const recovered =
                  record.recovered === true ||
                  record.recovery_status === "recovered";

                return (
                  <article
                    className="system-incident-card"
                    key={incident.id}
                  >
                    <div className="system-incident-top">
                      <button
                        type="button"
                        className="link system-incident-link"
                        onClick={() => onOpenIncident(incident)}
                      >
                        {number}
                      </button>

                      <span
                        className={`badge ${
                          severity.toLowerCase() === "critical"
                            ? "badge-bad"
                            : severity.toLowerCase() === "high"
                              ? "badge-warn"
                              : "badge-info"
                        }`}
                      >
                        {severity}
                      </span>
                    </div>

                    <p className="system-incident-title">
                      {title}
                    </p>

                    <div className="system-incident-statuses">
                      {recovered && (
                        <span className="badge badge-ok">
                          Recovered
                        </span>
                      )}

                      <span
                        className={`badge ${
                          status === "open"
                            ? "badge-bad"
                            : status === "acknowledged"
                              ? "badge-warn"
                              : status === "resolved"
                                ? "badge-ok"
                                : "badge-muted"
                        }`}
                      >
                        {status.charAt(0).toUpperCase() +
                          status.slice(1)}
                      </span>
                    </div>

                    <p className="muted small">
                      System: {system.code}
                    </p>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </aside>
    </div>
  );
}
