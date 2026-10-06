# Incident and persistence model

An incident stores service, severity, lifecycle state, version, timestamps, symptoms, source evidence, ranked hypotheses, root cause, historical matches, plan, approvals, verification, postmortem and timeline. Pydantic models forbid unknown fields. Evidence records retain source timestamps and provider provenance.

Normal progression is `DETECTED → TRIAGING → INVESTIGATING → DIAGNOSED → AWAITING_APPROVAL → REMEDIATING → VERIFYING → RESOLVED`. The explicit lifecycle matrix rejects invalid transitions. Inconclusive investigations and incomplete/failed recovery enter `FAILED`; retries require review and invalidate the old plan/approvals. Resolution can subsequently be closed.

Approval is specific to the incident, plan ID, immutable plan digest, ordered action IDs, risk and expiry. Execution atomically changes durable state before calling the executor. A second request, stale version, replay, changed action or cross-incident approval cannot reuse authorization. Provider revision preconditions and Cloud Run etags defend against intervening deployment changes.

The repository keeps optimistic incident aggregates, structured audit, runtime telemetry and an event outbox in SQLite locally or PostgreSQL in cloud mode. Alembic migrations preserve existing history. The indexed `started_at` column orders incidents before database pagination. Historical deployment events may be appended during investigation; the timeline endpoint and UI sort their actual timestamps for display.

Recovery requires five new samples after the recorded pre-execution boundary, acceptable errors/latency/resources, new logs, service readiness and expected revision. Infrastructure readiness alone does not establish application recovery. A postmortem is generated only when verification passes, and its historical record is included in the durable resolution event.
