variable "create_demo_target" {
  description = "Create a private, unprivileged orders-api demonstration workload. Disable for an existing monitored service."
  type        = bool
  default     = true
}
resource "google_service_account" "target" {
  count      = var.create_demo_target ? 1 : 0
  account_id = "sops-${var.environment}-target"
  depends_on = [google_project_service.required]
}
resource "google_cloud_run_v2_service" "target" {
  count               = var.deploy_runtimes && var.create_demo_target ? 1 : 0
  name                = "orders-api"
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"
  template {
    service_account = google_service_account.target[0].email
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    containers {
      image   = var.api_image
      command = ["uvicorn", "sentinelops.demo_service:app", "--host", "0.0.0.0", "--port", "8000"]
      ports { container_port = 8000 }
      env {
        name  = "DEMO_MODE"
        value = "false"
      }
      env {
        name  = "FAILURE_MODE"
        value = "none"
      }
      resources { limits = { cpu = "1", memory = "512Mi" } }
    }
  }
}
resource "google_cloud_run_v2_service_iam_member" "target_operator" {
  for_each = var.deploy_runtimes && var.create_demo_target ? var.dashboard_invokers : toset([])
  name     = google_cloud_run_v2_service.target[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = each.value
}
resource "google_service_account_iam_member" "executor_target_identity" {
  count              = var.create_demo_target ? 1 : 0
  service_account_id = google_service_account.target[0].name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.runtime["executor"].member
}
output "target_url" { value = try(google_cloud_run_v2_service.target[0].uri, null) }
