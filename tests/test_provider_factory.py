import pytest

from sentinelops.config import Settings
from sentinelops.providers.events import LocalEventBus
from sentinelops.providers.factory import build_providers
from sentinelops.providers.gcp.common import CloudConfigurationError
from sentinelops.providers.local import LocalTelemetryProvider


def test_local_factory_needs_no_cloud_imports_or_credentials() -> None:
    telemetry, bus = LocalTelemetryProvider(), LocalEventBus()
    providers = build_providers(Settings(_env_file=None),telemetry,bus)
    assert providers.metrics is telemetry
    assert providers.events is bus


def test_cloud_configuration_is_not_silently_ignored() -> None:
    with pytest.raises(CloudConfigurationError):
        build_providers(Settings(log_provider="gcp",gcp_project_id="",_env_file=None),LocalTelemetryProvider(),LocalEventBus())
