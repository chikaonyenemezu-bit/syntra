# User Requirements Specification (URS)

**System:** Syntra (Connected Systems Intelligence) · **Version:** 0.1 (draft) · **Scope of this version:** Monitoring, incidents, access control, audit trail

| Field | Value |
|---|---|
| GxP relevance | Yes: the platform supports the operation of GxP computerised systems (MES, LIMS, ERP) |
| Proposed GAMP 5 category | 5 (custom application) |
| Regulatory basis | EU GMP Annex 11, 21 CFR Part 11, GAMP 5 (2nd ed.), ALCOA+ |

## 1. Monitoring

| ID | Requirement | Priority |
|---|---|---|
| URS-MON-01 | The platform shall receive periodic heartbeats from monitored systems and record latency, error rate and reported status. | High |
| URS-MON-02 | A system shall be shown as *degraded* when latency or error rate exceed configured thresholds. | High |
| URS-MON-03 | A system shall be shown as *down* when it reports itself down or sends no heartbeat within the configured timeout. | High |
| URS-MON-04 | Every change of system status shall be recorded in the audit trail with the reason. | High |

## 2. Incident management

| ID | Requirement | Priority |
|---|---|---|
| URS-INC-01 | A degraded or down system shall automatically open an incident. Repeated failures of the same outage shall not open duplicates. | High |
| URS-INC-02 | An outage of a GxP-relevant system shall be classified *critical*; a degradation that becomes an outage shall be escalated. | High |
| URS-INC-03 | When a system recovers, the incident shall be marked as recovered but shall **not** be closed automatically. | High |
| URS-INC-04 | Incidents shall follow the lifecycle open → acknowledged → resolved → closed. Other transitions shall be rejected. | High |
| URS-INC-05 | Resolving an incident shall require a resolution note (root cause and action). | High |
| URS-INC-06 | Incidents on GxP-relevant systems shall only be closed by QA. | High |
| URS-INC-07 | The person who resolved an incident shall not close it (four-eyes principle). | High |
| URS-INC-08 | Authorised users shall be able to report incidents manually. | Medium |

## 3. Access control

| ID | Requirement | Priority |
|---|---|---|
| URS-SEC-01 | All functions shall require an authenticated, individual user account. | High |
| URS-SEC-02 | Permissions shall be role-based (viewer, IT Ops, system owner, QA, admin). | High |
| URS-SEC-03 | Successful and failed logins shall be recorded in the audit trail. | High |

## 4. Audit trail and data integrity

| ID | Requirement | Priority |
|---|---|---|
| URS-AUD-01 | Every create or change of a GxP record shall be logged with user, UTC timestamp, action, record and details. | High |
| URS-AUD-02 | Audit records shall not be modifiable or deletable through the application or the database. | High |
| URS-AUD-03 | Tampering with audit records shall be detectable by a verification function available to QA. | High |
| URS-AUD-04 | The audit history of a record shall be viewable by authorised users. | Medium |
