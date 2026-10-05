import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field

from sentinelops.config import Settings, get_settings
from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import Incident, Model, State
from sentinelops.runtime import Runtime
from sentinelops.security.request_limits import RequestSizeLimit
from sentinelops.simulation import scenarios


class ApprovalRequest(Model):
    plan_id: str = Field(min_length=1, max_length=64)
    actor: str = Field(default="local-operator", min_length=1, max_length=120)


class DemoRequest(Model):
    scenario: str = "bad-deployment"
    restart: bool = False


class SpeedRequest(Model):
    speed: float = Field(ge=.25, le=10)


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or get_settings()
    runtime = Runtime(configuration)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await runtime.initialize()
        yield
        await runtime.close()

    app = FastAPI(title="SentinelOps AI", version="0.1.0", lifespan=lifespan)
    app.state.runtime = runtime
    app.add_middleware(RequestSizeLimit)
    app.add_middleware(CORSMiddleware, allow_origins=configuration.cors_origins, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"], allow_credentials=False)

    @app.middleware("http")
    async def boundary(request: Request, call_next: Any) -> Any:
        from fastapi.responses import JSONResponse
        if request.url.path.startswith("/api/") and configuration.operator_token:
            supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
            if not secrets.compare_digest(supplied,configuration.operator_token):
                return JSONResponse(status_code=401,content={"detail":"Operator authentication required"})
        length = request.headers.get("Content-Length")
        if length and (not length.isdigit() or int(length) > 1000000):
            return JSONResponse(status_code=413,content={"detail":"Request exceeds allowed size"})
        return await call_next(request)

    @app.exception_handler(Exception)
    async def internal_error(request: Request, error: Exception) -> Any:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500,content={"detail":"Operation failed safely; inspect incident audit and service configuration"})

    async def operator(request: Request) -> str:
        if configuration.operator_token:
            supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
            if not secrets.compare_digest(supplied, configuration.operator_token):
                raise HTTPException(status_code=401, detail="Operator authentication required")
            return "authenticated-operator"
        if configuration.app_env == "production":
            raise HTTPException(status_code=401, detail="Operator authentication required")
        return "local-operator"

    async def require(incident_id: str) -> Incident:
        try:
            return await runtime.workflow.require(incident_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Incident not found") from error

    @app.exception_handler(ConflictError)
    async def conflict(request: Request, error: ConflictError) -> Any:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"detail":str(error)})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status":"healthy", "mode":configuration.app_env}

    @app.get("/api/v1/events")
    async def events(request: Request) -> Any:
        from fastapi.responses import StreamingResponse

        from sentinelops.streaming import stream_events
        return StreamingResponse(stream_events(runtime, request), media_type="text/event-stream", headers={"Cache-Control":"no-cache, no-transform", "X-Accel-Buffering":"no"})

    @app.get("/api/v1/incidents/{incident_id}/stream")
    async def incident_stream(incident_id: str, request: Request) -> Any:
        from fastapi.responses import StreamingResponse

        from sentinelops.streaming import stream_events
        await require(incident_id)
        return StreamingResponse(stream_events(runtime, request, incident_id), media_type="text/event-stream", headers={"Cache-Control":"no-cache, no-transform", "X-Accel-Buffering":"no"})

    @app.get("/api/v1/incidents", response_model=list[Incident])
    async def incidents(limit: Annotated[int, Query(ge=1, le=1000)] = 100, offset: Annotated[int, Query(ge=0)] = 0) -> list[Incident]:
        return await runtime.repository.list_incidents(limit, offset)

    @app.get("/api/v1/incidents/{incident_id}", response_model=Incident)
    async def detail(incident_id: str) -> Incident:
        return await require(incident_id)

    for field in ("timeline", "evidence", "hypotheses", "remediation", "historical_matches", "verification", "postmortem"):
        def route(selected: str) -> Any:
            async def handler(incident_id: str) -> Any:
                incident = await require(incident_id)
                value = getattr(incident, selected)
                return sorted(value, key=lambda e: e.timestamp) if selected == "timeline" else value
            handler.__name__ = "get_" + selected
            return handler
        app.add_api_route(f"/api/v1/incidents/{{incident_id}}/{field.replace('_', '-')}", route(field), methods=["GET"])

    @app.post("/api/v1/incidents/{incident_id}/investigate", status_code=202)
    async def investigate(incident_id: str, actor: str = Depends(operator)) -> dict[str, str]:
        incident = await require(incident_id)
        if incident.state not in {State.DETECTED, State.FAILED}:
            raise ConflictError("Incident has already been investigated")
        runtime.launch_investigation(incident_id)
        return {"status":"accepted", "incident_id":incident_id}

    @app.post("/api/v1/incidents/{incident_id}/approve-remediation", response_model=Incident)
    async def approval(incident_id: str, body: ApprovalRequest, actor: str = Depends(operator)) -> Incident:
        await require(incident_id)
        return await runtime.workflow.approve(incident_id, body.plan_id, actor if configuration.operator_token else body.actor)

    @app.post("/api/v1/incidents/{incident_id}/execute-remediation", response_model=Incident)
    async def execution(incident_id: str, actor: str = Depends(operator)) -> Incident:
        await require(incident_id)
        async with runtime.control_lock:
            incident = await runtime.workflow.execute(incident_id, actor)
            if configuration.demo_mode:
                runtime.simulation.recover()
            await runtime.repository.set_runtime("telemetry", runtime.telemetry.snapshot())
            return incident

    @app.get("/api/v1/services")
    async def services() -> Any:
        return [await runtime.workflow.tools.deployments.get_service_health("orders-api")]

    from sentinelops.ingestion import TelemetryBatch, ingest

    @app.post("/api/v1/telemetry", status_code=202)
    async def telemetry_ingestion(body: TelemetryBatch, actor: str = Depends(operator)) -> Any:
        return await ingest(runtime, body)

    @app.get("/api/v1/services/{service_id}/metrics")
    async def metrics(service_id: str, limit: Annotated[int, Query(ge=1, le=600)] = 120) -> Any:
        if service_id != "orders-api":
            raise HTTPException(status_code=404, detail="Service not found")
        return await runtime.workflow.tools.metrics.get_metric_series(service_id, limit)

    @app.get("/api/v1/deployments")
    async def deployments() -> Any:
        return await runtime.workflow.tools.deployments.get_recent_deployments("orders-api")

    @app.get("/api/v1/audit")
    async def audit(actor: str = Depends(operator)) -> Any:
        return await runtime.repository.audit()

    @app.get("/api/v1/system/status")
    async def status() -> dict[str, Any]:
        return {"status":"healthy" if runtime.last_error is None else "degraded", "mode":configuration.app_env, "demo_mode":configuration.demo_mode, "providers":{"logs":configuration.log_provider, "metrics":configuration.metrics_provider, "deployments":configuration.deployment_provider, "vectors":configuration.vector_provider, "llm":configuration.llm_provider, "remediation":configuration.remediation_provider}, "demo":runtime.demo_status(), "subscribers":len(runtime.bus.subscribers), "cloud_verified":False}

    @app.get("/api/v1/demo/scenarios")
    async def scenario_catalog() -> Any:
        return [{"name":s.name, "title":s.title} for s in scenarios().values()]

    @app.post("/api/v1/demo/start")
    async def demo_start(body: DemoRequest, actor: str = Depends(operator)) -> Any:
        if not configuration.demo_mode:
            raise HTTPException(status_code=403, detail="Demo controls disabled")
        if body.scenario not in scenarios():
            raise HTTPException(status_code=422, detail="Unknown scenario")
        return await runtime.start_demo(body.scenario, body.restart)

    @app.post("/api/v1/demo/pause")
    async def pause(actor: str = Depends(operator)) -> Any:
        if not configuration.demo_mode:
            raise HTTPException(status_code=403, detail="Demo controls disabled")
        runtime.simulation.paused = not runtime.simulation.paused
        return runtime.demo_status()

    @app.post("/api/v1/demo/speed")
    async def speed(body: SpeedRequest, actor: str = Depends(operator)) -> Any:
        if not configuration.demo_mode:
            raise HTTPException(status_code=403, detail="Demo controls disabled")
        runtime.simulation.speed = body.speed
        return runtime.demo_status()

    return app


app = create_app()
