# Telemetry worker

The deployable worker is `python -m sentinelops.worker --once`. Run it as a scheduled Cloud Run job every minute; it reads Logging, Monitoring and Cloud Run, then submits a bounded batch to the authenticated incident API. Omit `--once` for a supervised polling process. No remediation is executed by this worker. Configure `API_BASE_URL`, `API_AUTH_AUDIENCE`, `OPERATOR_TOKEN`, `GCP_PROJECT_ID`, and `GCP_REGION` through service identity and Secret Manager.

Local simulation supplies the same domain observations without requiring this cloud process. Tests exercise collection and ingestion using local providers.
