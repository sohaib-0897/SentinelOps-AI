from unittest.mock import MagicMock

from sentinelops.providers.gcp.vectors import BigQueryVectorProvider, embedding


async def test_vector_search_uses_parameters_and_real_distance() -> None:
    sdk = MagicMock()
    sdk.query.return_value.result.return_value = [{"id":"INC-007","title":"Database regression","signature":"pool timeout","cause":"bad_deployment","remediation":"rollback","outcome":"resolved","distance":.1}]
    provider = BigQueryVectorProvider("test-project","sentinelops",sdk, lambda values,limit:{"values":values,"limit":limit})
    matches = await provider.search("pool timeout")
    assert matches[0].similarity == .9
    assert "@embedding" in sdk.query.call_args.args[0]
    assert "pool timeout" not in sdk.query.call_args.args[0]
    assert len(embedding("pool timeout")) == 128
    assert embedding("pool timeout") == embedding("pool timeout")
