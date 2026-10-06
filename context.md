# SentinelOps AI — Project Context

## Repository state

- Repository: `https://github.com/sohaib-0897/SentinelOps-AI.git`
- Development branch: `codex/build-sentinelops`
- UI redesign implementation commit: `f2932ac`; verification and handoff are recorded in the following documentation commit.
- Local completion tag: `checkpoint/11-local-complete`; infrastructure tag: `checkpoint/10-infrastructure`.
- Pull request to `main`: https://github.com/sohaib-0897/SentinelOps-AI/pull/1 (open; do not merge without instruction).
- At handoff the tracked working tree was clean and all commits and checkpoint tags were pushed.

## Product

SentinelOps is an evidence-driven incident response system. It detects sustained service degradation, investigates using typed tools and historical incidents, ranks evidence-supported causes, requests approval for an exact remediation, verifies recovery, and creates a postmortem.

The stack is Python 3.12, FastAPI, Pydantic v2, SQLAlchemy/Alembic, SQLite locally, optional Cloud SQL PostgreSQL, and a Next.js dashboard. Local operation and deterministic tests need no GCP account.

## Key safeguards

- Deterministic domain workflow and evidence rules remain authoritative. Optional Vertex/ADK provides bounded, redacted advisory explanations; model output cannot execute actions.
- Remediation requires a structured plan, risk policy, exact incident/action approval, durable execution claim, allow-listed executor, and audit trail.
- Cloud telemetry uses a separate ingestion-only token and is limited to the validated ingestion endpoint. Production API routes and SSE are authenticated.
- Runtime identities are separated. The API lacks broad Cloud Run administration; cloud remediation uses short-lived scoped impersonation.
- Never commit credentials, `.env` files, Terraform state, or plan files. Do not use service-account JSON keys.

## Cloud implementation

`infra/terraform/` defines private Cloud Run services and workers, Artifact Registry, Pub/Sub with retry/dead-letter handling, BigQuery analytics/vector history, Cloud SQL, Secret Manager placeholders, service identities/IAM, Scheduler, Monitoring and optional GitHub federation.

PowerShell and POSIX entry points live under `scripts/gcp/`. Mutating cloud operations require explicit `--execute`; scripts reject destructive/replacement plans. No real GCP resources have been created or verified.

Live checks remain for IAM and identity exchange, Cloud SQL grants/migrations, Cloud Run remediation, Pub/Sub delivery, BigQuery queries/vector indexing, scheduled jobs, Monitoring, and Vertex/ADK responses. The API is currently designed for a single active instance.

## Local development

- Python: `uv sync --frozen --extra gcp`; run tests with `uv run --extra gcp pytest -q`.
- Quality: `uv run --extra gcp ruff check sentinelops tests scripts` and `uv run --extra gcp mypy sentinelops`.
- Dashboard: from `apps/dashboard`, run `npm ci`, then `npm run dev` or the documented lint/typecheck/test/build scripts.
- Compose: `docker compose config --quiet`, `docker compose build`, `docker compose up -d --wait`.
- Default ports are 8000 (API), 8001 (demo), and 3000 (dashboard). If occupied, set `API_PORT`, `DEMO_PORT`, and `DASHBOARD_PORT` before Compose.
- On the development machine, SentinelOps was left running at API `http://127.0.0.1:18000`, demo `http://127.0.0.1:18001`, dashboard `http://127.0.0.1:13000`.
- The landing page is `/`; the operational dashboard is `/overview`. The updated Docker dashboard is running at `http://127.0.0.1:13000`.
- **Start Demo** exercises a bad deployment. Open the incident, choose **Review remediation**, acknowledge the exact plan, then **Approve & execute** to run rollback, recovery checks, and postmortem generation.

## UI redesign handoff

- All principal frontend routes now use the graphite/lime design system. The landing page includes a real provider-data preview; charts show thresholds and observed revision transitions.
- Incident command includes lifecycle progress, evidence score visualization, source records, hypotheses, historical matches, exact-plan review drawer, verification, and postmortem export.
- Command navigation supports Ctrl/Cmd+K. Tabs and dialogs have keyboard controls; scrollable evidence/activity regions are focusable.
- No dependencies or backend/API contracts changed. See `docs/UI_REDESIGN.md`, `docs/verification/ui-redesign.md`, and `docs/screenshots/redesign/`.
- Verification on 2026-10-06: frontend lint/typecheck/6 tests, native and Docker production builds, 23 end-to-end checks, 8 UI state checks, 27 route/viewport combinations, and 18 axe checks with zero detected violations. Recovery was verified with five fresh samples; the audit log and two SSE reconnects were checked.

## Earlier local completion verification

- Backend: 214 tests passed in both active and clean lock-file-installed environments; Ruff and strict mypy passed.
- Frontend: six tests, lint, strict typecheck, production build passed; npm audit found zero vulnerabilities.
- Evaluation: 12 synthetic fixtures passed; these are regression fixtures, not a held-out operational benchmark.
- Docker/Compose and real browser workflow passed, including approval, five fresh recovery samples, audit/timeline, two SSE reconnections, and responsive widths 390/768/1440.
- Terraform 1.13.5 formatting, backend-disabled init, validation, and two mocked plan tests passed.
- Branch and PR CI passed all four jobs. See `docs/verification/local-complete.md`, `docs/verification/local-e2e.json`, and `evals/results/latest.json` for evidence.

## Working rules

- Inspect `git status`, diffs, and existing files before edits; preserve legitimate work and published history.
- Make small, related commits with conventional messages and push each commit to `codex/build-sentinelops`. Never amend, rebase, reset, squash, or force-push.
- Maintain `docs/DEVELOPMENT_LOG.md` using `scripts/milestone.py` for implementation milestones.
- Do not rebuild existing features unless a defect is demonstrated. Keep local/mock/synthetic verification distinct from live GCP claims.
- Do not provision GCP until the user provides a project, region, confirms billing, authenticates with gcloud/ADC, and explicitly authorizes reviewed provisioning and deployment.
