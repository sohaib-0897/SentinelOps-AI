from sentinelops.domain.models import Incident, IncidentEvent, State, event_time

TRANSITIONS: dict[State, frozenset[State]] = {
    State.DETECTED: frozenset({State.TRIAGING, State.CLOSED, State.FAILED}),
    State.TRIAGING: frozenset({State.INVESTIGATING, State.CLOSED, State.FAILED}),
    State.INVESTIGATING: frozenset({State.DIAGNOSED, State.FAILED}),
    State.DIAGNOSED: frozenset({State.AWAITING_APPROVAL, State.FAILED}),
    State.AWAITING_APPROVAL: frozenset({State.REMEDIATING, State.FAILED}),
    State.REMEDIATING: frozenset({State.VERIFYING, State.FAILED}),
    State.VERIFYING: frozenset({State.RESOLVED, State.FAILED}),
    State.RESOLVED: frozenset({State.CLOSED}),
    State.FAILED: frozenset({State.INVESTIGATING, State.CLOSED}),
    State.CLOSED: frozenset(),
}


class ConflictError(Exception):
    """A state, version, or approval no longer permits the requested action."""


def transition(incident: Incident, target: State, actor: str = "system") -> None:
    if target not in TRANSITIONS[incident.state]:
        raise ConflictError(f"Transition {incident.state} -> {target} is not allowed")
    previous = incident.state
    incident.state = target
    incident.updated_at = event_time(incident)
    if target == State.RESOLVED:
        incident.resolved_at = incident.updated_at
    incident.timeline.append(IncidentEvent(timestamp=incident.updated_at,kind="state", actor=actor, message=f"{previous} → {target}", data={"from": previous, "to": target}))
