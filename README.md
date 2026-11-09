# Syntra
[![CI](https://github.com/chikaonyenemezu-bit/syntra/actions/workflows/ci.yml/badge.svg)](https://github.com/chikaonyenemezu-bit/syntra/actions/workflows/ci.yml)

**CONNECTED SYSTEMS INTELLIGENCE**

An intelligent enterprise IT platform for monitoring connected systems, managing integrations and
incidents, supporting GxP lifecycle workflows, and providing AI-assisted knowledge retrieval.

Syntra runs against a simulated pharmaceutical IT landscape (MES, LIMS, ERP) plus a live external
data feed (openFDA drug recalls), and is built the way a regulated system should be: role-based access, a tamper-evident audit trail, and requirements traced
to automated tests.

**Status:** v0.4 · Operations Center, Integrations, GxP Lifecycle and Knowledge Assistant working (steps 1–5 of 6).

## What works now

- **Simulated systems:** MES (electronic batch records), LIMS (QC lab) and ERP send heartbeats every 10 s.
- **Health monitoring:** latency, error rate and heartbeat timeouts turn into *operational / degraded / down*.
- **Automatic incidents:** an outage opens one incident (critical for GxP systems), escalates if it gets worse,
  and is marked *recovered* when the system comes back, but stays open until a human resolves and closes it.
- **GxP incident workflow:** open → acknowledged → resolved (note required) → closed.
  GxP incidents can only be closed by QA, and never by the person who resolved them (four-eyes).
- **Audit trail:** every change and every login is recorded. The database rejects `UPDATE`, `DELETE`
  and `TRUNCATE` on the audit table, and each record carries the hash of the previous one, so QA can
  verify the whole chain with one click.
- **Fault injection (demo):** set any system to *degraded*, *down* or *silent* from the UI.
- **openFDA recall integration:** the worker imports FDA drug enforcement reports every 6 hours.
  Every record is validated (required fields, classification, status, dates, recall number format,
  duplicates). Invalid records are **quarantined with their reasons**, never silently dropped.
  Changed recalls (e.g. *Ongoing → Terminated*) are updated and the field-level change is audited.
- **Integration health:** the feed is a monitored system (`INT-FDA-01`). A failed fetch makes it
  *down*, more than 10 % rejected records make it *degraded*, and no successful sync for too long
  makes it *degraded*. Each opens an incident through the same GxP workflow.
- **Import run history:** every run is recorded with fetched / new / changed / unchanged / rejected
  counts, duration, source and who triggered it.
- **Recall browser:** search by product, firm, reason, recall or lot number; filter by class.
- **System inventory:** each system's GAMP category, risk, running vs. validated version, validation
  status and periodic review due date (in order / due soon / overdue).
- **Change control:** draft → in review → approved → implemented → verified. GxP systems need
  signed approval by the System Owner **and** QA; nobody approves their own request; IT Ops
  implements; an independent QA member verifies. A change requiring revalidation puts the system
  *in validation* until it is verified, then updates the validated version.
- **Electronic signatures (21 CFR Part 11 style):** approvals, rejections, verifications and periodic
  reviews require re-entering the password. Each signature shows name, user, role, date/time and
  meaning; failed attempts are audited; the database refuses to change or delete signatures.
- **Periodic reviews:** QA records and signs them; the next due date is recalculated.
- **Knowledge Assistant:** answers questions from 11 controlled documents (SOPs for incidents, change
  control, periodic review, e-signatures and audit trail review; runbooks for MES, LIMS, ERP and the
  openFDA interface; reference notes on 21 CFR Part 11 and EU GMP Annex 11), combined with live data.
  Works with Claude, OpenAI or Groq. Every citation is checked against the sections the model was given, and
  unverifiable ones are flagged. The model can only *read* Syntra data. Without an API key it still
  shows the matching sections. Every question is recorded, and answers can be rated.

## Run it

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8080 and sign in. All demo users use the password `demo1234`:

| User | Role | Can |
|---|---|---|
| `it.ops` / `it.ops2` | IT Operations | acknowledge, resolve, inject faults, run integration syncs |
| `qa.lead` / `qa.reviewer` | QA | close GxP incidents, approve and verify changes, sign periodic reviews, verify audit trail |
| `system.owner` | System owner | report incidents, approve changes |
| `viewer` | Read-only | view |
| `admin` | Admin | inject faults, run integration syncs, verify audit trail |

API docs: http://localhost:8000/docs

### Without Docker

```bash
# Database: any PostgreSQL 16, e.g. docker compose up db
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload            # terminal 1
python -m app.worker.jobs                # terminal 2

cd frontend
npm install && npm run dev               # terminal 3 → http://localhost:5173
```

## Demo in 2 minutes

1. Sign in as `it.ops`. All three systems are green.
2. On **MES-01**, set the simulator fault to **Silent**. After ~45 s the MES turns red and a **critical** incident opens.
3. Set the fault back to **Normal**. The incident shows **Recovered** but stays open.
4. Open the incident, **Acknowledge**, then **Resolve** with a note. Try to close it: not allowed.
5. Sign in as `it.ops2`: still not allowed (GxP needs QA).
6. Sign in as `qa.lead`, close the incident, and click **Verify audit trail**.

### Integration demo

1. Open **Integrations & Incidents** as `it.ops`. On first start the worker already tried a live sync
   from openFDA (it needs internet access).
2. Click **Load sample data**: 12 recalls imported, the integration is *operational*.
3. Click **Load sample with errors**: 6 of 14 records are rejected, the integration turns *degraded*
   and an incident opens. Click the run to see each quarantined record and why it was rejected.
   One recall changed from *Ongoing* to *Terminated*; the audit trail shows the field-level change.
4. Click **Load sample data** again: the integration recovers; the incident stays open for review.

### Knowledge Assistant setup

Add one API key to `.env` (never commit it; `.env` is git-ignored), then restart:

```bash
ANTHROPIC_API_KEY=sk-ant-...      # Claude (default model claude-sonnet-5-5)
# or
OPENAI_API_KEY=sk-...             # OpenAI Responses API (default model gpt-6-luna)
# or
GROQ_API_KEY=gsk_...              # Groq, OpenAI-compatible (default model openai/gpt-oss-120b)
LLM_MODEL=                        # optional: another model name, e.g. llama-3.3-70b-versatile on Groq
```

```bash
docker compose up -d --force-recreate api
```

The Knowledge Assistant page shows which provider and model are active. Try the suggested questions,
or open an incident and click **Ask the Knowledge Assistant about this incident**.

### Change control demo

1. As `it.ops`, open **GxP Lifecycle**. LIMS-01's periodic review is overdue, ERP-01's is due soon,
   and the openFDA interface is not validated yet.
2. **New change request** for MES-01: category *Major*, target version `3.3.0`. Create the draft,
   then **Submit for approval**.
3. As `system.owner`: open it, **Approve…** and sign with the password. Still one approval pending.
4. As `qa.lead`: **Approve…** and sign. The change is approved.
5. As `it.ops2`: **Mark as implemented**. MES-01 now runs 3.3.0 but is *in validation*
   (validated version still 3.2.1).
6. As `qa.reviewer`: **Verify…** with test evidence and sign. MES-01 is validated at 3.3.0, and the
   change shows all three signatures.
7. As `qa.lead`: open **LIMS-01** and sign a periodic review; it is no longer overdue.

The sample files are synthetic records in openFDA format (invented firms and recall numbers), so
the demo works offline. Live data comes from https://open.fda.gov/apis/drug/enforcement/.

## Architecture

```
frontend (React + TypeScript, nginx) ──/api──▶ api (FastAPI)
                                                 │
                     worker (APScheduler) ───────┤  simulators → health monitor → incidents
                          │                      │
                          └── openFDA sync ──────┤  fetch → validate → quarantine / upsert → job record
                                                 ▼
                                   PostgreSQL 16 (+ pgvector for step 5)
```

| Folder | Contents |
|---|---|
| `backend/app/models` | Systems, telemetry, incidents, users, audit events, recalls, ingestion jobs, rejected records, lifecycle, periodic reviews, change requests, e-signatures |
| `backend/app/services` | `health_monitor`, `incident_manager`, `audit_logger`, `data_validator`, `fda_pipeline`, `lifecycle_manager`, `esign`, `knowledge_index`, `retrieval`, `llm`, `assistant_tools`, `assistant` |
| `backend/app/integrations` | openFDA client and the synthetic sample fixtures |
| `backend/app/knowledge` | Controlled documents (Markdown) and the retrieval evaluation set |
| `backend/app/simulators` | MES, LIMS and ERP heartbeat simulators |
| `backend/app/worker` | Scheduled monitoring cycle |
| `backend/tests` | 89 tests: monitoring, incident rules, permissions, audit integrity, validation rules, sync pipeline, openFDA client, change control, segregation of duties, e-signatures, periodic reviews, document indexing, retrieval evaluation, Claude, OpenAI and Groq tool loops, citation checks, read-only tools |
| `validation/` | URS and traceability matrix (requirement → code → test) |

## Configuration

All settings come from environment variables (see `.env.example`). The integration ones:

| Variable | Default | Meaning |
|---|---|---|
| `FDA_SYNC_ENABLED` | `true` | Scheduled live sync in the worker |
| `FDA_SYNC_INTERVAL_MINUTES` | `360` | Time between scheduled syncs |
| `FDA_LOOKBACK_DAYS` | `30` | Import recalls reported in the last N days |
| `FDA_MAX_RECORDS` | `500` | Upper limit per run |
| `FDA_REJECTION_THRESHOLD` | `0.10` | Share of rejected records above which the integration is degraded |
| `FDA_API_KEY` | empty | Optional openFDA key for a higher rate limit |

## Troubleshooting

- **A container stopped (e.g. `worker-1 exited with code 1`):** `api` and `worker` restart
  automatically. To restart one by hand: `docker compose restart worker`.
- **The page looks outdated after an update:** reload once. If it still looks old, reload with
  `Cmd + Shift + R` (Mac) or `Ctrl + Shift + R` (Windows).
- **Start from an empty database:** `docker compose down -v`, then `docker compose up --build`.

## Tests

```bash
cd backend && python -m pytest -v          # SQLite, fast
DATABASE_URL=postgresql+psycopg://syntra:syntra@localhost:5432/syntra python smoke_pg.py
```

CI (GitHub Actions) runs both, builds the frontend and both Docker images, and keeps the JUnit
report as test evidence.

## Roadmap

| Step | Scope | Status |
|---|---|---|
| 1 | Database, models, auth, audit trail | Done |
| 2 | Simulators, health monitoring, incidents, Operations Center | Done |
| 3 | openFDA recall integration with data validation, quarantine, job history, integration incidents | Done |
| 4 | GxP Lifecycle: system inventory, change control with dual approval, periodic review, electronic signatures | Done |
| 5 | Knowledge Assistant: cited answers from controlled documents and live data, Claude, OpenAI or Groq | Done |
| 6 | Demo scenario script, end-to-end test, risk assessment, test protocol, Alembic migrations | Next |

## Disclaimer

Portfolio project. Systems, batches and users are simulated. Not a validated system.
