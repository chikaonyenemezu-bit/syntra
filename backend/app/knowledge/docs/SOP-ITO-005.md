---
doc_id: SOP-ITO-005
title: Audit Trail Review
type: sop
version: "1.1"
effective: 2026-04-01
owner: Head of Quality Assurance
---

## 1 Purpose
Audit trails show who did what, when and why. This procedure defines how audit trails are protected
and reviewed (EU GMP Annex 11 §9, ALCOA+ principles).

## 2 What Syntra records
Every create or change of a GxP record is logged with user, UTC timestamp, action, record and details:
incidents, system status changes, import runs, recall updates, change requests, electronic signatures,
periodic reviews and logins, including failed logins and failed signature attempts.

## 3 Protection
Audit records cannot be changed or deleted: the database rejects such operations. Each record also
stores a cryptographic hash of the previous record. If any record were altered outside the
application, the chain would no longer match.

## 4 Integrity verification
QA verifies the integrity of the audit trail with the "Verify audit trail" function at least monthly
and before every periodic review. A broken chain is a critical incident: QA opens a deviation and IT
Security investigates. Do not attempt to repair the audit trail.

## 5 Routine review
QA reviews audit trail entries for GxP-critical events at least monthly, focusing on failed logins
and failed signatures, changes made outside the change control process, and records changed after
approval. Findings are documented and, where needed, raised as deviations.
