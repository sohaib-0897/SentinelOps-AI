locals {
  prefix = "sentinelops-${var.environment}"
  labels = { application = "sentinelops", environment = var.environment }
  apis = toset([
    "run.googleapis.com", "artifactregistry.googleapis.com", "pubsub.googleapis.com",
    "bigquery.googleapis.com", "sqladmin.googleapis.com", "secretmanager.googleapis.com",
    "monitoring.googleapis.com", "logging.googleapis.com", "cloudscheduler.googleapis.com",
    "aiplatform.googleapis.com", "iam.googleapis.com", "iamcredentials.googleapis.com",
    "sts.googleapis.com", "cloudresourcemanager.googleapis.com", "serviceusage.googleapis.com",
    "storage.googleapis.com"
  ])
}
resource "google_project_service" "required" {
  for_each           = local.apis
  service            = each.key
  disable_on_destroy = false
}
resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = local.prefix
  format        = "DOCKER"
  labels        = local.labels
  depends_on    = [google_project_service.required]
}
resource "google_service_account" "runtime" {
  for_each     = toset(["api", "dashboard", "telemetry", "analytics", "executor", "scheduler"])
  account_id   = "sops-${var.environment}-${each.key}"
  display_name = "SentinelOps ${each.key} (${var.environment})"
  depends_on   = [google_project_service.required]
}
resource "google_secret_manager_secret" "operator" {
  secret_id = "${local.prefix}-operator-token"
  labels    = local.labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}
resource "google_secret_manager_secret" "telemetry" {
  secret_id = "${local.prefix}-telemetry-token"
  labels    = local.labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}
resource "google_sql_database_instance" "incidents" {
  name                = "${local.prefix}-incidents"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = true
  settings {
    tier              = var.sql_tier
    availability_type = var.sql_availability_type
    disk_autoresize   = true
    disk_size         = 20
    user_labels       = local.labels
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
      # No authorized networks; Cloud SQL connector requires authenticated IAM access.
    }
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
    }
    maintenance_window {
      day  = 7
      hour = 4
    }
  }
  depends_on = [google_project_service.required]
}
resource "google_sql_database" "incidents" {
  name     = "sentinelops"
  instance = google_sql_database_instance.incidents.name
}
resource "google_sql_user" "api" {
  name     = trimsuffix(google_service_account.runtime["api"].email, ".gserviceaccount.com")
  instance = google_sql_database_instance.incidents.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}
resource "google_storage_bucket" "bootstrap" {
  name                        = "${var.project_id}-${local.prefix}-bootstrap"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels
  lifecycle_rule {
    condition { age = 1 }
    action { type = "Delete" }
  }
  depends_on = [google_project_service.required]
}
resource "google_storage_bucket_iam_member" "sql_bootstrap" {
  bucket = google_storage_bucket.bootstrap.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_sql_database_instance.incidents.service_account_email_address}"
}
resource "google_pubsub_topic" "events" {
  name       = "${local.prefix}-events"
  labels     = local.labels
  depends_on = [google_project_service.required]
}
resource "google_pubsub_topic" "dead_letter" {
  name       = "${local.prefix}-dead-letter"
  labels     = local.labels
  depends_on = [google_project_service.required]
}
resource "google_pubsub_subscription" "analytics" {
  name                       = "${local.prefix}-analytics"
  topic                      = google_pubsub_topic.events.id
  ack_deadline_seconds       = 600
  message_retention_duration = "604800s"
  enable_message_ordering    = true
  expiration_policy { ttl = "" }
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 10
  }
}
resource "google_pubsub_subscription" "dead_letter" {
  name                       = "${local.prefix}-dead-letter-review"
  topic                      = google_pubsub_topic.dead_letter.id
  message_retention_duration = "604800s"
  expiration_policy { ttl = "" }
}
data "google_project" "current" {}
resource "google_pubsub_topic_iam_member" "dead_letter_forward" {
  topic      = google_pubsub_topic.dead_letter.name
  role       = "roles/pubsub.publisher"
  member     = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on = [google_project_service.required]
}
resource "google_pubsub_subscription_iam_member" "dead_letter_source" {
  subscription = google_pubsub_subscription.analytics.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
