# Variables for Anomaly Detection System Terraform

variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "bigquery_dataset" {
  description = "BigQuery dataset name"
  type        = string
  default     = "anomaly_detection"
}

variable "bigquery_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run services"
  type        = string
  default     = "1"
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run services"
  type        = string
  default     = "512Mi"
}

variable "cloud_run_max_instances" {
  description = "Maximum instances for Cloud Run services"
  type        = number
  default     = 10
}

variable "cloud_run_concurrency" {
  description = "Concurrency setting for Cloud Run services"
  type        = number
  default     = 80
}

variable "training_service_name" {
  description = "Name for the training service"
  type        = string
  default     = "anomaly-training"
}

variable "inference_service_name" {
  description = "Name for the inference service"
  type        = string
  default     = "anomaly-inference"
}

variable "monitoring_service_name" {
  description = "Name for the monitoring service"
  type        = string
  default     = "anomaly-monitoring"
}

variable "docker_registry" {
  description = "Docker registry URL"
  type        = string
  default     = "gcr.io"
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "user_email" {
  description = "User email for IAM and notifications"
  type        = string
}

variable "admin_email" {
  description = "Admin email for notifications"
  type        = string
}

variable "enable_authentication" {
  description = "Enable authentication for Cloud Run services"
  type        = bool
  default     = false
}

variable "metrics_retention_days" {
  description = "Days to retain metrics data"
  type        = number
  default     = 30
}

variable "budget_alert_threshold" {
  description = "Budget alert threshold in USD (0 to disable)"
  type        = number
  default     = 0
}

variable "budget_alert_email" {
  description = "Email for budget alerts"
  type        = string
  default     = ""
}

variable "billing_account_id" {
  description = "Billing account ID for budget alerts"
  type        = string
  default     = ""
}
