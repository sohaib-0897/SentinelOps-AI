import time
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sentinelops.api import create_app
from sentinelops.config import Settings
from sentinelops.domain.models import now
from sentinelops.ingestion import TelemetryBatch
from sentinelops.simulation import materialize
from sentinelops.worker import collect


async def test_collect_scoped_observations() -> None:
    provider = materialize("bad-deployment")
    batch = await collect(provider,provider,provider)
    assert batch.metrics and batch.logs and batch.deployments
    with pytest.raises(ValidationError):
        TelemetryBatch(metrics=[batch.metrics[0].model_copy(update={"service_id":"other"})])


def test_ingestion_detects_once_and_rejects_invalid_scope(tmp_path: Path) -> None:
    settings = Settings(app_env="test",demo_mode=False,database_url=f"sqlite+aiosqlite:///{tmp_path/'ingestion.db'}",_env_file=None)
    provider = materialize("bad-deployment")
    start = now()+timedelta(seconds=1)
    metrics = [point.model_copy(update={"timestamp":start+timedelta(seconds=i)}) for i,point in enumerate(provider.metrics)]
    batch = TelemetryBatch(metrics=metrics,logs=provider.logs,deployments=provider.deployments,service=provider.service).model_dump(mode="json")
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/telemetry",json={"service_id":"other"}).status_code == 422
        response = client.post("/api/v1/telemetry",json=batch)
        assert response.status_code == 202 and response.json()["incident_id"]
        assert client.post("/api/v1/telemetry",json=batch).json()["accepted_metrics"] == 0
        for _ in range(100):
            incidents = client.get("/api/v1/incidents").json()
            if incidents[0]["state"] == "AWAITING_APPROVAL":
                break
            time.sleep(.02)
        assert len(incidents) == 1 and incidents[0]["state"] == "AWAITING_APPROVAL"
        assert incidents[0]["approvals"] == []
