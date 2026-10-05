mock_provider "google" {
  mock_data "google_project" {
    defaults = { number = "123456789012" }
  }
}
variables {
  project_id = "sentinelops-test"
}
run "foundation_is_private_and_non_destructive" {
  command = plan
  assert {
    condition     = length(google_cloud_run_v2_service.api) == 0
    error_message = "Foundation must not deploy placeholder runtime images."
  }
  assert {
    condition     = alltrue([for account in google_service_account.runtime : length(account.account_id) <= 30])
    error_message = "Service account IDs must fit the IAM limit."
  }
  assert {
    condition     = google_sql_database_instance.incidents.deletion_protection && !google_bigquery_dataset.operations.delete_contents_on_destroy
    error_message = "Durable incident and analytics storage must be protected."
  }
  assert {
    condition     = !contains([for grant in google_project_iam_member.runtime : grant.role], "roles/run.admin")
    error_message = "Runtime identities cannot receive broad Run admin."
  }
}
run "runtimes_use_digests_and_private_invokers" {
  command = plan
  variables {
    deploy_runtimes = true
    api_image       = "us-central1-docker.pkg.dev/sentinelops-test/sentinelops-production/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    dashboard_image = "us-central1-docker.pkg.dev/sentinelops-test/sentinelops-production/dashboard@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  }
  assert {
    condition     = google_cloud_run_v2_service.api[0].template[0].scaling[0].max_instance_count == 1
    error_message = "The current control plane requires a single active instance."
  }
  assert {
    condition     = length(google_cloud_run_v2_service_iam_member.dashboard_invoker) == 0
    error_message = "Dashboard cannot gain public access by default."
  }
  assert {
    condition     = length(google_cloud_run_v2_job.worker) == 2 && length(google_cloud_scheduler_job.worker) == 2
    error_message = "Both bounded workers need scheduled triggers."
  }
}
