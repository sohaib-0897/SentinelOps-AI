# Evaluation

Run `uv run python -m sentinelops.evaluation.run` to regenerate `evals/results/latest.json`. Twelve scenarios cover healthy/transient behavior, bad deployment, database/cache/dependency/resource/application/configuration issues and abstention.

The report measures root-cause accuracy, annotated evidence-source recall, tool selection, remediation correctness, false diagnosis and execution without approval. It also exercises approved local recovery. Current measured results are in the report, with limitations embedded in that file. Full regression tests separately probe lifecycle transitions, replay/tampering/expiry, optimistic persistence, outbox retry, authenticated ingestion/SSE and mock provider behavior.

These fixtures are also regression inputs for the deterministic rules. Perfect scores demonstrate consistency with known cases, not generalization, calibrated confidence or real incident performance. Evidence recall counts source categories rather than all relevant facts; unsafe-action probes do not cover every cloud IAM threat. No GCP SDK operation or live model generation is used in this benchmark.

Browser QA adds a real HTTP demo service and production dashboard, exact-plan UI approval, rollback, five fresh verification samples, postmortem, all resource pages, widths 390/768/1440, audit and two real SSE proxy reconnections. Its observations are kept in `docs/verification/local-e2e.json`; screenshots show actual UI state. Cloud smoke checks are deliberately separate.
