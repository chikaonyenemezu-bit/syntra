# Syntra
[![CI](https://github.com/chikaonyenemezu-bit/syntra/actions/workflows/ci.yml/badge.svg)](https://github.com/chikaonyenemezu-bit/syntra/actions/workflows/ci.yml)

**CONNECTED SYSTEMS INTELLIGENCE**

An intelligent enterprise IT platform for monitoring connected systems, managing integrations and
incidents, supporting GxP lifecycle workflows, and providing AI-assisted knowledge retrieval.

Syntra runs against a simulated pharmaceutical IT landscape (MES, LIMS, ERP) plus a live external
data feed (openFDA drug recalls), and is built the way a regulated system should be: role-based access, a tamper-evident audit trail, and requirements traced
to automated tests.

**Status:** v0.2 · Operations Center and Integrations working (steps 1–3 of 6).

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

## Run it

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8080 and sign in. All demo users use the password `demo1234`:

| User | Role | Can |
|---|---|---|
| `it.ops` / `it.ops2` | IT Operations | acknowledge, resolve, inject faults, run integration syncs |
| `qa.lead` | QA | close GxP incidents, verify audit trail |
| `system.owner` | System owner | report incidents |
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
| `backend/app/models` | Systems, telemetry, incidents, users, audit events, recalls, ingestion jobs, rejected records |
| `backend/app/services` | `health_monitor`, `incident_manager`, `audit_logger`, `data_validator`, `fda_pipeline` |
| `backend/app/integrations` | openFDA client and the synthetic sample fixtures |
| `backend/app/simulators` | MES, LIMS and ERP heartbeat simulators |
| `backend/app/worker` | Scheduled monitoring cycle |
| `backend/tests` | 55 tests: monitoring, workflow rules, permissions, audit integrity, validation rules, sync pipeline, openFDA client |
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
| 4 | GxP Lifecycle: system inventory, change requests, periodic review | Next |
| 5 | Knowledge Assistant: RAG over runbooks and regulatory documents | |
| 6 | Demo scenario script, end-to-end test, risk assessment, test protocol, Alembic migrations | |

## Disclaimer

Portfolio project. Systems, batches and users are simulated. Not a validated system.
