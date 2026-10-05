"""Run only after real cloud setup; writes the seven documented seed incidents."""
import asyncio
import json
from pathlib import Path

from sentinelops.config import Settings
from sentinelops.domain.models import HistoricalIncident
from sentinelops.providers.gcp.vectors import BigQueryVectorProvider


async def main() -> None:
    settings = Settings()
    fixtures = json.loads(Path("fixtures/historical-incidents.json").read_text(encoding="utf-8"))
    await BigQueryVectorProvider(settings.gcp_project_id,settings.bigquery_dataset).seed([HistoricalIncident.model_validate(item) for item in fixtures])
    print(f"Seeded {len(fixtures)} historical incident rows")


if __name__ == "__main__":
    asyncio.run(main())
