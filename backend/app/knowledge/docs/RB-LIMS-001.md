---
doc_id: RB-LIMS-001
title: "Runbook: LIMS-01 degraded or down"
type: runbook
version: "1.1"
effective: 2026-06-02
owner: IT Operations
---

## 1 Symptoms
- LIMS-01 degraded: slow sample registration or result entry, latency above 1500 ms.
- LIMS-01 down: "Database connection pool exhausted" or no heartbeat.
- Instrument results (for example from HPLC-07) are not imported.

## 2 Immediate actions
1. Acknowledge the incident in Syntra and inform the QC lab supervisor.
2. QC decides whether to pause testing. Results must not be recorded outside LIMS except on the
   approved paper worksheets; QA must be informed if worksheets are used.
3. A LIMS outage can delay batch release. Inform QA so release planning can be adjusted.

## 3 Diagnosis
1. Check the number of open database connections against the pool limit.
2. Look for long-running reports or stuck instrument import jobs holding connections.
3. Check disk space on the LIMS database server.

## 4 Recovery
1. Stop stuck import jobs from the LIMS admin console, then restart the LIMS application service.
2. Confirm that instrument import resumes and that results created during the incident are complete.
   Results must never be edited to fill gaps; missing results are re-imported from the instrument
   data system or handled as a deviation.
3. Resolve the incident in Syntra with the root cause and action taken.

## 5 After the incident
QA closes the incident. Recurring pool exhaustion is a candidate for a change request, for example to
increase the pool size or to reschedule heavy reports. Such a configuration change requires change
control (SOP-ITO-002).
