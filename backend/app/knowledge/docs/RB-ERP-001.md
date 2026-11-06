---
doc_id: RB-ERP-001
title: "Runbook: ERP-01 interface queue stopped or ERP degraded"
type: runbook
version: "1.0"
effective: 2026-05-18
owner: IT Operations
---

## 1 Symptoms
- ERP-01 down: "Interface queue to MES stopped".
- Process orders are not released to MES, or batch status changes do not reach ERP.
- ERP-01 degraded: slow goods receipt postings and stock queries.

## 2 Immediate actions
1. Acknowledge the incident in Syntra and inform the Supply Chain System Owner.
2. Check whether production is waiting for a process order. If so, inform the shift supervisor.
3. Do not post material movements twice by hand. Messages waiting in the queue are processed when
   the interface restarts.

## 3 Diagnosis
1. Open the interface monitor and check the outbound queue to MES for errors.
2. A single faulty message (for example an unknown material number) can block the whole queue.
3. Check the MES side: if MES-01 is down, the ERP queue stops by design.

## 4 Recovery
1. Correct or remove the faulty message following the interface error procedure, then restart the
   queue. Removing a message is documented with the message ID in the resolution note.
2. Confirm that the backlog is processed and that batch statuses in ERP and MES match.
3. Resolve the incident in Syntra.

## 5 After the incident
QA closes the incident and checks whether any batch status (for example quarantine or release) was
wrong during the outage. A material in quarantine must never be used because a status update was
delayed.
