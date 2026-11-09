
import { useEffect, useState } from "react";

import { api } from "../../services/api";
import { ago } from "../../format";

import type {
  FaultMode,
  System,
  Telemetry,
} from "../../types";

import { StatusBadge } from "../shared/StatusBadge";
import { LatencySparkline } from "./LatencySparkline";

// --------------------------------------------------
// Configuration
// --------------------------------------------------

const LATENCY_THRESHOLD_MS = 1500;

const FAULTS: { value: FaultMode; text: string }[] = [
  { value: null, text: "Normal" },
  { value: "degraded", text: "Degraded" },
  { value: "down", text: "Down" },
  { value: "silent", text: "Silent (no heartbeat)" },
];

// --------------------------------------------------
// Props
// --------------------------------------------------

interface Props {
  system: System;
  tick: number;
  canInjectFault: boolean;
  onFaultChanged: () => void;

  // Opens the System Details Drawer
  onViewDetails?: () => void;
}

// --------------------------------------------------
// System Card Component
// --------------------------------------------------

export function SystemCard({
  system,
  tick,
  canInjectFault,
  onFaultChanged,
  onViewDetails,
}: Props) {
  // --------------------------------------------------
  // State
  // --------------------------------------------------

  const [telemetry, setTelemetry] = useState<Telemetry[]>([]);

  const [busy, setBusy] = useState(false);

  const [faultError, setFaultError] = useState<string | null>(
    null
  );

  const isIntegration = system.system_type === "INTEGRATION";

  // --------------------------------------------------
  // Load system telemetry
  // --------------------------------------------------

  useEffect(() => {
    if (isIntegration) {
      return;
    }

    let cancelled = false;

    api
      .telemetry(system.code)
      .then((data) => {
        if (!cancelled) {
          setTelemetry(data);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.error(
            `Telemetry fetch failed for ${system.code}:`,
            error
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [system.code, tick, isIntegration]);

  // --------------------------------------------------
  // Latest telemetry record
  // --------------------------------------------------

  const last = telemetry[telemetry.length - 1];

  // --------------------------------------------------
  // Fault simulator
  // --------------------------------------------------

  async function setFault(mode: FaultMode) {
    if (busy || !canInjectFault || isIntegration) {
      return;
    }

    setBusy(true);
    setFaultError(null);

    try {
      await api.setFault(system.code, mode);

      // Refresh parent Operations Center
      onFaultChanged();
    } catch (error) {
      console.error(
        `Failed to update fault for ${system.code}:`,
        error
      );

      setFaultError(
        "Unable to update the simulator fault. Try again."
      );
    } finally {
      setBusy(false);
    }
  }

  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <article
      className={`card system-card status-${system.status}`}
    >
      {/* ----------------------------------------------
          System Header
      ---------------------------------------------- */}

      <header className="system-head">
        <div>
          <div className="system-code">
            {system.code}
          </div>

          <h3>{system.name}</h3>
        </div>

        <div className="system-head-actions">
          <StatusBadge value={system.status} />

          {/* Open system detail panel */}

          {onViewDetails && (
            <button
              type="button"
              className="system-view-button"
              onClick={onViewDetails}
              aria-label={`View details for ${system.code}`}
            >
              View details
            </button>
          )}
        </div>
      </header>

      {/* ----------------------------------------------
          System Description
      ---------------------------------------------- */}

      <p className="muted small">
        {system.description}
      </p>

      {/* ----------------------------------------------
          GxP Metadata
      ---------------------------------------------- */}

      <div className="tags">
        {system.gxp_relevant && (
          <span className="tag">GxP</span>
        )}

        {system.gamp_category && (
          <span className="tag">
            GAMP {system.gamp_category}
          </span>
        )}

        <span className="tag">
          Owner: {system.owner}
        </span>
      </div>

      {/* ----------------------------------------------
          External Integration
          Example: FDA-01
      ---------------------------------------------- */}

      {isIntegration ? (
        <>
          <dl className="metrics">
            <div>
              <dt>Monitored by</dt>
              <dd>Import runs</dd>
            </div>

            <div>
              <dt>Last sync</dt>
              <dd>
                {ago(system.last_heartbeat_at)}
              </dd>
            </div>
          </dl>

          <p className="small status-reason">
            {system.status_reason ||
              "Waiting for the first sync."}
          </p>

          <a
            className="card-link small"
            href="#/integrations"
          >
            Open integration →
          </a>
        </>
      ) : (
        <>
          {/* ------------------------------------------
              Telemetry Chart
          ------------------------------------------ */}

          <LatencySparkline
            points={telemetry}
            threshold={LATENCY_THRESHOLD_MS}
          />

          {/* ------------------------------------------
              Operational Metrics
          ------------------------------------------ */}

          <dl className="metrics">
            <div>
              <dt>Latency</dt>

              <dd>
                {last
                  ? `${last.latency_ms} ms`
                  : "–"}
              </dd>
            </div>

            <div>
              <dt>Error rate</dt>

              <dd>
                {last
                  ? `${(
                      last.error_rate * 100
                    ).toFixed(1)} %`
                  : "–"}
              </dd>
            </div>

            <div>
              <dt>Heartbeat</dt>

              <dd>
                {ago(system.last_heartbeat_at)}
              </dd>
            </div>
          </dl>

          {/* ------------------------------------------
              System Status Explanation
          ------------------------------------------ */}

          <p className="small status-reason">
            {system.status_reason}
          </p>

          {/* ------------------------------------------
              Latest System Activity
          ------------------------------------------ */}

          {last && (
            <p className="small muted activity">
              {last.message}
            </p>
          )}

          {/* ------------------------------------------
              Fault Simulator (Demo Only)
          ------------------------------------------ */}

          {canInjectFault && (
            <div className="fault">
              <label
                htmlFor={`fault-${system.code}`}
                className="small"
              >
                Simulator fault (demo)
              </label>

              <select
                id={`fault-${system.code}`}
                disabled={busy}
                value={system.simulated_fault ?? ""}
                onChange={(event) => {
                  void setFault(
                    (event.target.value ||
                      null) as FaultMode
                  );
                }}
              >
                {FAULTS.map((fault) => (
                  <option
                    key={fault.text}
                    value={fault.value ?? ""}
                  >
                    {fault.text}
                  </option>
                ))}
              </select>

              {faultError && (
                <p
                  className="small error"
                  role="alert"
                >
                  {faultError}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </article>
  );
}
