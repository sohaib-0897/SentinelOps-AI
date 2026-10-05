# Demonstration guide

Start the native launcher or Compose as described in local development. Open the IPv4 dashboard URL. The overview shows a healthy Orders API and synthetic baseline metrics; the real demo HTTP service returns successful items/orders.

1. Select **Start Demo** for `bad-deployment`, then **Speed Up** if desired.
2. Observe the new revision, pool-exhaustion logs, elevated errors/latency and detected incident.
3. Open the incident. Explain triage, metric/log/revision evidence and deployment correlation. Show alternative hypotheses, contradictory resource evidence and historical match INC-007.
4. Review the exact previous/current revision parameters and expiry in **Remediation**. Execution without approval returns a conflict.
5. Select **Approve Remediation**. The UI records approval and executes that exact plan. The real local demo recovers, independently checked alongside five fresh synthetic samples.
6. Show **Postmortem**, chronological timeline, audit records and resolved state. Browse Services, Metrics, Deployments, Postmortems and System.

Use **Restart** only when intentionally retaining an interrupted run as failed. The service is deliberately bounded: latency sleeps and failure responses simulate degradation without exhausting machine resources. State that metrics/root-cause scores and the benchmark are synthetic; a live service response does not turn them into production telemetry.

`scripts/browser_qa.py` automates this sequence and retains screenshots/report. Cloud tests instead use real Cloud Logging/Monitoring and an explicitly authorized fault revision on the private demonstration target; runtime `/control` is disabled there. Never inject a bad revision into an existing production service for a presentation.
