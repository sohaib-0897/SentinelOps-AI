import asyncio
import json
import os
import secrets
import time
from collections import deque
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import Field

from sentinelops.config import get_settings
from sentinelops.domain.models import Model, now

FailureMode = Literal["none", "db_pool_exhaustion", "latency", "http_500", "dependency_timeout", "memory_pressure"]


class DemoControl(Model):
    failure_mode: FailureMode = "none"
    revision: str = Field(default="api-v1", pattern=r"^[a-z][a-z0-9-]{0,62}$")


class DemoState:
    def __init__(self) -> None:
        self.configuration = DemoControl.model_validate({"failure_mode":os.getenv("FAILURE_MODE", "none"), "revision":os.getenv("DEMO_REVISION", os.getenv("K_REVISION", "api-v1"))})
        self.requests = 0
        self.errors = 0
        self.logs: deque[dict[str, Any]] = deque(maxlen=128)
        self.latencies: deque[float] = deque(maxlen=128)


def create_demo_app() -> FastAPI:
    state = DemoState()
    app = FastAPI(title="SentinelOps Breakable Orders Service", version="0.1.0")
    app.state.demo = state

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status":"healthy" if state.configuration.failure_mode == "none" else "degraded", "revision":state.configuration.revision, "failure_mode":state.configuration.failure_mode, "bounded_simulation":True}

    async def request_work() -> None:
        start = time.monotonic()
        state.requests += 1
        mode = state.configuration.failure_mode
        messages = {"db_pool_exhaustion":"PostgreSQL pool exhaustion: connection acquisition timeout", "http_500":"Unhandled application exception: HTTP 500", "dependency_timeout":"Upstream payments dependency timeout", "memory_pressure":"Memory pressure: simulated utilization exceeded threshold"}
        if mode in {"latency", "dependency_timeout"}:
            await asyncio.sleep(.2)
        fail = mode in {"db_pool_exhaustion", "dependency_timeout", "memory_pressure"} or (mode == "http_500" and state.requests % 100 < 18)
        state.latencies.append((time.monotonic()-start)*1000)
        state.logs.append({"timestamp":now().isoformat(), "severity":"ERROR" if fail else "INFO", "message":messages.get(mode, "Request completed"), "revision":state.configuration.revision})
        # Cloud Logging reads structured stdout; these bounded messages contain no user data.
        print(json.dumps(state.logs[-1]), flush=True)
        if fail:
            state.errors += 1
            raise HTTPException(status_code=504 if mode == "dependency_timeout" else 500, detail=messages[mode])

    @app.get("/api/items")
    async def items() -> dict[str, Any]:
        await request_work()
        return {"items":[{"id":"SKU-101", "name":"Cloud runtime", "stock":42}], "revision":state.configuration.revision}

    @app.get("/api/orders")
    async def orders() -> dict[str, Any]:
        await request_work()
        return {"orders":[{"id":"ORD-1007", "status":"fulfilled", "items":2}], "revision":state.configuration.revision}

    @app.get("/telemetry")
    async def telemetry() -> dict[str, Any]:
        return {"requests":state.requests, "errors":state.errors, "error_rate":state.errors/max(state.requests, 1), "latencies_ms":list(state.latencies), "logs":list(state.logs), "configuration":state.configuration.model_dump()}

    @app.post("/control")
    async def control(body: DemoControl, request: Request) -> dict[str, Any]:
        settings = get_settings()
        if not settings.demo_mode:
            raise HTTPException(status_code=403, detail="Runtime failure injection disabled")
        if settings.operator_token and not secrets.compare_digest(request.headers.get("Authorization", "").removeprefix("Bearer "), settings.operator_token):
            raise HTTPException(status_code=401, detail="Operator authentication required")
        state.configuration = body
        state.logs.append({"timestamp":now().isoformat(), "severity":"INFO", "message":"Controlled demo configuration changed", "revision":body.revision})
        return body.model_dump()

    return app


app = create_demo_app()
