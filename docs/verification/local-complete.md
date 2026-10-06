# Local completion verification

Measured on 2026-10-05 against implementation commit `331f7861480f9dd9094ce7736d6354aa4c4d8bb8`. The completion commit adds this record and regenerated browser artifacts; it does not change runtime code. No real GCP deployment was attempted.

| Check | Newly measured result |
|---|---|
| Backend | `uv run --extra gcp pytest -q`: **214 passed**, 20.36 seconds; one upstream AnyIO deprecation warning |
| Backend lint/types | Ruff across `sentinelops tests scripts` passed; strict mypy passed for 53 source files |
| Clean Python installation | Independent `.local/verification-clean-venv`, installed from `uv.lock` with the GCP extra: **214 passed**, 29.76 seconds |
| Frontend installation/security | Fresh `npm ci`; `npm audit`: **0 vulnerabilities** |
| Frontend code/build | ESLint, strict TypeScript, **6 tests** and Next.js production build passed |
| Evaluation | Regenerated [report](../../evals/results/latest.json): **12/12** fixture scenarios; root-cause accuracy/evidence recall/tool selection/remediation correctness 1.0; false-cause/unsafe-action rates 0.0 |
| Docker | Compose configuration, API/dashboard image builds and `up -d --wait` passed; API/demo healthy, dashboard responds; runtime API UID 10001, dashboard UID 1000 |
| Browser | Full bad-deployment → approved rollback → five fresh samples → resolved postmortem; historical evidence, chronological timeline, audit and resource views checked; no page errors; no overflow at 390/768/1440; two real SSE proxy reconnections |
| Terraform 1.13.5 | `fmt -check -recursive`, `init -backend=false -lockfile=readonly`, `validate` and **2 mocked plan tests** passed with Google provider 7.46.1 |
| Hosted Linux CI | All four jobs passed on the implementation commit: [run 37342977867](https://github.com/sohaib-0897/SentinelOps-AI/actions/runs/37342977867), including fresh dependency installs, Docker and real browser QA |
| Targeted security review | Tracked credential/env/state scan and execution/trust-boundary review completed; verified defects fixed with regressions; details in [security model](../security.md) |

The browser incident was `e0bfb161-6d6d-4f02-b0de-85f3959ea55f`; recovery samples completed at `2026-10-05T16:47:22.218660Z`. Error rate recovered from 18% to 0.2%, p95 latency from 1680ms to 85ms. All eight verification checks passed. See [raw browser observations](local-e2e.json) and [screenshots](../screenshots/incident-postmortem.png).

On this machine another application owns the default API port. SentinelOps was checked on API 18000, demo 18001 and dashboard 13000, using the documented Compose overrides. Existing unrelated processes, containers, images and volumes were preserved. The earlier internal missing-blob failure did not recur; no global cache cleanup was used. SentinelOps containers remain available for review and the incident volume is retained.

The evaluation is synthetic and shares fixtures with deterministic regression rules. The local demo's HTTP failure/recovery is real, while investigation telemetry is deterministic. Mocked providers and valid Terraform do not demonstrate live cloud operation. ADK construction was checked without network calls and model behavior was mocked.

Pending real integration checks include IAM/identity exchange, Cloud SQL PostgreSQL grants/migrations, Cloud Run target traffic rollback, Scheduler, Monitoring latency/alerts, Pub/Sub redelivery/dead letters, BigQuery views/MERGE/vector index and Vertex/ADK responses. The single-instance API scaling limit and minimum authorized cloud setup are documented in [architecture](../architecture.md) and [final GCP setup](../final-gcp-setup.md).
