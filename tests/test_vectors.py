from sentinelops.providers.vectors import LocalVectorProvider


async def test_retrieves_relevant_history() -> None:
    provider = LocalVectorProvider()
    matches = await provider.search("PostgreSQL pool exhaustion connection acquisition timeout bad deployment HTTP 500")
    assert matches[0].id == "INC-007"
    assert 0 < matches[0].similarity <= 1
    assert await provider.search("") == []
