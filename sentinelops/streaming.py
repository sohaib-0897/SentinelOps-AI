import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import Request

from sentinelops.runtime import Runtime


async def stream_events(runtime: Runtime, request: Request, incident_id: str | None = None, heartbeat: float = 15) -> AsyncIterator[str]:
    async with runtime.bus.subscribe() as queue:
        yield "event: connected\ndata: " + json.dumps({"type":"resync", "reason":"Fetch current persisted state on every connection"}) + "\n\n"
        while not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat)
                if incident_id and event.get("incident_id") not in {incident_id, None}:
                    continue
                yield f"id: {event['sequence']}\nevent: update\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"
            except TimeoutError:
                yield ": heartbeat\n\n"
