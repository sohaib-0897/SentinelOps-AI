locals {
  project_roles = {
    api_logging    = { identity = "api", role = "roles/logging.viewer" }
    api_monitoring = { identity = "api", role = "roles/monitoring.viewer" }
    api_run        = { identity = "api", role = "roles/run.viewer" }
    api_vertex     = { identity = "api", role = "roles/aiplatform.user" }
    api_bq         = { identity = "api", role = "roles/bigquery.jobUser" }
    analytics_bq   = { identity = "analytics", role = "roles/bigquery.jobUser" }
    api_sql_client = { identity = "api", role = "roles/cloudsql.client" }
    api_sql_user   = { identity = "api", role = "roles/cloudsql.instanceUser" }
    telemetry_logs = { identity = "telemetry", role = "roles/logging.viewer" }
    telemetry_mon  = { identity = "telemetry", role = "roles/monitoring.viewer" }
    telemetry_run  = { identity = "telemetry", role = "roles/run.viewer" }
  }
}
resource "google_project_iam_member" "runtime" {
  project  = var.project_id
  for_each = local.project_roles
  role     = each.value.role
  member   = google_service_account.runtime[each.value.identity].member
}
resource "google_secret_manager_secret_iam_member" "operator" {
  for_each  = toset(["api", "dashboard"])
  secret_id = google_secret_manager_secret.operator.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.runtime[each.key].member
}
resource "google_secret_manager_secret_iam_member" "telemetry" {
  for_each  = toset(["api", "telemetry"])
  secret_id = google_secret_manager_secret.telemetry.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.runtime[each.key].member
}
resource "google_pubsub_topic_iam_member" "publish" {
  topic  = google_pubsub_topic.events.name
  role   = "roles/pubsub.publisher"
  member = google_service_account.runtime["api"].member
}
resource "google_pubsub_subscription_iam_member" "consume" {
  subscription = google_pubsub_subscription.analytics.name
  role         = "roles/pubsub.subscriber"
  member       = google_service_account.runtime["analytics"].member
}
resource "google_bigquery_table_iam_member" "analytics_write" {
  dataset_id = google_bigquery_dataset.operations.dataset_id
  table_id   = google_bigquery_table.events.table_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.runtime["analytics"].member
}
resource "google_bigquery_table_iam_member" "history_read" {
  dataset_id = google_bigquery_dataset.operations.dataset_id
  table_id   = google_bigquery_table.history.table_id
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.runtime["api"].member
}
resource "google_bigquery_table_iam_member" "history_write" {
  dataset_id = google_bigquery_dataset.operations.dataset_id
  table_id   = google_bigquery_table.history.table_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.runtime["analytics"].member
}
# The API has no direct Cloud Run mutation role. Its executor impersonation is
# limited to this identity, which can update only the allow-listed orders-api.
resource "google_project_iam_custom_role" "rollback" {
  role_id     = "sentinelops_${var.environment}_rollback"
  title       = "SentinelOps approved traffic rollback"
  permissions = ["run.services.get", "run.services.update", "run.revisions.get", "run.operations.get"]
}
resource "google_project_iam_member" "executor" {
  project = var.project_id
  role    = google_project_iam_custom_role.rollback.name
  member  = google_service_account.runtime["executor"].member
  condition {
    title      = "orders-api-only"
    expression = "resource.name == 'projects/${var.project_id}/locations/${var.region}/services/orders-api' || resource.name.startsWith('projects/${var.project_id}/locations/${var.region}/services/orders-api/revisions/') || resource.type == 'run.googleapis.com/Operation'"
  }
}
resource "google_service_account_iam_member" "executor_token" {
  service_account_id = google_service_account.runtime["executor"].name
  role               = google_project_iam_custom_role.executor_token.name
  member             = google_service_account.runtime["api"].member
}
resource "google_project_iam_custom_role" "executor_token" {
  role_id     = "sentinelops_${var.environment}_executor_token"
  title       = "SentinelOps executor access token only"
  permissions = ["iam.serviceAccounts.getAccessToken"]
}
