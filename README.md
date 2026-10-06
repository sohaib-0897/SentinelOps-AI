# SentinelOps AI

Evidence-driven incident investigation with human-approved remediation. SentinelOps detects sustained degradation, gathers source evidence, ranks supported causes, retrieves historical incidents, proposes an exact action, and verifies recovery before generating a postmortem.

The FastAPI control plane uses Python 3.12, Pydantic v2, SQLAlchemy/Alembic and a transactional outbox. The Next.js dashboard shows live incidents, services, metrics, deployments, postmortems and system status. Local operation needs no cloud account.

| Verification category | Scope |
|---|---|
| Verified locally | Backend, strict typing/lint, dashboard tests/build, non-root containers, complete browser approval/rollback/recovery flow and responsive views |
| Mock-tested GCP adapters | Logging, Monitoring, Run, Pub/Sub, BigQuery analytics/vector history, Secret Manager, IAM Cloud SQL connector, Vertex and advisory ADK |
| Synthetic evaluation | Twelve fixture scenarios; evidence rules and expected outcomes share the regression fixtures. This is not a held-out operational benchmark. |
| Real GCP | Not yet deployed or verified. IAM enforcement, live SQL/BigQuery, model access, scheduling and cloud recovery remain pending. |

Current evidence is retained in the [local completion report](docs/verification/local-complete.md), [browser observations](docs/verification/local-e2e.json), [evaluation](evals/results/latest.json), [development log](docs/DEVELOPMENT_LOG.md) and GitHub Actions. A mock test or Terraform validation does not establish a working cloud deployment.

The [interface redesign guide](docs/UI_REDESIGN.md) covers the landing page, operational workspace, charts, keyboard controls, screenshots, and verification.

Install Python 3.12, Node.js 22 and uv. From this checkout:

```powershell
uv sync --frozen --extra gcp
Set-Location apps/dashboard
npm ci
npm run build
Set-Location ../..
uv run python scripts/run_local.py --production
```

Open `http://127.0.0.1:3000` and enter the workspace at `/overview`. Select **Start Demo**, open the incident, and choose **Review remediation**. Inspect the exact rollback plan, acknowledge its scope, then select **Approve & execute**. The launcher connects a real bounded demo HTTP service; investigation metrics remain deterministic synthetic observations. It preserves previous incidents and coordinates process shutdown.

Alternatively:

```powershell
docker compose build
docker compose up -d --wait
```

The API is on port 8000, demo service on 8001, and dashboard on 3000. Compose binds IPv4 loopback only. See [local development](docs/local-development.md) for port overrides and all verification commands.

Cloud infrastructure is defined under [infra/terraform](infra/terraform). It includes private Cloud Run services, bounded worker jobs, scheduled triggers, Artifact Registry, Pub/Sub with retry/dead-letter handling, BigQuery schemas and canonical analytics, IAM-authenticated PostgreSQL, secret placeholders, monitoring and optional GitHub federation. Cloud scripts refuse mutations without an explicit execution switch. No real project or secret value is committed.

The domain workflow controls diagnosis and privileged actions. ADK/Gemini only explain bounded redacted evidence; they receive no privileged tools or agent credentials. Approval binds incident, plan digest, action IDs, risk and expiry. The executor validates allow-listed revisions and serving-revision preconditions. Evidence scores are deterministic heuristics, not calibrated AI confidence. Cloud execution supports traffic rollback; local capacity/restart simulations are rejected by the GCP executor.

Read [architecture](docs/architecture.md), [agents](docs/agents.md), [incident model](docs/incident-model.md), [security](docs/security.md), [evaluation](docs/evaluation.md), [demo guide](docs/demo-script.md), [GCP deployment](docs/gcp-deployment.md), and the [final setup checklist](docs/final-gcp-setup.md).
