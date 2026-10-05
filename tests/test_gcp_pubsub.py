import base64
from unittest.mock import MagicMock

import pytest

from sentinelops.providers.events import DomainEvent
from sentinelops.providers.gcp.pubsub import GCPPubSubEventBus, decode_push


async def test_pubsub_preserves_event_identity_and_ordering() -> None:
    sdk = MagicMock()
    event = DomainEvent(type="IncidentDetected",incident_id="incident-1")
    await GCPPubSubEventBus("test-project","events",sdk).publish(event.model_dump(mode="json"))
    args = sdk.publish.call_args
    assert args.args[0] == "projects/test-project/topics/events"
    assert args.kwargs["ordering_key"] == "incident-1"
    assert args.kwargs["event_id"] == event.id
    pushed = {"message":{"data":base64.b64encode(args.args[1]).decode()}}
    assert decode_push(pushed).id == event.id


def test_malformed_push_is_rejected() -> None:
    with pytest.raises(ValueError):
        decode_push({"message":{"data":"invalid"}})
