import pytest
from pydantic import ValidationError

from sentinelops.config import Settings


def test_local_needs_no_credentials() -> None:
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "deterministic"
    assert settings.gcp_project_id == ""


def test_production_fails_closed() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", _env_file=None)


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="explicit origins"):
        Settings(app_env="production", demo_mode=False, operator_token="x"*32, database_url="postgresql+asyncpg://", cors_origins=["*"], _env_file=None)
