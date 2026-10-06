resource "google_monitoring_alert_policy" "api_errors" {
  display_name          = "${local.prefix}: API server errors"
  combiner              = "OR"
  notification_channels = var.notification_channels
  conditions {
    display_name = "Sustained API 5xx responses"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${local.prefix}-api\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "300s"
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }
  alert_strategy { auto_close = "1800s" }
  depends_on = [google_project_service.required]
}
resource "google_monitoring_alert_policy" "analytics_backlog" {
  display_name          = "${local.prefix}: analytics backlog"
  combiner              = "OR"
  notification_channels = var.notification_channels
  conditions {
    display_name = "Oldest unacknowledged event exceeds ten minutes"
    condition_threshold {
      filter          = "resource.type = \"pubsub_subscription\" AND resource.labels.subscription_id = \"${google_pubsub_subscription.analytics.name}\" AND metric.type = \"pubsub.googleapis.com/subscription/oldest_unacked_message_age\""
      comparison      = "COMPARISON_GT"
      threshold_value = 600
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }
  depends_on = [google_project_service.required]
}
