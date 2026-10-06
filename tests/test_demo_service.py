import pytest
from fastapi.testclient import TestClient

from sentinelops.demo_service import create_demo_app


@pytest.mark.parametrize("mode", ["db_pool_exhaustion", "http_500", "dependency_timeout", "memory_pressure"])
def test_failure_and_recovery_are_bounded(mode: str) -> None:
    with TestClient(create_demo_app()) as client:
        assert client.get("/health").json()["status"] == "healthy"
        assert client.get("/api/items").status_code == 200
        assert client.post("/control", json={"failure_mode":mode, "revision":"api-v2"}).status_code == 200
        assert client.get("/api/orders").status_code in {500, 504}
        assert client.get("/telemetry").json()["errors"] == 1
        client.post("/control", json={"failure_mode":"none", "revision":"api-v1"})
        assert client.get("/api/orders").status_code == 200


def test_invalid_control_rejected() -> None:
    with TestClient(create_demo_app()) as client:
        assert client.post("/control", json={"failure_mode":"fork_bomb"}).status_code == 422
