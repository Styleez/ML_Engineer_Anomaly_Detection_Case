# Outputs for Anomaly Detection System

output "project_id" {
  description = "Google Cloud Project ID"
  value       = var.project_id
}

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.anomaly_detection.dataset_id
}

output "bigquery_dataset_location" {
  description = "BigQuery dataset location"
  value       = google_bigquery_dataset.anomaly_detection.location
}

output "training_service_url" {
  description = "Training service URL"
  value       = google_cloud_run_service.training_service.status[0].url
}

output "inference_service_url" {
  description = "Inference service URL"
  value       = google_cloud_run_service.inference_service.status[0].url
}

output "monitoring_service_url" {
  description = "Monitoring service URL"
  value       = google_cloud_run_service.monitoring_service.status[0].url
}

output "dashboard_url" {
  description = "Monitoring dashboard URL"
  value       = "${google_cloud_run_service.monitoring_service.status[0].url}/dashboard"
}

output "api_endpoints" {
  description = "API endpoints for testing"
  value = {
    train_model     = "${google_cloud_run_service.training_service.status[0].url}/fit/{series_id}"
    predict         = "${google_cloud_run_service.inference_service.status[0].url}/predict/{series_id}"
    health_training = "${google_cloud_run_service.training_service.status[0].url}/healthcheck"
    health_inference = "${google_cloud_run_service.inference_service.status[0].url}/healthcheck"
    health_monitoring = "${google_cloud_run_service.monitoring_service.status[0].url}/healthcheck"
    metrics_latency = "${google_cloud_run_service.monitoring_service.status[0].url}/metrics/latency"
    metrics_throughput = "${google_cloud_run_service.monitoring_service.status[0].url}/metrics/throughput"
    metrics_model_usage = "${google_cloud_run_service.monitoring_service.status[0].url}/metrics/model-usage"
  }
}

output "curl_examples" {
  description = "Example curl commands"
  value = {
    train_model = "curl -X POST '${google_cloud_run_service.training_service.status[0].url}/fit/sensor_1' -H 'Content-Type: application/json' -d '{\"timestamps\": [1609459200, 1609459260, 1609459320], \"values\": [23.5, 24.1, 23.8]}'"
    predict = "curl -X POST '${google_cloud_run_service.inference_service.status[0].url}/predict/sensor_1' -H 'Content-Type: application/json' -d '{\"timestamp\": \"1609459500\", \"value\": 25.5}'"
    health_check = "curl '${google_cloud_run_service.monitoring_service.status[0].url}/healthcheck'"
  }
}

output "bigquery_tables" {
  description = "BigQuery table information"
  value = {
    trained_models = "${var.project_id}.${google_bigquery_dataset.anomaly_detection.dataset_id}.${google_bigquery_table.trained_models.table_id}"
    predictions = "${var.project_id}.${google_bigquery_dataset.anomaly_detection.dataset_id}.${google_bigquery_table.predictions.table_id}"
    training_data = "${var.project_id}.${google_bigquery_dataset.anomaly_detection.dataset_id}.${google_bigquery_table.training_data.table_id}"
  }
}

output "cost_estimation" {
  description = "Estimated monthly costs"
  value = {
    cloud_run_estimate = "~$3-10/month (based on 1000-10000 requests/day)"
    bigquery_estimate = "$0.10-1/month (storage + queries)"
    total_estimate = "~$5-15/month for typical usage"
    note = "Actual costs depend on usage patterns. Monitor via Google Cloud Console."
  }
}
