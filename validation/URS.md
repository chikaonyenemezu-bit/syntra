# User Requirements Specification (URS)

**System:** Syntra (Connected Systems Intelligence) · **Version:** 0.4 (draft) · **Scope of this version:** Monitoring, incidents, access control, audit trail, external data integration, GxP lifecycle (change control, periodic review, electronic signatures), Knowledge Assistant (AI)

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

## 5. External data integration (openFDA drug recalls)

| ID | Requirement | Priority |
|---|---|---|
| URS-INT-01 | The platform shall import drug recall records from the openFDA enforcement API on a configurable schedule, and on demand by authorised users. | High |
| URS-INT-02 | Every import run shall be recorded with source, trigger, user, start and end time, and the number of records fetched, inserted, updated, unchanged and rejected. | High |
| URS-INT-03 | Each record shall be validated before it is stored: required fields, allowed classification and status values, product type, recall number format, valid and non-future dates, termination not before initiation, no duplicates within a run. | High |
| URS-INT-04 | Records that fail validation shall not be stored as recalls. They shall be kept in quarantine with the original content and every reason for rejection. | High |
| URS-INT-05 | A recall that changes in the source shall be updated, and the changed fields with old and new values shall be recorded in the audit trail. Re-importing unchanged data shall not create duplicates. | High |
| URS-INT-06 | A failed import shall mark the integration *down*; a rejection rate above the configured threshold shall mark it *degraded*; both shall open an incident through the incident workflow. | High |
| URS-INT-07 | When no import has succeeded for more than twice the schedule interval, the integration shall be marked *degraded*. | Medium |
| URS-INT-08 | Authorised users shall be able to search stored recalls by product, firm, reason, recall number and lot information, and filter by classification. | Medium |
| URS-INT-09 | Only IT Operations and administrators shall be able to start an import manually. | High |

## 6. GxP lifecycle

### 6.1 System inventory and validation state

| ID | Requirement | Priority |
|---|---|---|
| URS-LC-01 | Each computerised system shall have a lifecycle record: GAMP category, risk class, running version, validated version, validation status, validation date and reference, and periodic review interval. | High |
| URS-LC-02 | The validation state shall not be editable directly. It shall change only through a verified change request or a signed periodic review. | High |
| URS-LC-03 | The platform shall show when the running version differs from the validated version. | High |
| URS-LC-04 | The next periodic review date shall be calculated from the last review (or the validation date) and the interval, and shown as in order, due soon (60 days) or overdue. | High |
| URS-LC-05 | Periodic reviews shall be recorded and signed by QA, with outcome and summary, only for validated systems. | High |

### 6.2 Change control

| ID | Requirement | Priority |
|---|---|---|
| URS-CC-01 | IT Operations, System Owners and QA shall be able to raise change requests with description, justification, impact assessment, category, risk, revalidation need and target version. | High |
| URS-CC-02 | A change request shall follow draft → in review → approved → implemented → verified, or be rejected in review. Other transitions shall be refused. | High |
| URS-CC-03 | Only the requester shall edit or submit a draft. Description, justification and impact assessment are required for submission. Submitted requests shall not be editable. | High |
| URS-CC-04 | Changes to GxP-relevant systems shall require signed approval by the System Owner and by QA; other systems by the System Owner. | High |
| URS-CC-05 | No one shall approve or reject their own change request; each role approves once; administrators are not approvers. | High |
| URS-CC-06 | Only IT Operations shall implement an approved change, with an implementation note. Implementing a change that requires revalidation shall set the system to "in validation" and update the running version. | High |
| URS-CC-07 | Only QA shall verify an implemented change, with evidence and a signature, and never a change they requested or implemented. Verification shall update the validated version and, for revalidation, set the system to "validated" with the verification date. | High |
| URS-CC-08 | A rejection shall require a signed reason and shall be final. | Medium |

### 6.3 Electronic signatures

| ID | Requirement | Priority |
|---|---|---|
| URS-ES-01 | Approvals, rejections, verifications and periodic reviews shall be electronic signatures executed by re-entering the password. | High |
| URS-ES-02 | Each signature shall show the signer's printed name, user ID, role, date and time, and meaning, and be linked to the signed record (21 CFR Part 11 §11.50, §11.70). | High |
| URS-ES-03 | A failed signature attempt shall change nothing and shall be recorded in the audit trail. | High |
| URS-ES-04 | Signatures shall not be modifiable or deletable, enforced by the database. | High |

## 7. Knowledge Assistant (AI)

| ID | Requirement | Priority |
|---|---|---|
| URS-AI-01 | The assistant shall answer from the controlled documents (SOPs, runbooks, regulatory notes) and cite each statement with document, section and version. | High |
| URS-AI-02 | Every citation shall be checked against the sections the model was actually given; citations that cannot be verified shall be flagged to the user, not hidden. | High |
| URS-AI-03 | The assistant shall use live Syntra data only through read-only tools. It shall not be able to create, change, approve or close any record. | High |
| URS-AI-04 | Without a configured model, or when the model fails, the assistant shall return the most relevant document sections and state why no written answer is available. | High |
| URS-AI-05 | Every question shall be recorded with user, time, question, answer, provider and model, sources, live-data lookups and token use, and logged in the audit trail. | High |
| URS-AI-06 | The person who asked shall be able to rate an answer as helpful or report it as incorrect, with a comment; ratings shall be recorded. | Medium |
| URS-AI-07 | Documents shall be indexed with their version; new and changed versions shall be recorded in the audit trail; malformed documents shall be rejected. | High |
| URS-AI-08 | Retrieval shall be validated against a fixed evaluation set on every build: the expected document in the top 3 for at least 90 % of questions, the expected section for at least 80 %, and no match for out-of-scope questions. | High |
| URS-AI-09 | The API key shall be read from the environment only, never stored in code, returned by the API or written to logs. | High |
| URS-AI-10 | Text from documents and external sources (e.g. FDA recall texts) shall be passed to the model as data; the model shall be instructed not to follow instructions contained in it. | Medium |
