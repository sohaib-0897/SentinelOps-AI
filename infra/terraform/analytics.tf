resource "google_bigquery_dataset" "operations" {
  dataset_id                 = "sentinelops_${var.environment}"
  location                   = var.region
  labels                     = local.labels
  delete_contents_on_destroy = false
  depends_on                 = [google_project_service.required]
}
resource "google_bigquery_table" "events" {
  dataset_id          = google_bigquery_dataset.operations.dataset_id
  table_id            = "domain_events"
  deletion_protection = true
  clustering          = ["event_type", "incident_id"]
  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }
  schema = jsonencode([
    { name = "event_id", type = "STRING", mode = "REQUIRED" },
    { name = "timestamp", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "event_type", type = "STRING", mode = "REQUIRED" },
    { name = "incident_id", type = "STRING", mode = "NULLABLE" },
    { name = "payload", type = "STRING", mode = "REQUIRED" }
  ])
}
resource "google_bigquery_table" "canonical_events" {
  dataset_id          = google_bigquery_dataset.operations.dataset_id
  table_id            = "canonical_domain_events"
  deletion_protection = true
  view {
    use_legacy_sql = false
    query          = "SELECT * FROM `${var.project_id}.${google_bigquery_table.events.dataset_id}.${google_bigquery_table.events.table_id}` QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC, payload DESC) = 1"
  }
}
resource "google_bigquery_table" "history" {
  dataset_id          = google_bigquery_dataset.operations.dataset_id
  table_id            = "historical_incidents"
  deletion_protection = true
  schema = jsonencode(concat(
    [for field in ["id", "title", "signature", "cause", "remediation", "outcome", "embedding_version"] : { name = field, type = "STRING", mode = "REQUIRED" }],
    [{ name = "embedding", type = "FLOAT64", mode = "REPEATED" }]
  ))
}
output "bigquery_dataset" { value = google_bigquery_dataset.operations.dataset_id }
