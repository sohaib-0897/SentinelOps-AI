variable "enable_github_deployment" {
  type    = bool
  default = false
}
variable "github_repository" {
  type    = string
  default = "sohaib-0897/SentinelOps-AI"
}
variable "github_repository_id" {
  description = "Immutable numeric GitHub repository ID; resolve from GitHub API when enabling federation."
  type        = string
  default     = ""
}
resource "google_iam_workload_identity_pool" "github" {
  count                     = var.enable_github_deployment ? 1 : 0
  workload_identity_pool_id = "sops-${var.environment}-github"
  display_name              = "SentinelOps GitHub deployment"
  depends_on                = [google_project_service.required]
}
resource "google_iam_workload_identity_pool_provider" "github" {
  count                              = var.enable_github_deployment ? 1 : 0
  workload_identity_pool_id          = google_iam_workload_identity_pool.github[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  attribute_mapping = {
    "google.subject"          = "assertion.sub"
    "attribute.repository_id" = "assertion.repository_id"
  }
  attribute_condition = "assertion.repository_id == '${var.github_repository_id}' && assertion.repository == '${var.github_repository}' && assertion.ref == 'refs/heads/codex/build-sentinelops' && assertion.workflow_ref == '${var.github_repository}/.github/workflows/deploy.yml@refs/heads/codex/build-sentinelops'"
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
  lifecycle {
    precondition {
      condition     = can(regex("^[0-9]+$", var.github_repository_id)) && can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
      error_message = "Federation requires a numeric repository ID and owner/repository name."
    }
  }
}
resource "google_service_account" "github" {
  count      = var.enable_github_deployment ? 1 : 0
  account_id = "sops-${var.environment}-deploy"
  depends_on = [google_project_service.required]
}
resource "google_service_account_iam_member" "github" {
  count              = var.enable_github_deployment ? 1 : 0
  service_account_id = google_service_account.github[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github[0].name}/attribute.repository_id/${var.github_repository_id}"
}
resource "google_artifact_registry_repository_iam_member" "github" {
  count      = var.enable_github_deployment ? 1 : 0
  location   = var.region
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.github[0].member
}
resource "google_service_account_iam_member" "github_act_as" {
  for_each           = var.enable_github_deployment ? toset(["api", "dashboard", "telemetry", "analytics"]) : toset([])
  service_account_id = google_service_account.runtime[each.key].name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github[0].member
}
resource "google_project_iam_custom_role" "deploy" {
  count       = var.enable_github_deployment ? 1 : 0
  role_id     = "sentinelops_${var.environment}_deploy"
  title       = "SentinelOps update existing runtimes"
  permissions = ["run.services.get", "run.services.update", "run.jobs.get", "run.jobs.update", "run.operations.get"]
}
resource "google_project_iam_member" "github_deploy" {
  count   = var.enable_github_deployment ? 1 : 0
  project = var.project_id
  role    = google_project_iam_custom_role.deploy[0].name
  member  = google_service_account.github[0].member
  condition {
    title      = "existing-sentinelops-runtimes"
    expression = "resource.name in ['projects/${var.project_id}/locations/${var.region}/services/${local.prefix}-api', 'projects/${var.project_id}/locations/${var.region}/services/${local.prefix}-dashboard', 'projects/${var.project_id}/locations/${var.region}/jobs/${local.prefix}-telemetry', 'projects/${var.project_id}/locations/${var.region}/jobs/${local.prefix}-analytics'] || resource.type == 'run.googleapis.com/Operation'"
  }
}
output "github_workload_identity_provider" { value = try(google_iam_workload_identity_pool_provider.github[0].name, null) }
output "github_deploy_service_account" { value = try(google_service_account.github[0].email, null) }
