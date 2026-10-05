from unittest.mock import MagicMock

import pytest

from sentinelops.providers.events import DomainEvent
from sentinelops.providers.gcp.bigquery import BigQueryAnalyticsProvider, table_name
from sentinelops.providers.gcp.common import CloudConfigurationError


async def test_bigquery_streams_stable_id_and_reports_rejection() -> None:
    sdk = MagicMock()
    sdk.insert_rows_json.return_value = []
    provider = BigQueryAnalyticsProvider("test-project","sentinelops",sdk)
    event = DomainEvent(type="IncidentResolved")
    await provider.record_event(event.model_dump(mode="json"))
    assert sdk.insert_rows_json.call_args.kwargs["row_ids"] == [event.id]
    sdk.insert_rows_json.return_value = [{"errors":["invalid"]}]
    with pytest.raises(CloudConfigurationError):
        await provider.record_event(event.model_dump(mode="json"))


def test_bigquery_identifiers_reject_sql_injection() -> None:
    with pytest.raises(ValueError):
        table_name("test-project","sentinelops`; DROP TABLE x", "incidents")
