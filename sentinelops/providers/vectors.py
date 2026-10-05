import json
import math
import re
from collections import Counter
from pathlib import Path

from sentinelops.domain.models import HistoricalIncident


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9_]+", text.lower())


class LocalVectorProvider:
    """Deterministic TF-IDF cosine retrieval; no network or embedding model needed."""

    def __init__(self, incidents: list[HistoricalIncident] | None = None) -> None:
        path = Path(__file__).resolve().parents[2] / "fixtures/historical-incidents.json"
        self.incidents = incidents if incidents is not None else [HistoricalIncident.model_validate(i) for i in json.loads(path.read_text(encoding="utf-8"))]
        self.documents = [Counter(tokens(i.signature + " " + i.title)) for i in self.incidents]
        self.idf = {word: math.log((len(self.documents) + 1) / (1 + sum(word in doc for doc in self.documents))) + 1 for doc in self.documents for word in doc}

    async def search(self, query: str, limit: int = 3) -> list[HistoricalIncident]:
        query_counts = Counter(tokens(query))
        def vector(counts: Counter[str]) -> dict[str, float]:
            return {word: count * self.idf.get(word, 1) for word, count in counts.items()}
        q = vector(query_counts)
        q_norm = math.sqrt(sum(value**2 for value in q.values()))
        matches: list[HistoricalIncident] = []
        for incident, document in zip(self.incidents, self.documents, strict=True):
            values = vector(document)
            denominator = q_norm * math.sqrt(sum(value**2 for value in values.values()))
            score = sum(q.get(word, 0) * value for word, value in values.items()) / denominator if denominator else 0
            if score > 0:
                matches.append(incident.model_copy(update={"similarity": min(1., score)}))
        return sorted(matches, key=lambda match: (-match.similarity, match.id))[:limit]
