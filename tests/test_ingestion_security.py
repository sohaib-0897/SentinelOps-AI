from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sentinelops.api import create_app
from sentinelops.config import Settings
from sentinelops.domain.models import now
from sentinelops.ingestion import TelemetryBatch
from sentinelops.simulation import materialize


async def test_chunked_body_cannot_bypass_size_limit(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", database_url=f"sqlite+aiosqlite:///{tmp_path/'body.db'}", _env_file=None))

    async def chunks():
        for _ in range(11):
            yield b"x" * 100000

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/telemetry", content=chunks())
    assert response.status_code == 413


def test_auth_scope_future_clock_and_scenario_boundaries(tmp_path: Path) -> None:
    provider = materialize("bad-deployment")
    with pytest.raises(ValidationError, match="future"):
        TelemetryBatch(metrics=[provider.metrics[0].model_copy(update={"timestamp": now()+timedelta(days=1)})])
    app = create_app(Settings(app_env="test", operator_token="operator", database_url=f"sqlite+aiosqlite:///{tmp_path/'auth.db'}", _env_file=None))
    with TestClient(app) as client:
        assert client.post("/api/v1/telemetry", json={}).status_code == 401
        headers = {"Authorization": "Bearer operator"}
        assert client.post("/api/v1/demo/start", json={"scenario": "bad-deployment"}, headers=headers).status_code == 200
        assert client.post("/api/v1/telemetry", json={}, headers=headers).status_code == 409
        assert app.state.runtime.simulation.step == 0
