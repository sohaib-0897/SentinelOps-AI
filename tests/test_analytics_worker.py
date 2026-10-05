from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from sentinelops.analytics_worker import AnalyticsConsumer
from sentinelops.providers.events import DomainEvent


async def test_ack_only_after_success_and_preserve_event_id() -> None:
    event = DomainEvent(type="IncidentResolved",incident_id="incident-1")
    sdk = MagicMock()
    sdk.pull.return_value.received_messages = [SimpleNamespace(ack_id="success",message=SimpleNamespace(data=event.model_dump_json().encode())),SimpleNamespace(ack_id="invalid",message=SimpleNamespace(data=b"not-json"))]
    analytics = MagicMock(record_event=AsyncMock())
    consumer = AnalyticsConsumer("test-project","analytics",analytics,sdk)
    assert await consumer.drain_once() == {"accepted":1,"retry_pending":1}
    assert analytics.record_event.call_args.args[0]["id"] == event.id
    assert sdk.acknowledge.call_args.kwargs["request"]["ack_ids"] == ["success"]
    analytics.record_event.side_effect = RuntimeError("BigQuery unavailable")
    sdk.reset_mock()
    assert (await consumer.drain_once())["retry_pending"] == 2
    sdk.acknowledge.assert_not_called()
    with pytest.raises(ValueError):
        await consumer.drain_once(1000)
