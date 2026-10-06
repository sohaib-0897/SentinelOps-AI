from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from sentinelops.providers.gcp.common import CloudConfigurationError
from sentinelops.providers.gcp.vertex import GeminiVertexAIProvider


async def test_vertex_uses_structured_output_and_rejects_unsupported_fields() -> None:
    sdk = MagicMock()
    sdk.aio.models.generate_content = AsyncMock(return_value=SimpleNamespace(text='{"explanation":"Evidence e1 reports elevated errors."}'))
    provider = GeminiVertexAIProvider("test-project","us-central1","configured-model",sdk)
    facts = [{"id":"e1","source":"metrics","summary":"HTTP errors","timestamp":"2026-10-05T00:00:00Z", "data":{"private":"not-sent"}}]
    assert "e1" in await provider.explain(facts)
    args = sdk.aio.models.generate_content.call_args.kwargs
    assert "not-sent" not in args["contents"]
    assert args["config"]["temperature"] == 0
    sdk.aio.models.generate_content.return_value = SimpleNamespace(text='{"explanation":"x","cause":"invented"}')
    with pytest.raises(CloudConfigurationError):
        await provider.explain(facts)
