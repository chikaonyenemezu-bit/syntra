---
doc_id: SOP-ITO-002
title: Change Control for Computerised Systems
type: sop
version: "3.1"
effective: 2026-07-15
owner: Head of Quality Assurance
---

## 1 Purpose
This procedure ensures that changes to computerised systems are assessed, approved, implemented and
verified in a controlled way, so that systems remain in a validated state (EU GMP Annex 11 §10).

## 2 Scope
Software upgrades and patches, configuration changes, infrastructure changes, interface changes and
changes to user roles of systems listed in the Syntra system inventory.

## 3 Raising a change request
IT Operations, System Owners and QA can raise a change request in Syntra. The request starts as a
draft. Before submitting, the requester must describe what will change, why it is needed, and the
impact on GxP functions, data integrity and validation. Only the requester can edit or submit a draft.
A submitted change request can no longer be edited.

## 4 Categories and revalidation
- Minor change: no impact on validated functionality, for example a report layout fix.
- Major change: affects GxP functionality, data or interfaces, for example a new MES release.
Major changes normally require revalidation. While a change that requires revalidation is
implemented and tested, the system is shown as "in validation". The running version and the
validated version then differ until QA verifies the change.

## 5 Approval
Changes to GxP-relevant systems require two approvals: the System Owner and QA. Changes to systems
without GxP relevance require the System Owner only. Approvals are electronic signatures
(SOP-ITO-004). Nobody may approve or reject their own change request, and each role approves once.
A rejection requires a written reason and closes the change request; a new request must be raised.

## 6 Implementation
Only IT Operations implements approved changes, normally in a planned maintenance window. The
implementer records an implementation note: what was deployed, when, and how installation was checked.
Changes must not be implemented before all approvals are signed.

## 7 Verification and closure
QA verifies the implemented change with documented evidence, for example an executed test protocol,
and signs the verification. QA may not verify a change they requested or implemented. Verification
records the new validated version. For changes that required revalidation the system returns to the
validated state with the verification date as the new validation date.

## 8 Emergency changes
If a change is needed immediately to restore a GxP-critical service, IT Operations may implement it
with verbal approval from the System Owner and QA. A change request must be raised and approved
retrospectively within 2 working days and referenced in the related incident.
