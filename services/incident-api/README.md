# Incident API

Run from the monorepo root: `uv run uvicorn sentinelops.api:app --host 127.0.0.1 --port 8000`.
The reusable application and runtime live in `sentinelops/` so the worker, API and evaluation harness share business rules. Local startup applies Alembic migrations. Use one API worker with SQLite and the local event bus.
