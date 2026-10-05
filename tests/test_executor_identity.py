from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from sentinelops.config import Settings
from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import RemediationAction
from sentinelops.providers.gcp.cloud_run import (
    CloudRunDeploymentProvider,
    CloudRunRemediationProvider,
)


async def test_mutation_uses_executor_not_read_identity() -> None:
    read = CloudRunDeploymentProvider("test-project", "us-central1", MagicMock(), MagicMock())
    executor = CloudRunRemediationProvider(read, "executor@test-project.iam.gserviceaccount.com")
    privileged = MagicMock(rollback=AsyncMock(return_value={"revision": "api-v1"}))
    action = RemediationAction(capability="rollback_demo_revision", service_id="orders-api", parameters={"revision":"api-v1", "expected_revision":"api-v2"})
    with patch.object(executor, "privileged_deployments", return_value=privileged) as factory:
        await executor.execute(action)
        privileged.rollback.assert_awaited_once_with(action)
        read.services_sdk.update_service.assert_not_called()
        with pytest.raises(ConflictError):
            await executor.execute(action.model_copy(update={"service_id": "incident-api"}))
        assert factory.call_count == 1


def test_production_requires_separate_executor() -> None:
    with pytest.raises(ValidationError, match="separate executor"):
        Settings(app_env="production", demo_mode=False, operator_token="x"*32, database_url="postgresql+asyncpg://", remediation_provider="gcp", _env_file=None)
