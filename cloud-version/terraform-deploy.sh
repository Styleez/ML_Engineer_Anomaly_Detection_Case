#!/bin/bash
# Terraform deployment script for Anomaly Detection System

set -e

echo "🚀 Anomaly Detection System - Terraform Deployment"
echo "=================================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Create .env file based on env.example"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Validate required variables
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ GOOGLE_CLOUD_PROJECT not set in .env"
    exit 1
fi

if [ -z "$USER_EMAIL" ]; then
    echo "❌ USER_EMAIL not set in .env"
    exit 1
fi

echo "📋 Project: $GOOGLE_CLOUD_PROJECT"
echo "📧 User: $USER_EMAIL"
echo ""

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Please install Terraform first."
    echo "   https://learn.hashicorp.com/tutorials/terraform/install-cli"
    exit 1
fi

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "❌ Not authenticated with gcloud. Please run:"
    echo "   gcloud auth login"
    echo "   gcloud auth application-default login"
    exit 1
fi

# Set gcloud project
gcloud config set project $GOOGLE_CLOUD_PROJECT

cd terraform

# Create terraform.tfvars from environment variables
echo "📝 Creating terraform.tfvars from .env..."
cat > terraform.tfvars << EOF
project_id = "$GOOGLE_CLOUD_PROJECT"
region     = "${CLOUD_RUN_REGION:-us-central1}"

# BigQuery Configuration
bigquery_dataset  = "${BQ_DATASET:-anomaly_detection}"
bigquery_location = "${BQ_LOCATION:-US}"

# Cloud Run Configuration
cloud_run_cpu           = "${CLOUD_RUN_CPU:-1}"
cloud_run_memory        = "${CLOUD_RUN_MEMORY:-512Mi}"
cloud_run_max_instances = ${CLOUD_RUN_MAX_INSTANCES:-10}
cloud_run_concurrency   = ${CLOUD_RUN_CONCURRENCY:-80}

# Service Names
training_service_name   = "${TRAINING_SERVICE_NAME:-anomaly-training}"
inference_service_name  = "${INFERENCE_SERVICE_NAME:-anomaly-inference}"
monitoring_service_name = "${MONITORING_SERVICE_NAME:-anomaly-monitoring}"

# Docker Configuration
docker_registry = "${DOCKER_REGISTRY:-gcr.io}"
image_tag      = "${IMAGE_TAG:-latest}"

# User Configuration
user_email  = "$USER_EMAIL"
admin_email = "${ADMIN_EMAIL:-$USER_EMAIL}"

# Security
enable_authentication = ${ENABLE_AUTHENTICATION:-false}

# Monitoring
metrics_retention_days = ${METRICS_RETENTION_DAYS:-30}

# Budget Alerts
budget_alert_threshold = ${BUDGET_ALERT_THRESHOLD:-0}
budget_alert_email     = "${BUDGET_ALERT_EMAIL:-}"
billing_account_id     = "${BILLING_ACCOUNT_ID:-}"
EOF

echo "✅ terraform.tfvars created"

# Initialize Terraform
echo "🔧 Initializing Terraform..."
terraform init

# Validate configuration
echo "✅ Validating Terraform configuration..."
terraform validate

# Plan deployment
echo "📋 Planning deployment..."
terraform plan -out=tfplan

# Ask for confirmation
echo ""
read -p "🚀 Deploy infrastructure? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Applying Terraform configuration..."
    terraform apply tfplan
    
    echo ""
    echo "✅ Infrastructure deployed successfully!"
    echo ""
    echo "📊 Next steps:"
    echo "1. Build and deploy services: gcloud builds submit --config=../cloudbuild.yaml"
    echo "2. View outputs: terraform output"
    echo "3. Open dashboard: terraform output -raw dashboard_url"
    echo ""
    
    # Show key outputs
    echo "🔗 Service URLs:"
    terraform output -json api_endpoints | jq -r 'to_entries[] | "\(.key): \(.value)"'
    
else
    echo "❌ Deployment cancelled"
    rm -f tfplan
fi

cd ..

echo "✅ Terraform deployment script completed!"
