from unittest.mock import MagicMock

import pytest

from sentinelops.domain.models import HistoricalIncident
from sentinelops.providers.gcp.vectors import BigQueryVectorProvider, embedding


async def test_vector_search_uses_parameters_and_real_distance() -> None:
    sdk = MagicMock()
    sdk.query.return_value.result.return_value = [{"id":"INC-007","title":"Database regression","signature":"pool timeout","cause":"bad_deployment","remediation":"rollback","outcome":"resolved","distance":.1}]
    provider = BigQueryVectorProvider("test-project","sentinelops",sdk, lambda values,limit:{"values":values,"limit":limit})
    matches = await provider.search("pool timeout")
    assert matches[0].similarity == .9
    assert "@embedding" in sdk.query.call_args.args[0]
    assert "embedding_version = 'hash128-v1'" in sdk.query.call_args.args[0]
    assert "pool timeout" not in sdk.query.call_args.args[0]
    assert len(embedding("pool timeout")) == 128
    assert embedding("pool timeout") == embedding("pool timeout")


async def test_seed_upserts_parameterized_rows_with_version_metadata() -> None:
    sdk = MagicMock()
    provider = BigQueryVectorProvider("test-project", "sentinelops", sdk)
    incident = HistoricalIncident(id="INC-1", title="pool", signature="timeouts", cause="bad_deployment", remediation="rollback")
    await provider.seed([incident])
    sql = sdk.query.call_args.args[0]
    assert "MERGE" in sql and "target.id=source.id" in sql
    assert "hash-lexical" in sql and "embedding_dimensions" in sql
    assert "INC-1" not in sql
    assert sdk.query.call_args.kwargs["job_config"].query_parameters[0].name == "rows"
    with pytest.raises(ValueError):
        await provider.seed([incident, incident])
