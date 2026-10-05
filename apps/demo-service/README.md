# Deliberately breakable orders service

From the monorepo root: `uv run uvicorn sentinelops.demo_service:app --host 127.0.0.1 --port 8001`.
Endpoints: `/health`, `/api/items`, `/api/orders`, `/telemetry`, `/control`.
Failure modes are bounded simulations; memory pressure never allocates large buffers, and dependency/latency delays are capped at 200ms. Production disables runtime injection; separate Cloud Run revisions may specify `FAILURE_MODE` and `DEMO_REVISION` at deployment time.
