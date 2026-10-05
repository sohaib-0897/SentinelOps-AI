output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}
output "cloud_sql_instance" { value = google_sql_database_instance.incidents.connection_name }
output "cloud_sql_user" { value = google_sql_user.api.name }
output "operator_secret" { value = google_secret_manager_secret.operator.secret_id }
output "service_accounts" { value = { for key, identity in google_service_account.runtime : key => identity.email } }
