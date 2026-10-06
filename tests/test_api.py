import time
from pathlib import Path

from fastapi.testclient import TestClient

from sentinelops.api import create_app
from sentinelops.config import Settings


def settings(tmp_path: Path, **kwargs) -> Settings:
    return Settings(app_env="test", database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}", _env_file=None, **kwargs)


def test_api_complete_demo(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/incidents/missing").status_code == 404
        assert client.post("/api/v1/demo/start", json={"scenario":"bad-deployment"}).status_code == 200
        client.post("/api/v1/demo/speed", json={"speed":10})
        incident = None
        for _ in range(100):
            data = client.get("/api/v1/incidents").json()
            if data and data[0]["state"] == "AWAITING_APPROVAL":
                incident = data[0]
                break
            time.sleep(.1)
        assert incident
        path = f"/api/v1/incidents/{incident['id']}"
        assert client.get(path+"/evidence").json()
        assert client.post(path+"/execute-remediation").status_code == 409
        assert client.post(path+"/approve-remediation", json={"plan_id":incident["remediation"]["id"], "actor":"test-sre"}).status_code == 200
        result = client.post(path+"/execute-remediation")
        assert result.status_code == 200
        assert result.json()["state"] == "RESOLVED"
        assert result.json()["postmortem"]["prevention"]
        assert client.post(path+"/execute-remediation").status_code == 409
        assert len(client.get("/api/v1/audit").json()) == 4


def test_authentication_and_input_validation(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path, operator_token="x"*32))) as client:
        assert client.get("/api/v1/incidents").status_code == 401
        assert client.get("/api/v1/events").status_code == 401
        assert client.post("/api/v1/demo/start", json={}).status_code == 401
        headers = {"Authorization":"Bearer " + "x"*32}
        assert client.post("/api/v1/demo/start", json={"scenario":"invalid"}, headers=headers).status_code == 422
        assert client.get("/api/v1/incidents?limit=10000", headers=headers).status_code == 422
        assert client.post("/api/v1/demo/start", content="{}", headers={**headers, "Content-Length":"1000001"}).status_code == 413
        assert client.post("/api/v1/demo/speed", json={"speed":100}, headers=headers).status_code == 422
