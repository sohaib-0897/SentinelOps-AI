from sentinelops.domain.models import Incident, IncidentEvent, MetricPoint


def threshold_exceeded(point: MetricPoint) -> bool:
    return point.error_rate >= .05 or point.latency_ms >= 800 or point.memory >= .9 or point.cpu >= .95 or point.db_connections >= .9


def detect_incident(series: list[MetricPoint], active_incidents: list[Incident]) -> Incident | None:
    if len(series) < 3 or not all(threshold_exceeded(point) for point in series[-3:]):
        return None
    service_id = series[-1].service_id
    if any(i.service_id == service_id and i.state not in {"RESOLVED", "CLOSED", "FAILED"} for i in active_incidents):
        return None
    point = series[-1]
    symptoms = []
    if point.error_rate >= .05:
        symptoms.append(f"HTTP error rate {point.error_rate:.1%}")
    if point.latency_ms >= 800:
        symptoms.append(f"p95 latency {point.latency_ms:.0f}ms")
    if point.memory >= .9:
        symptoms.append(f"Memory utilization {point.memory:.0%}")
    if point.cpu >= .95:
        symptoms.append(f"CPU utilization {point.cpu:.0%}")
    if point.db_connections >= .9:
        symptoms.append(f"Database connections {point.db_connections:.0%}")
    incident = Incident(title=f"{service_id}: {symptoms[0]}", service_id=service_id, started_at=series[-3].timestamp, symptoms=symptoms)
    incident.timeline.append(IncidentEvent(timestamp=point.timestamp, kind="MetricThresholdExceeded", message="Three consecutive samples exceeded health thresholds", data=point.model_dump(mode="json")))
    return incident
