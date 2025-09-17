#!/bin/bash
set -e

# Load configuration from env_config.yaml
CONFIG_FILE="../config/env_config.yaml"

# Extract values using yq (install: brew install yq)
PROJECT_ID=$(yq '.gcp.project_id' $CONFIG_FILE)
REGION=$(yq '.gcp.region' $CONFIG_FILE)
API_ID=$(yq '.gcp.api_gateway.api_id' $CONFIG_FILE)
GATEWAY_ID=$(yq '.gcp.api_gateway.gateway_id' $CONFIG_FILE)

# Service names
TRAINING_SERVICE=$(yq '.services.training_service.name' $CONFIG_FILE)
INFERENCE_SERVICE=$(yq '.services.inference_service.name' $CONFIG_FILE)
PLOT_SERVICE=$(yq '.services.plot_service.name' $CONFIG_FILE)
HEALTHCHECK_SERVICE=$(yq '.services.healthcheck_service.name' $CONFIG_FILE)

API_CONFIG="api_config.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Deploying API Gateway for Anomaly Detection...${NC}"

# 1. Enable necessary APIs
echo "Enabling required APIs..."
gcloud services enable \
    apigateway.googleapis.com \
    servicemanagement.googleapis.com \
    servicecontrol.googleapis.com

# 2. Create service account
echo "Creating service account..."
gcloud iam service-accounts create anomaly-gateway-sa \
    --display-name="Anomaly Detection Gateway SA" \
    --project=$PROJECT_ID

# 3. Grant necessary roles
echo "Granting IAM roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:anomaly-gateway-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/apigateway.admin"

# 4. Create API
echo "Creating API..."
gcloud api-gateway apis create $API_ID \
    --project=$PROJECT_ID

# 5. Substitute variables in API config
echo "Preparing API config with environment variables..."
export TRAINING_SERVICE INFERENCE_SERVICE PLOT_SERVICE HEALTHCHECK_SERVICE REGION
envsubst < $API_CONFIG > api_config_final.yaml

# 5. Create API Config
echo "Creating API config..."
gcloud api-gateway api-configs create v1 \
    --api=$API_ID \
    --openapi-spec=api_config_final.yaml \
    --project=$PROJECT_ID \
    --backend-auth-service-account=anomaly-gateway-sa@$PROJECT_ID.iam.gserviceaccount.com

# 6. Create Gateway
echo "Creating gateway..."
gcloud api-gateway gateways create $GATEWAY_ID \
    --api=$API_ID \
    --api-config=v1 \
    --location=$REGION \
    --project=$PROJECT_ID

# 7. Get Gateway URL
GATEWAY_URL=$(gcloud api-gateway gateways describe $GATEWAY_ID \
    --location=$REGION \
    --project=$PROJECT_ID \
    --format="value(defaultHostname)")

echo -e "${GREEN}Deployment complete!${NC}"
echo "Gateway URL: https://$GATEWAY_URL"

# 8. Create API Key (optional)
read -p "Create API key? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    API_KEY=$(gcloud alpha services api-keys create \
        --display-name="Anomaly Detection API Key" \
        --api-target=service=$API_ID \
        --format="value(keyString)")
    
    echo -e "${GREEN}API Key created:${NC} $API_KEY"
    echo "Store this key securely!"
fi

# 9. Test endpoints
echo -e "\nTesting endpoints..."
curl -i -X GET https://$GATEWAY_URL/healthcheck

echo -e "\n${GREEN}Setup complete!${NC}"
echo "Use the following environment variables in your applications:"
echo "GATEWAY_URL=https://$GATEWAY_URL"
if [[ -n "$API_KEY" ]]; then
    echo "API_KEY=$API_KEY"
fi
