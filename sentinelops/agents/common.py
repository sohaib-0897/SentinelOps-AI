from dataclasses import dataclass
from typing import Protocol

from sentinelops.domain.models import Incident, IncidentEvent
from sentinelops.providers.contracts import LLMProvider
from sentinelops.tools.operations import AgentTools


@dataclass
class AgentContext:
    incident: Incident
    tools: AgentTools
    llm: LLMProvider

    def activity(self, actor: str, message: str) -> None:
        self.incident.timeline.append(IncidentEvent(kind="agent", actor=actor, message=message))


class Agent(Protocol):
    async def run(self, context: AgentContext) -> None: ...
