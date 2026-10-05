import hashlib
import importlib
import math
import re
from typing import Any

from sentinelops.domain.models import HistoricalIncident
from sentinelops.providers.gcp.bigquery import table_name
from sentinelops.providers.gcp.common import client, cloud_call


def embedding(text: str, dimensions: int = 128) -> list[float]:
    """Versioned hash embedding used by both ingestion and queries; not semantic Gemini embeddings."""
    values = [0.] * dimensions
    for token in re.findall(r"[a-z][a-z0-9_]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        values[int.from_bytes(digest[:4],"big") % dimensions] += 1 if digest[4] % 2 else -1
    norm = math.sqrt(sum(v*v for v in values))
    return [value/norm if norm else 0. for value in values]


class BigQueryVectorProvider:
    def __init__(self, project: str, dataset: str, sdk: Any = None, query_config_factory: Any = None) -> None:
        self.table = table_name(project,dataset,"historical_incidents")
        self.sdk = sdk if sdk is not None else client("google.cloud.bigquery","Client",project=project)
        self.query_config_factory = query_config_factory

    def query_config(self, query: str, limit: int) -> Any:
        if self.query_config_factory:
            return self.query_config_factory(embedding(query), limit)
        bq = importlib.import_module("google.cloud.bigquery")
        return bq.QueryJobConfig(query_parameters=[bq.ArrayQueryParameter("embedding","FLOAT64",embedding(query)), bq.ScalarQueryParameter("top_k","INT64",limit)], maximum_bytes_billed=1000000000)

    async def search(self, query: str, limit: int = 3) -> list[HistoricalIncident]:
        if not query.strip():
            return []
        if not 1 <= limit <= 10:
            raise ValueError("Vector search limit must be 1–10")
        # Identifiers are validated by table_name; every query value is bound as a parameter.
        sql = f"SELECT base.*, distance FROM VECTOR_SEARCH(TABLE `{self.table}`, 'embedding', (SELECT @embedding AS embedding), top_k => @top_k, distance_type => 'COSINE') ORDER BY distance"  # noqa: S608
        config = self.query_config(query,limit)
        job = await cloud_call(lambda:self.sdk.query(sql,job_config=config))
        rows = await cloud_call(lambda:list(job.result(timeout=30)))
        return [HistoricalIncident(id=row["id"], title=row["title"], signature=row["signature"], cause=row["cause"], remediation=row["remediation"], outcome=row["outcome"], similarity=max(0., min(1., 1-float(row["distance"])))) for row in rows]

    async def seed(self, incidents: list[HistoricalIncident]) -> None:
        rows = [{**incident.model_dump(exclude={"similarity"}), "embedding":embedding(incident.signature+" "+incident.title), "embedding_version":"hash128-v1"} for incident in incidents]
        errors = await cloud_call(lambda:self.sdk.insert_rows_json(self.table,rows,row_ids=[i.id for i in incidents]))
        if errors:
            raise ValueError("BigQuery historical seed rejected; inspect schema and embedding version")
