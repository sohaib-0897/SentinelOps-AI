import pytest

from sentinelops.domain.lifecycle import TRANSITIONS, ConflictError, transition
from sentinelops.domain.models import Incident, State


@pytest.mark.parametrize("source", list(State))
@pytest.mark.parametrize("target", list(State))
def test_every_transition(source: State, target: State) -> None:
    incident = Incident(title="test", state=source)
    if target in TRANSITIONS[source]:
        transition(incident, target)
        assert incident.state == target
        assert incident.timeline[-1].data["to"] == target
    else:
        with pytest.raises(ConflictError):
            transition(incident, target)
        assert incident.state == source


def test_resolution_records_time() -> None:
    incident = Incident(title="test", state=State.VERIFYING)
    transition(incident, State.RESOLVED)
    assert incident.resolved_at is not None
