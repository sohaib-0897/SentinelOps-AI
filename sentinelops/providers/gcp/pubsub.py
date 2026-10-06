import importlib
import json
from typing import Any

from sentinelops.providers.events import DomainEvent, LocalEventBus
from sentinelops.providers.gcp.common import client, cloud_call, require_project


class GCPPubSubEventBus:
    def __init__(self, project: str, topic: str, sdk: Any = None) -> None:
        require_project(project)
        self.topic = f"projects/{project}/topics/{topic}"
        if sdk is not None:
            self.sdk = sdk
        else:
            types = importlib.import_module("google.cloud.pubsub_v1.types")
            self.sdk = client("google.cloud.pubsub_v1", "PublisherClient", publisher_options=types.PublisherOptions(enable_message_ordering=True))

    async def publish(self, event: dict[str, Any]) -> None:
        validated = DomainEvent.model_validate(event)
        payload = validated.model_dump_json().encode()
        if len(payload) > 9000000:
            raise ValueError("Event exceeds safe Pub/Sub payload size")
        ordering_key = validated.incident_id or "system"
        future = self.sdk.publish(self.topic, payload, ordering_key=ordering_key, event_id=validated.id, event_type=validated.type)
        try:
            await cloud_call(lambda: future.result(timeout=30))
        except Exception:
            # Ordered publishing pauses a key after failure; the durable outbox must be able to retry it.
            self.sdk.resume_publish(self.topic, ordering_key)
            raise


class MirroredEventBus:
    def __init__(self, local: LocalEventBus, cloud: GCPPubSubEventBus) -> None:
        self.local, self.cloud = local, cloud

    async def publish(self, event: dict[str, Any]) -> None:
        await self.local.publish(event)
        await self.cloud.publish(event)


def decode_push(body: dict[str, Any]) -> DomainEvent:
    import base64
    try:
        message = body["message"]
        payload = base64.b64decode(message["data"], validate=True)
        if len(payload) > 9000000:
            raise ValueError("Event too large")
        return DomainEvent.model_validate(json.loads(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Malformed Pub/Sub event envelope") from error
