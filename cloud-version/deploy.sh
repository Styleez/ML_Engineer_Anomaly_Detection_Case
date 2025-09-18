#!/bin/bash

# Deploy script para Google Cloud Platform
# Requer: gcloud CLI configurado e autenticado

set -e

# Configurações
PROJECT_ID=${1:-"your-gcp-project-id"}
REGION=${2:-"us-central1"}

echo "🚀 Deploying Anomaly Detection System to Google Cloud"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Verificar se gcloud está configurado
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Verificar autenticação
echo "🔐 Checking gcloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "❌ Not authenticated with gcloud. Please run:"
    echo "   gcloud auth login"
    echo "   gcloud auth application-default login"
    echo ""
    echo "For BigQuery access, also run:"
    echo "   gcloud auth application-default login"
    exit 1
fi

echo "✅ Authentication verified"

# Definir projeto
gcloud config set project $PROJECT_ID

# Habilitar APIs necessárias
echo "📋 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable bigquery.googleapis.com

# Build e deploy usando Cloud Build
echo "🔨 Building and deploying services..."
gcloud builds submit --config=cloudbuild.yaml

# Verificar deployments
echo "✅ Checking deployments..."

TRAINING_URL=$(gcloud run services describe anomaly-training --region=$REGION --format="value(status.url)")
INFERENCE_URL=$(gcloud run services describe anomaly-inference --region=$REGION --format="value(status.url)")

echo ""
echo "🔗 Service URLs:"
echo "Training Service:  $TRAINING_URL"
echo "Inference Service: $INFERENCE_URL"
echo ""

# Teste básico
echo "🧪 Testing services..."
curl -s "$TRAINING_URL" | jq '.'
curl -s "$INFERENCE_URL" | jq '.'

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📖 Usage examples:"
echo ""
echo "# Train a model:"
echo "curl -X POST '$TRAINING_URL/fit/sensor_1' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"timestamps\": [1609459200, 1609459260, 1609459320], \"values\": [23.5, 24.1, 23.8]}'"
echo ""
echo "# Make prediction:"
echo "curl -X POST '$INFERENCE_URL/predict/sensor_1' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"timestamp\": \"1609459500\", \"value\": 25.5}'"
