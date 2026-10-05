locals {
  api_env = {
    APP_ENV                     = "production", DEMO_MODE = "false", GCP_PROJECT_ID = var.project_id,
    GCP_REGION                  = var.region, VERTEX_LOCATION = var.region, GEMINI_MODEL = var.gemini_model,
    LOG_PROVIDER                = "gcp", METRICS_PROVIDER = "gcp", DEPLOYMENT_PROVIDER = "gcp",
    VECTOR_PROVIDER             = "bigquery", LLM_PROVIDER = "adk", REMEDIATION_PROVIDER = "gcp",
    REMEDIATION_SERVICE_ACCOUNT = google_service_account.runtime["executor"].email,
    EVENT_PROVIDER              = "pubsub", PUBSUB_TOPIC = google_pubsub_topic.events.name,
    BIGQUERY_DATASET            = google_bigquery_dataset.operations.dataset_id,
    CLOUD_SQL_INSTANCE          = google_sql_database_instance.incidents.connection_name,
    CLOUD_SQL_USER              = google_sql_user.api.name, CLOUD_SQL_DATABASE = google_sql_database.incidents.name,
    CORS_ORIGINS                = "[]", VERIFICATION_ATTEMPTS = "12", VERIFICATION_INTERVAL = "60"
  }
}
resource "google_cloud_run_v2_service" "api" {
  count               = var.deploy_runtimes ? 1 : 0
  name                = "${local.prefix}-api"
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"
  template {
    service_account                  = google_service_account.runtime["api"].email
    timeout                          = "900s"
    max_instance_request_concurrency = 40
    scaling {
      min_instance_count = 1
      max_instance_count = 1
    }
    containers {
      image = var.api_image
      resources {
        limits            = { cpu = "1", memory = "1Gi" }
        cpu_idle          = false
        startup_cpu_boost = true
      }
      ports { container_port = 8000 }
      dynamic "env" {
        for_each = local.api_env
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name = "OPERATOR_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.operator.secret_id
            version = var.operator_secret_version
          }
        }
      }
      startup_probe {
        http_get { path = "/health" }
        period_seconds    = 10
        failure_threshold = 30
      }
      liveness_probe {
        http_get { path = "/health" }
      }
    }
  }
  lifecycle {
    precondition {
      condition     = can(regex("@sha256:[a-f0-9]{64}$", var.api_image))
      error_message = "Deploy an immutable API image digest."
    }
  }
  depends_on = [google_project_iam_member.runtime, google_secret_manager_secret_iam_member.operator, google_sql_user.api]
}
resource "google_cloud_run_v2_service" "dashboard" {
  count               = var.deploy_runtimes ? 1 : 0
  name                = "${local.prefix}-dashboard"
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"
  template {
    service_account = google_service_account.runtime["dashboard"].email
    timeout         = "900s"
    scaling { max_instance_count = 3 }
    containers {
      image = var.dashboard_image
      ports { container_port = 3000 }
      resources { limits = { cpu = "1", memory = "512Mi" } }
      env {
        name  = "API_BASE_URL"
        value = google_cloud_run_v2_service.api[0].uri
      }
      env {
        name  = "API_AUTH_AUDIENCE"
        value = google_cloud_run_v2_service.api[0].uri
      }
      env {
        name = "API_OPERATOR_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.operator.secret_id
            version = var.operator_secret_version
          }
        }
      }
    }
  }
  lifecycle {
    precondition {
      condition     = can(regex("@sha256:[a-f0-9]{64}$", var.dashboard_image))
      error_message = "Deploy an immutable dashboard image digest."
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.operator]
}
resource "google_cloud_run_v2_service_iam_member" "api_invoker" {
  for_each = var.deploy_runtimes ? toset(["dashboard", "telemetry"]) : toset([])
  name     = google_cloud_run_v2_service.api[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = google_service_account.runtime[each.key].member
}
resource "google_cloud_run_v2_service_iam_member" "dashboard_invoker" {
  for_each = var.deploy_runtimes ? var.dashboard_invokers : toset([])
  name     = google_cloud_run_v2_service.dashboard[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = each.value
}
resource "google_cloud_run_v2_service_iam_member" "api_operator" {
  for_each = var.deploy_runtimes ? var.dashboard_invokers : toset([])
  name     = google_cloud_run_v2_service.api[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = each.value
}
resource "google_cloud_run_v2_job" "worker" {
  for_each            = var.deploy_runtimes ? toset(["telemetry", "analytics"]) : toset([])
  name                = "${local.prefix}-${each.key}"
  location            = var.region
  deletion_protection = true
  template {
    task_count  = 1
    parallelism = 1
    template {
      service_account = google_service_account.runtime[each.key].email
      timeout         = "240s"
      max_retries     = 2
      containers {
        image   = var.api_image
        command = ["python", "-m", each.key == "telemetry" ? "sentinelops.worker" : "sentinelops.analytics_worker"]
        args    = each.key == "telemetry" ? ["--once"] : []
        resources { limits = { cpu = "1", memory = "512Mi" } }
        dynamic "env" {
          for_each = {
            GCP_PROJECT_ID      = var.project_id, GCP_REGION = var.region, DEMO_MODE = "false",
            BIGQUERY_DATASET    = google_bigquery_dataset.operations.dataset_id,
            PUBSUB_SUBSCRIPTION = google_pubsub_subscription.analytics.name,
            API_BASE_URL        = google_cloud_run_v2_service.api[0].uri,
            API_AUTH_AUDIENCE   = google_cloud_run_v2_service.api[0].uri
          }
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = each.key == "telemetry" ? [1] : []
          content {
            name = "OPERATOR_TOKEN"
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.operator.secret_id
                version = var.operator_secret_version
              }
            }
          }
        }
      }
    }
  }
  depends_on = [google_project_iam_member.runtime, google_pubsub_subscription_iam_member.consume, google_bigquery_table_iam_member.analytics_write, google_secret_manager_secret_iam_member.operator]
}
resource "google_cloud_run_v2_job_iam_member" "scheduler" {
  for_each = google_cloud_run_v2_job.worker
  name     = each.value.name
  location = var.region
  role     = "roles/run.invoker"
  member   = google_service_account.runtime["scheduler"].member
}
resource "google_cloud_scheduler_job" "worker" {
  for_each         = google_cloud_run_v2_job.worker
  name             = "${local.prefix}-${each.key}"
  region           = var.region
  schedule         = "* * * * *"
  time_zone        = "Etc/UTC"
  attempt_deadline = "30s"
  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/${each.value.id}:run"
    body        = base64encode("{}")
    headers     = { "Content-Type" = "application/json" }
    oauth_token {
      service_account_email = google_service_account.runtime["scheduler"].email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
  depends_on = [google_cloud_run_v2_job_iam_member.scheduler]
}
output "api_url" { value = try(google_cloud_run_v2_service.api[0].uri, null) }
output "dashboard_url" { value = try(google_cloud_run_v2_service.dashboard[0].uri, null) }
output "worker_jobs" { value = { for name, job in google_cloud_run_v2_job.worker : name => job.name } }
