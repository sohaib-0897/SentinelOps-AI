FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.9.21 && useradd --system --uid 10001 sentinelops && mkdir /data && chown sentinelops /data
COPY pyproject.toml uv.lock ./
COPY sentinelops ./sentinelops
RUN uv sync --frozen --no-dev --extra gcp
COPY migrations ./migrations
COPY alembic.ini ./
COPY fixtures ./fixtures
COPY evals/scenarios ./evals/scenarios
COPY runbooks ./runbooks
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8000
USER sentinelops
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn sentinelops.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
