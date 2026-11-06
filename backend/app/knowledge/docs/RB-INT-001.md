---
doc_id: RB-INT-001
title: "Runbook: openFDA recall interface (INT-FDA-01)"
type: runbook
version: "1.0"
effective: 2026-11-05
owner: Head of Quality Assurance
---

## 1 How the interface works
INT-FDA-01 imports FDA drug enforcement reports (recalls) from the openFDA API every 6 hours, covering
recalls reported in the last 30 days. Every record is validated before it is stored. Each run is
recorded as an import run (ING-nnnnnn) with the number of records fetched, new, changed, unchanged and
rejected. Re-importing unchanged recalls creates no duplicates.

## 2 Integration down: import failed
Symptom: the last import run has status "failed" and INT-FDA-01 is down, for example "Could not reach
openFDA" or "HTTP 500". Nothing was imported.
1. Acknowledge the incident. Check internet access from the worker and the openFDA status page.
2. An HTTP 429 means the rate limit was hit: configure an openFDA API key (FDA_API_KEY).
3. Start a manual sync ("Sync from openFDA") once the cause is fixed. A successful run brings the
   integration back to operational; the incident stays open until resolved and closed.

## 3 Integration degraded: too many rejected records
Symptom: more than 10 % of the records in a run were rejected. Rejected records are kept in
quarantine with all reasons; they are never stored as recalls.
1. Open the import run and review the reasons of each quarantined record.
2. Decide whether the source data is faulty (for example a missing or invalid recall number) or
   whether a validation rule no longer matches the source format.
3. Faulty source data: no action in Syntra; corrected records are imported by a later run.
4. Validation rule out of date: raise a change request (SOP-ITO-002). Never relax a rule without
   change control.

## 4 Typical rejection reasons
- Missing required field, for example no recall_number.
- Recall number not in the format X-NNNN-YYYY, for example "N/A".
- Unknown classification (only Class I, II and III exist) or unknown status.
- Invalid date or a date in the future; termination date before initiation date.
- Duplicate recall number within the same run.

## 5 Recall classes
- Class I: reasonable probability that the product will cause serious adverse health consequences
  or death.
- Class II: the product may cause temporary or medically reversible adverse health consequences, or
  serious consequences are remote.
- Class III: the product is unlikely to cause adverse health consequences.
