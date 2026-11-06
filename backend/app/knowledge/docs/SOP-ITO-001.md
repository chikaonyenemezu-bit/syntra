---
doc_id: SOP-ITO-001
title: Incident Management for GxP Computerised Systems
type: sop
version: "2.0"
effective: 2026-09-01
owner: Head of IT Operations
---

## 1 Purpose
This procedure defines how IT Operations detects, records, classifies, resolves and closes incidents
on computerised systems, so that failures affecting product quality, patient safety or data integrity
are handled in a controlled and documented way.

## 2 Scope
All computerised systems in the Syntra system inventory, including MES-01, LIMS-01, ERP-01 and the
openFDA drug recall interface INT-FDA-01. Incidents on GxP-relevant systems follow the additional QA
steps in section 6.

## 3 Responsibilities
IT Operations acknowledges, investigates and resolves incidents. The System Owner is informed of
every incident on their system and decides on business workarounds. QA closes incidents on
GxP-relevant systems and decides whether a deviation must be opened.

## 4 Detection and recording
Incidents are opened automatically by the Syntra health monitor when a system becomes degraded or
down, or manually by IT Operations, a System Owner or QA. One outage produces one incident: repeated
failures of the same outage are added to the existing incident, not recorded as new ones.
Every incident receives a unique number (INC-nnnnnn) and every step is recorded in the audit trail.

## 5 Classification
Severity is assigned as follows:
- Critical: a GxP-relevant system is down. Production, release or quality decisions may be affected.
- High: a system without GxP relevance is down.
- Medium: a system is degraded (slow or error-prone) but still available.
- Low: minor issues without impact on operations.
If a degraded incident turns into an outage on a GxP-relevant system, it is escalated to critical.
Critical incidents must be acknowledged within 15 minutes during operating hours.

## 6 Investigation and resolution
1. Acknowledge the incident so others can see that it is being handled.
2. Follow the runbook for the affected system (RB-MES-001, RB-LIMS-001, RB-ERP-001, RB-INT-001).
3. Inform the System Owner. For critical incidents also inform QA immediately.
4. Restore the service. Do not change configuration or software outside an approved change
   request (SOP-ITO-002); an emergency change must be documented retrospectively within 2 working days.
5. Resolve the incident with a resolution note that states the root cause and the action taken.
A system that recovers by itself is marked as recovered, but the incident stays open: the cause must
still be investigated and documented.

## 7 Closure
Incidents on GxP-relevant systems are closed by QA. QA reviews the resolution note and decides whether
data created during the outage must be checked and whether a deviation is required, for example when
batch records were completed on paper during an MES outage.
The person who resolved an incident may not close it (four-eyes principle). Incidents without GxP
relevance can be closed by a second member of IT Operations.

## 8 Records
Incident records and their audit trail are kept for the lifetime of the system plus 5 years.
