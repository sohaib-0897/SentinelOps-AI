from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sentinelops.domain.models import Incident, IncidentEvent, event_time
from sentinelops.providers.contracts import LLMProvider
from sentinelops.tools.operations import AgentTools


@dataclass
class AgentContext:
    incident: Incident
    tools: AgentTools
    llm: LLMProvider

    def activity(self, actor: str, message: str, observed_at: datetime | None = None) -> None:
        timestamp = event_time(self.incident)
        self.incident.timeline.append(IncidentEvent(timestamp=max(timestamp,observed_at) if observed_at else timestamp,kind="agent", actor=actor, message=message))


class Agent(Protocol):
    async def run(self, context: AgentContext) -> None: ...
