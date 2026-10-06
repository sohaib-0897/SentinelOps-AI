import json
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock, MagicMock

import pytest

from sentinelops.providers.gcp.adk import ADKExplanationProvider, build_runner
from sentinelops.providers.gcp.common import CloudConfigurationError


def provider(output: str):
    runner, sessions = MagicMock(), MagicMock()
    sessions.create_session = AsyncMock()
    sessions.delete_session = AsyncMock()
    runner.close = AsyncMock()

    async def events(**kwargs):
        yield Obj(is_final_response=lambda: True, content=Obj(parts=[Obj(text=output)]))

    runner.run_async = events
    return ADKExplanationProvider("test-project", "us-central1", "test-model", lambda *args: (runner, sessions)), runner, sessions


async def test_explanation_is_advisory_and_session_is_deleted() -> None:
    adapter, runner, sessions = provider(json.dumps({"explanation": "E1 corroborates timeout"}))
    assert await adapter.explain([{"id": "E1", "source": "logs", "summary": "Timeout", "timestamp": "2026-10-05", "data": {"secret": "omitted"}}]) == "E1 corroborates timeout"
    sessions.delete_session.assert_awaited_once()
    runner.close.assert_awaited_once()


@pytest.mark.parametrize("output", ['{"explanation":"ok","execute":"rollback"}', "not-json", '{"explanation":""}'])
async def test_invalid_or_action_output_fails_closed(output: str) -> None:
    adapter, runner, sessions = provider(output)
    with pytest.raises(CloudConfigurationError):
        await adapter.explain([])
    sessions.delete_session.assert_awaited_once()
    runner.close.assert_awaited_once()


async def test_real_adk_runner_has_no_privileged_capabilities() -> None:
    runner, sessions = build_runner("test-project", "us-central1", "gemini-2.5-flash")
    assert runner.agent.tools == [] and runner.agent.sub_agents == []
    assert runner.agent.code_executor is None
    assert runner.agent.output_schema.model_config["extra"] == "forbid"
    await runner.close()
