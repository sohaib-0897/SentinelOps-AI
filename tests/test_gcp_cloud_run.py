from types import SimpleNamespace as Obj
from unittest.mock import MagicMock

import pytest

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import RemediationAction
from sentinelops.providers.gcp.cloud_run import CloudRunDeploymentProvider, CloudRunRemediationProvider


def adapter():
    services, revisions = MagicMock(), MagicMock()
    services.get_service.return_value = Obj(name="orders-api", latest_ready_revision="api-v2", traffic_statuses=[Obj(revision="api-v2",percent=100)], reconciling=False, etag="v1", terminal_condition=Obj(state=4))
    revisions.get_revision.return_value = Obj(conditions=[Obj(state=4)])
    return CloudRunDeploymentProvider("test-project","us-central1",services,revisions), services


async def test_cloud_run_rollback_scopes_update_and_uses_etag() -> None:
    provider, sdk = adapter()
    action = RemediationAction(capability="rollback_demo_revision", service_id="orders-api", parameters={"revision":"api-v1","expected_revision":"api-v2"})
    result = await CloudRunRemediationProvider(provider).execute(action)
    request = sdk.update_service.call_args.kwargs["request"]
    assert request["update_mask"]["paths"] == ["traffic"]
    assert request["service"]["etag"] == "v1"
    assert result["simulated"] is False
    assert (await provider.get_service_health("orders-api")).revision == "api-v2"


async def test_cloud_run_rejects_cross_service_and_unsupported_actions() -> None:
    provider, _ = adapter()
    with pytest.raises(ConflictError):
        await provider.get_service_health("incident-api")
    with pytest.raises(ConflictError):
        await CloudRunRemediationProvider(provider).execute(RemediationAction(capability="restart_demo_service",service_id="orders-api"))
