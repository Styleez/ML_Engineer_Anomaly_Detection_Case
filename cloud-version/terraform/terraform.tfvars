project_id = "mlops-test-472217"
region     = "us-central1"

# BigQuery Configuration
bigquery_dataset  = "anomaly_detection"
bigquery_location = "US"

# Cloud Run Configuration
cloud_run_cpu           = "1"
cloud_run_memory        = "512Mi"
cloud_run_max_instances = 10
cloud_run_concurrency   = 80

# Service Names
training_service_name   = "anomaly-training"
inference_service_name  = "anomaly-inference"
monitoring_service_name = "anomaly-monitoring"

# Docker Configuration
docker_registry = "gcr.io"
image_tag      = "latest"

# User Configuration
user_email  = "arodrigues@folks.la"
admin_email = "arodrigues@folks.la"

# Security
enable_authentication = false

# Monitoring
metrics_retention_days = 30

# Budget Alerts (disabled for testing)
budget_alert_threshold = 0
budget_alert_email     = ""
billing_account_id     = ""
