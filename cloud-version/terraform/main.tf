# Terraform configuration for Anomaly Detection System on Google Cloud
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "bigquery.googleapis.com",
    "containerregistry.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com"
  ])

  service = each.key

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = false
}

# BigQuery Dataset
resource "google_bigquery_dataset" "anomaly_detection" {
  dataset_id                  = var.bigquery_dataset
  friendly_name              = "Anomaly Detection Dataset"
  description                = "Dataset for storing anomaly detection models, predictions, and training data"
  location                   = var.bigquery_location
  # default_table_expiration_ms commented out for testing - TTL can be set via BigQuery console

  access {
    role          = "OWNER"
    user_by_email = var.user_email
  }

  access {
    role          = "READER"
    user_by_email = var.admin_email
  }

  depends_on = [google_project_service.apis]
}

# BigQuery Tables
resource "google_bigquery_table" "trained_models" {
  dataset_id = google_bigquery_dataset.anomaly_detection.dataset_id
  table_id   = "trained_models"

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }

  schema = jsonencode([
    {
      name = "series_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "model_version"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "mean_value"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "std_value"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "threshold_value"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "points_used"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "created_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "is_active"
      type = "BOOLEAN"
      mode = "REQUIRED"
    }
  ])
}

resource "google_bigquery_table" "predictions" {
  dataset_id = google_bigquery_dataset.anomaly_detection.dataset_id
  table_id   = "predictions"

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }

  clustering = ["series_id"]

  schema = jsonencode([
    {
      name = "series_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "timestamp"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "value"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "prediction"
      type = "BOOLEAN"
      mode = "REQUIRED"
    },
    {
      name = "model_version"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "inference_latency_ms"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "database_latency_ms"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "total_latency_ms"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "created_at"
      type = "INTEGER"
      mode = "REQUIRED"
    }
  ])
}

resource "google_bigquery_table" "training_data" {
  dataset_id = google_bigquery_dataset.anomaly_detection.dataset_id
  table_id   = "training_data"

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }

  schema = jsonencode([
    {
      name = "series_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "model_version"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "timestamps"
      type = "INTEGER"
      mode = "REPEATED"
    },
    {
      name = "values"
      type = "FLOAT"
      mode = "REPEATED"
    },
    {
      name = "data_points_count"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "created_at"
      type = "INTEGER"
      mode = "REQUIRED"
    }
  ])
}

# Cloud Run Services
resource "google_cloud_run_service" "training_service" {
  name     = var.training_service_name
  location = var.region

  template {
    spec {
      containers {
        image = "${var.docker_registry}/${var.project_id}/${var.training_service_name}:${var.image_tag}"
        
        ports {
          container_port = 8080
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        resources {
          limits = {
            cpu    = var.cloud_run_cpu
            memory = var.cloud_run_memory
          }
        }
      }

      container_concurrency = var.cloud_run_concurrency
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = var.cloud_run_max_instances
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_service" "inference_service" {
  name     = var.inference_service_name
  location = var.region

  template {
    spec {
      containers {
        image = "${var.docker_registry}/${var.project_id}/${var.inference_service_name}:${var.image_tag}"
        
        ports {
          container_port = 8080
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        resources {
          limits = {
            cpu    = var.cloud_run_cpu
            memory = var.cloud_run_memory
          }
        }
      }

      container_concurrency = var.cloud_run_concurrency
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = var.cloud_run_max_instances
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_service" "monitoring_service" {
  name     = var.monitoring_service_name
  location = var.region

  template {
    spec {
      containers {
        image = "${var.docker_registry}/${var.project_id}/${var.monitoring_service_name}:${var.image_tag}"
        
        ports {
          container_port = 8080
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        env {
          name  = "TRAINING_SERVICE_URL"
          value = google_cloud_run_service.training_service.status[0].url
        }

        env {
          name  = "INFERENCE_SERVICE_URL"
          value = google_cloud_run_service.inference_service.status[0].url
        }

        resources {
          limits = {
            cpu    = var.cloud_run_cpu
            memory = var.cloud_run_memory
          }
        }
      }

      container_concurrency = var.cloud_run_concurrency
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = var.cloud_run_max_instances
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_service.training_service,
    google_cloud_run_service.inference_service
  ]
}

# IAM bindings for Cloud Run services
resource "google_cloud_run_service_iam_binding" "training_noauth" {
  count = var.enable_authentication ? 0 : 1
  
  location = google_cloud_run_service.training_service.location
  project  = google_cloud_run_service.training_service.project
  service  = google_cloud_run_service.training_service.name
  role     = "roles/run.invoker"

  members = [
    "allUsers",
  ]
}

resource "google_cloud_run_service_iam_binding" "inference_noauth" {
  count = var.enable_authentication ? 0 : 1
  
  location = google_cloud_run_service.inference_service.location
  project  = google_cloud_run_service.inference_service.project
  service  = google_cloud_run_service.inference_service.name
  role     = "roles/run.invoker"

  members = [
    "allUsers",
  ]
}

resource "google_cloud_run_service_iam_binding" "monitoring_noauth" {
  count = var.enable_authentication ? 0 : 1
  
  location = google_cloud_run_service.monitoring_service.location
  project  = google_cloud_run_service.monitoring_service.project
  service  = google_cloud_run_service.monitoring_service.name
  role     = "roles/run.invoker"

  members = [
    "allUsers",
  ]
}

# Budget Alert (if budget threshold is set)
resource "google_billing_budget" "budget" {
  count = var.budget_alert_threshold > 0 ? 1 : 0

  billing_account = var.billing_account_id
  display_name    = "Anomaly Detection Budget"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(floor(var.budget_alert_threshold))
      nanos         = (var.budget_alert_threshold - floor(var.budget_alert_threshold)) * 1000000000
    }
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = var.budget_alert_email != "" ? [
      google_monitoring_notification_channel.email[0].id
    ] : []
  }
}

# Monitoring notification channel
resource "google_monitoring_notification_channel" "email" {
  count = var.budget_alert_email != "" ? 1 : 0

  display_name = "Budget Alert Email"
  type         = "email"

  labels = {
    email_address = var.budget_alert_email
  }

  depends_on = [google_project_service.apis]
}
