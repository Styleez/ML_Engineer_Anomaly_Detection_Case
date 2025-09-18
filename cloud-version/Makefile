# Cloud Version Makefile - Deploy individual services
PROJECT_ID := $(shell gcloud config get-value project)
REGION := us-central1

.PHONY: help deploy-training deploy-inference deploy-monitoring deploy-all test-logic

help: ## Show available commands
	@echo "Cloud Anomaly Detection - Single Service Deploy"
	@echo ""
	@echo "Quick Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-15s %s\n", $$1, $$2}'

deploy-training: ## Deploy training service only
	@echo "🚀 Deploying training service..."
	@gcloud auth configure-docker -q
	@docker build -t gcr.io/$(PROJECT_ID)/anomaly-training:latest -f training-service/Dockerfile .
	@docker push gcr.io/$(PROJECT_ID)/anomaly-training:latest
	@gcloud run deploy anomaly-training \
		--image gcr.io/$(PROJECT_ID)/anomaly-training:latest \
		--region $(REGION) --platform managed --allow-unauthenticated \
		--set-env-vars GOOGLE_CLOUD_PROJECT=$(PROJECT_ID) \
		--memory 512Mi --cpu 1 --max-instances 10 -q
	@echo "✅ Training service deployed"
	@echo "🔗 URL: $$(gcloud run services describe anomaly-training --region=$(REGION) --format='value(status.url)')"

deploy-inference: ## Deploy inference service only
	@echo "🚀 Deploying inference service..."
	@gcloud auth configure-docker -q
	@docker build -t gcr.io/$(PROJECT_ID)/anomaly-inference:latest -f inference-service/Dockerfile .
	@docker push gcr.io/$(PROJECT_ID)/anomaly-inference:latest
	@gcloud run deploy anomaly-inference \
		--image gcr.io/$(PROJECT_ID)/anomaly-inference:latest \
		--region $(REGION) --platform managed --allow-unauthenticated \
		--set-env-vars GOOGLE_CLOUD_PROJECT=$(PROJECT_ID) \
		--memory 512Mi --cpu 1 --max-instances 10 -q
	@echo "✅ Inference service deployed"
	@echo "🔗 URL: $$(gcloud run services describe anomaly-inference --region=$(REGION) --format='value(status.url)')"

deploy-monitoring: ## Deploy monitoring service only
	@echo "🚀 Deploying monitoring service..."
	@gcloud auth configure-docker -q
	@docker build -t gcr.io/$(PROJECT_ID)/anomaly-monitoring:latest -f monitoring-service/Dockerfile .
	@docker push gcr.io/$(PROJECT_ID)/anomaly-monitoring:latest
	@$(eval TRAINING_URL := $(shell gcloud run services describe anomaly-training --region=$(REGION) --format='value(status.url)' 2>/dev/null || echo ""))
	@$(eval INFERENCE_URL := $(shell gcloud run services describe anomaly-inference --region=$(REGION) --format='value(status.url)' 2>/dev/null || echo ""))
	@gcloud run deploy anomaly-monitoring \
		--image gcr.io/$(PROJECT_ID)/anomaly-monitoring:latest \
		--region $(REGION) --platform managed --allow-unauthenticated \
		--set-env-vars GOOGLE_CLOUD_PROJECT=$(PROJECT_ID),TRAINING_SERVICE_URL=$(TRAINING_URL),INFERENCE_SERVICE_URL=$(INFERENCE_URL) \
		--memory 512Mi --cpu 1 --max-instances 10 -q
	@echo "✅ Monitoring service deployed"
	@echo "🔗 URL: $$(gcloud run services describe anomaly-monitoring --region=$(REGION) --format='value(status.url)')"
	@echo "📊 Dashboard: $$(gcloud run services describe anomaly-monitoring --region=$(REGION) --format='value(status.url)')/dashboard"

deploy-all: ## Deploy all services (Cloud Build)
	@echo "🚀 Deploying all services with Cloud Build..."
	@gcloud builds submit --config=cloudbuild.yaml --timeout=15m

test-logic: ## Test ML logic locally
	@echo "🧪 Testing ML logic..."
	@cd tests/local && python test_logic_only.py

test-monitoring: ## Test monitoring service locally
	@echo "📊 Testing monitoring service..."
	@cd tests/local && python test_monitoring_local.py

test-training: ## Test training service locally
	@echo "🧠 Testing training service..."
	@cd tests/local && python test_training_local.py

test-inference: ## Test inference service locally  
	@echo "🔍 Testing inference service..."
	@cd tests/local && python test_inference_local.py

status: ## Show deployed services status
	@echo "📊 Cloud Run Services:"
	@gcloud run services list --region=$(REGION) --format="table(SERVICE:label=SERVICE,URL:label=URL,LAST_DEPLOYED_BY:label=DEPLOYED_BY)"

clean: ## Remove local Docker images
	@echo "🧹 Cleaning local images..."
	@docker rmi -f gcr.io/$(PROJECT_ID)/anomaly-training:latest 2>/dev/null || true
	@docker rmi -f gcr.io/$(PROJECT_ID)/anomaly-inference:latest 2>/dev/null || true  
	@docker rmi -f gcr.io/$(PROJECT_ID)/anomaly-monitoring:latest 2>/dev/null || true
	@echo "✅ Local images cleaned"

# Quick development aliases
dev-training: test-logic test-training deploy-training ## Test + deploy training
dev-inference: test-logic test-inference deploy-inference ## Test + deploy inference  
dev-monitoring: test-logic test-monitoring deploy-monitoring ## Test + deploy monitoring

# All tests
test-all: test-logic test-training test-inference test-monitoring ## Run all local tests
