variable "project_id" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Use a valid GCP project ID."
  }
}
variable "region" {
  type    = string
  default = "us-central1"
  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]$", var.region))
    error_message = "Use a GCP region."
  }
}
variable "environment" {
  type    = string
  default = "production"
  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "Use production or staging."
  }
}
variable "deploy_runtimes" {
  description = "Enable only after images and the operator secret version exist."
  type        = bool
  default     = false
}
variable "api_image" {
  description = "Immutable Artifact Registry image digest."
  type        = string
  default     = ""
}
variable "dashboard_image" {
  type    = string
  default = ""
}
variable "operator_secret_version" {
  description = "Pinned version created outside Terraform; no secret values enter state."
  type        = string
  default     = "1"
}
variable "sql_tier" {
  type    = string
  default = "db-custom-1-3840"
}
variable "sql_availability_type" {
  type    = string
  default = "REGIONAL"
  validation {
    condition     = contains(["REGIONAL", "ZONAL"], var.sql_availability_type)
    error_message = "Choose REGIONAL or ZONAL."
  }
}
variable "gemini_model" {
  type    = string
  default = "gemini-2.5-flash"
}
variable "notification_channels" {
  type    = list(string)
  default = []
}
variable "dashboard_invokers" {
  description = "IAM principals allowed to open the private dashboard; no public default."
  type        = set(string)
  default     = []
  validation {
    condition     = alltrue([for member in var.dashboard_invokers : can(regex("^(user|group|serviceAccount):", member))])
    error_message = "Specify named IAM users, groups or service accounts."
  }
}
