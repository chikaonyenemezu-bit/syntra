---
doc_id: RB-MES-001
title: "Runbook: MES-01 down or degraded"
type: runbook
version: "1.3"
effective: 2026-08-20
owner: IT Operations
---

## 1 Symptoms
- Syntra shows MES-01 as down: "No heartbeat since …" or "System reports down".
- Operators on Tablet Line 2 cannot open or complete electronic batch record (EBR) steps.
- MES-01 degraded: slow screens, latency above 1500 ms or error rate above 5 %.

## 2 Immediate actions
1. Acknowledge the incident in Syntra. An MES outage is critical because MES-01 is GxP-relevant.
2. Call the shift supervisor of Tablet Line 2. Production decides whether to pause the line or
   continue with the paper backup batch record (form PBR-02) according to the business continuity
   plan. IT Operations does not make this decision.
3. Inform QA immediately. QA must be aware of any batch steps documented on paper.

## 3 Diagnosis
1. Check the MES application server and the EBR service status in the server console.
2. Check the network connection between the shop-floor terminals and the MES server.
3. Check whether ERP-01 and LIMS-01 are also affected: several systems down at once points to
   network or infrastructure.
4. Review the MES application log for the time of the last heartbeat shown in Syntra.

## 4 Recovery
1. Restart the EBR application service. Do not restart the database server without consulting the
   database administrator.
2. Confirm that terminals reconnect and that open batch steps are intact. No EBR data may be
   re-entered from memory; missing entries are handled as a deviation by QA.
3. When Syntra shows MES-01 as operational again, the incident is marked as recovered. Resolve it
   with a note stating the root cause and the action taken.

## 5 After the incident
QA closes the incident and decides whether a deviation is needed, for example when paper backup
records must be reconciled into the EBR. If the fix required a configuration or software change, raise
a change request (SOP-ITO-002), retrospectively within 2 working days for an emergency change.
