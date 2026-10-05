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
