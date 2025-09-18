#!/bin/bash
# Deploy individual service to Cloud Run
# Usage: ./deploy-single.sh <service_name>
# Examples: 
#   ./deploy-single.sh training
#   ./deploy-single.sh inference  
#   ./deploy-single.sh monitoring

set -e

SERVICE_NAME=$1
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

if [ -z "$SERVICE_NAME" ]; then
    echo "❌ Usage: $0 <service_name>"
    echo ""
    echo "Available services:"
    echo "  training    - Training service only"
    echo "  inference   - Inference service only"
    echo "  monitoring  - Monitoring service only"
    echo "  all         - All services (same as cloudbuild.yaml)"
    echo ""
    echo "Examples:"
    echo "  $0 training"
    echo "  $0 monitoring"
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "❌ Not authenticated with gcloud. Please run:"
    echo "   gcloud auth login"
    echo "   gcloud auth application-default login"
    exit 1
fi

echo "🚀 Single Service Deploy - $SERVICE_NAME"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

case $SERVICE_NAME in
    "training")
        SERVICE_DIR="training-service"
        SERVICE_FULL_NAME="anomaly-training"
        ;;
    "inference")
        SERVICE_DIR="inference-service"
        SERVICE_FULL_NAME="anomaly-inference"
        ;;
    "monitoring")
        SERVICE_DIR="monitoring-service"
        SERVICE_FULL_NAME="anomaly-monitoring"
        ;;
    "all")
        echo "🏗️ Building all services with Cloud Build..."
        gcloud builds submit --config=cloudbuild.yaml --timeout=15m
        echo "✅ All services deployed!"
        exit 0
        ;;
    *)
        echo "❌ Unknown service: $SERVICE_NAME"
        echo "Available: training, inference, monitoring, all"
        exit 1
        ;;
esac

IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_FULL_NAME:latest"

echo "📦 Service: $SERVICE_FULL_NAME"
echo "📁 Directory: $SERVICE_DIR"
echo "🏷️ Image: $IMAGE_NAME"
echo ""

# Configure Docker for gcloud
echo "🔧 Configuring Docker..."
gcloud auth configure-docker --quiet

# Build image
echo "🏗️ Building Docker image..."
docker build \
    -t $IMAGE_NAME \
    -f $SERVICE_DIR/Dockerfile \
    .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

# Push image
echo "📤 Pushing image to registry..."
docker push $IMAGE_NAME

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed"
    exit 1
fi

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."

# Get existing service URLs for monitoring service env vars
if [ "$SERVICE_NAME" = "monitoring" ]; then
    TRAINING_URL=$(gcloud run services describe anomaly-training --region=$REGION --format="value(status.url)" 2>/dev/null || echo "")
    INFERENCE_URL=$(gcloud run services describe anomaly-inference --region=$REGION --format="value(status.url)" 2>/dev/null || echo "")
    
    ENV_VARS="GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
    if [ ! -z "$TRAINING_URL" ]; then
        ENV_VARS="$ENV_VARS,TRAINING_SERVICE_URL=$TRAINING_URL"
    fi
    if [ ! -z "$INFERENCE_URL" ]; then
        ENV_VARS="$ENV_VARS,INFERENCE_SERVICE_URL=$INFERENCE_URL"
    fi
    
    gcloud run deploy $SERVICE_FULL_NAME \
        --image $IMAGE_NAME \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "$ENV_VARS" \
        --memory 512Mi \
        --cpu 1 \
        --max-instances 10 \
        --concurrency 80
else
    gcloud run deploy $SERVICE_FULL_NAME \
        --image $IMAGE_NAME \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
        --memory 512Mi \
        --cpu 1 \
        --max-instances 10 \
        --concurrency 80
fi

if [ $? -ne 0 ]; then
    echo "❌ Cloud Run deploy failed"
    exit 1
fi

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_FULL_NAME --region=$REGION --format="value(status.url)")

echo ""
echo "✅ Deployment successful!"
echo "🔗 Service URL: $SERVICE_URL"
echo ""

# Test health check
echo "🩺 Testing health check..."
if curl -f -s "$SERVICE_URL/healthcheck" > /dev/null; then
    echo "✅ Health check passed"
    
    # Show specific endpoints
    case $SERVICE_NAME in
        "training")
            echo ""
            echo "📚 Training endpoints:"
            echo "   Health: $SERVICE_URL/healthcheck"
            echo "   Train:  $SERVICE_URL/fit/{series_id}"
            echo ""
            echo "🧪 Test command:"
            echo "curl -X POST '$SERVICE_URL/fit/sensor_test' \\"
            echo "  -H 'Content-Type: application/json' \\"
            echo "  -d '{\"timestamps\": [1609459200, 1609459260], \"values\": [23.5, 24.1]}'"
            ;;
        "inference")
            echo ""
            echo "🔍 Inference endpoints:"
            echo "   Health:  $SERVICE_URL/healthcheck"
            echo "   Predict: $SERVICE_URL/predict/{series_id}"
            echo ""
            echo "🧪 Test command (after training):"
            echo "curl -X POST '$SERVICE_URL/predict/sensor_test' \\"
            echo "  -H 'Content-Type: application/json' \\"
            echo "  -d '{\"timestamp\": \"1609459320\", \"value\": 24.0}'"
            ;;
        "monitoring")
            echo ""
            echo "📊 Monitoring endpoints:"
            echo "   Health:    $SERVICE_URL/healthcheck"
            echo "   Dashboard: $SERVICE_URL/dashboard"
            echo "   Latency:   $SERVICE_URL/metrics/latency"
            echo "   Usage:     $SERVICE_URL/metrics/model-usage"
            echo ""
            echo "🌐 Open dashboard: $SERVICE_URL/dashboard"
            ;;
    esac
else
    echo "⚠️ Health check failed - service might still be starting"
    echo "   Try: curl $SERVICE_URL/healthcheck"
fi

echo ""
echo "⚡ Quick redeploy next time:"
echo "   $0 $SERVICE_NAME"
