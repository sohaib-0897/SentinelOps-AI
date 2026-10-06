output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}
output "cloud_sql_instance" { value = google_sql_database_instance.incidents.connection_name }
output "cloud_sql_user" { value = google_sql_user.api.name }
output "operator_secret" { value = google_secret_manager_secret.operator.secret_id }
output "telemetry_secret" { value = google_secret_manager_secret.telemetry.secret_id }
output "sql_instance_name" { value = google_sql_database_instance.incidents.name }
output "bootstrap_bucket" { value = google_storage_bucket.bootstrap.name }
output "service_accounts" { value = { for key, identity in google_service_account.runtime : key => identity.email } }
