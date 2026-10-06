from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from sentinelops.domain.models import now
from sentinelops.providers.gcp.common import CloudConfigurationError
from sentinelops.providers.gcp.logging import GCPLoggingProvider


async def test_logging_uses_scoped_escaped_query_and_redacts_payload() -> None:
    sdk = MagicMock()
    sdk.list_entries.return_value = [SimpleNamespace(timestamp=now(), severity="ERROR", payload={"message":"password=example-private-value PostgreSQL timeout"}, resource=SimpleNamespace(labels={"revision_name":"api-v2"}))]
    provider = GCPLoggingProvider("test-project", sdk)
    entries = await provider.search_logs("orders-api", 'a" OR severity>=INFO', 10)
    call = sdk.list_entries.call_args.kwargs
    assert call["resource_names"] == ["projects/test-project"]
    assert 'a\\" OR' in call["filter_"]
    assert "example-private" not in entries[0].message
    assert entries[0].revision == "api-v2"


def test_missing_project_has_helpful_error() -> None:
    with pytest.raises(CloudConfigurationError, match="GCP_PROJECT_ID"):
        GCPLoggingProvider("")
