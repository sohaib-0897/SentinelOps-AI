import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from pydantic import Field

from sentinelops.domain.models import Model, identifier, now


class DomainEvent(Model):
    id: str = Field(default_factory=identifier)
    type: str
    incident_id: str | None = None
    timestamp: datetime = Field(default_factory=now)
    data: dict[str, Any] = Field(default_factory=dict)


class LocalEventBus:
    """Bounded fan-out. Slow clients receive a resync signal instead of unlimited memory."""

    def __init__(self, capacity: int = 256) -> None:
        self.capacity = capacity
        self.subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self.sequence = 0

    async def publish(self, event: dict[str, Any]) -> None:
        self.sequence += 1
        envelope = {**event, "sequence": self.sequence}
        for queue in tuple(self.subscribers):
            if queue.full():
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait({"type": "resync", "sequence": self.sequence})
            else:
                queue.put_nowait(envelope)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(self.capacity)
        self.subscribers.add(queue)
        try:
            yield queue
        finally:
            self.subscribers.discard(queue)
