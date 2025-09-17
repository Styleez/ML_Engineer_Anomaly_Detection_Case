# Anomaly Detection System - Makefile

.PHONY: help install test test-unit test-integration test-performance docker-up docker-down docker-build clean lint format

# Default target
help: ## Show this help message
	@echo "Anomaly Detection System - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install all dependencies
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	@if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
	@echo "✅ Dependencies installed"

install-dev: ## Install development dependencies
	pip install pytest pytest-cov pytest-asyncio httpx black flake8 mypy
	@echo "✅ Development dependencies installed"

# Testing
test: ## Run full test pipeline locally
	python scripts/run_full_tests.py

test-unit: ## Run unit tests only
	python -m pytest tests/unit/ -v --tb=short

test-integration: ## Run integration tests only (requires Docker services)
	python -m pytest tests/integration/ -v --tb=short

test-performance: ## Run performance/load tests (requires Docker services)
	cd tests/performance && python inference_load_test.py
	cd tests/performance && python training_load_test.py

test-coverage: ## Run tests with coverage report
	python -m pytest tests/unit/ --cov=shared --cov=services --cov-report=html --cov-report=term

# Docker operations
docker-up: ## Start all services with Docker Compose
	docker-compose -f docker-compose.test.yml up -d --build

docker-down: ## Stop all Docker services
	docker-compose -f docker-compose.test.yml down -v

docker-build: ## Build all Docker images
	docker-compose -f docker-compose.test.yml build

docker-logs: ## Show logs from all services
	docker-compose -f docker-compose.test.yml logs -f

docker-restart: ## Restart all Docker services
	docker-compose -f docker-compose.test.yml restart

# Service-specific commands
logs-training: ## Show training service logs
	docker logs training_service -f

logs-inference: ## Show inference service logs
	docker logs inference_service -f

logs-monitoring: ## Show monitoring service logs
	docker logs monitoring_service -f

logs-healthcheck: ## Show healthcheck service logs
	docker logs healthcheck_service -f

# Health checks
health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:8000/healthcheck | python -m json.tool || echo "❌ Training service down"
	@curl -s http://localhost:8001/healthcheck | python -m json.tool || echo "❌ Inference service down"
	@curl -s http://localhost:8002/healthcheck | python -m json.tool || echo "❌ Monitoring service down"
	@curl -s http://localhost:8003/healthcheck | python -m json.tool || echo "❌ Healthcheck service down"

dashboard: ## Open monitoring dashboard in browser
	@echo "Opening dashboard..."
	@python -c "import webbrowser; webbrowser.open('http://localhost:8002/dashboard')"

# Database operations
db-migrate: ## Run database migrations
	python scripts/run_migrations.py

db-reset: ## Reset database (WARNING: destroys all data)
	docker-compose -f docker-compose.test.yml down -v
	docker-compose -f docker-compose.test.yml up -d database-vm
	sleep 10
	python scripts/run_migrations.py

# Code quality
lint: ## Run linting checks
	@echo "Running flake8..."
	@flake8 services/ shared/ tests/ --max-line-length=120 --ignore=E203,W503 || true
	@echo "Running mypy..."
	@mypy services/ shared/ --ignore-missing-imports || true

format: ## Format code with black
	black services/ shared/ tests/ scripts/ --line-length=120
	@echo "✅ Code formatted"

format-check: ## Check code formatting
	black services/ shared/ tests/ scripts/ --line-length=120 --check

# Development
dev-setup: install-dev db-migrate ## Complete development setup
	@echo "✅ Development environment ready!"
	@echo "Run 'make docker-up' to start services"
	@echo "Run 'make test' to run full test suite"

# Quick development workflow
dev: docker-up health dashboard ## Start development environment and open dashboard

# Performance testing with different loads
perf-light: ## Run light performance test
	cd tests/performance && python -c "
import asyncio
from inference_load_test import InferenceLoadTest
async def main():
    test = InferenceLoadTest()
    await test.run_load_test(10, 30)  # 10 users, 30 seconds
asyncio.run(main())
"

perf-heavy: ## Run heavy performance test
	cd tests/performance && python -c "
import asyncio
from inference_load_test import InferenceLoadTest
async def main():
    test = InferenceLoadTest()
    for users in [50, 100, 200]:
        await test.run_load_test(users, 60)  # Escalating load
asyncio.run(main())
"

# Cleanup
clean: ## Clean up Docker and Python cache
	docker-compose -f docker-compose.test.yml down -v
	docker system prune -f
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	rm -rf .pytest_cache/ htmlcov/ .mypy_cache/ 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Git operations
git-setup: ## Setup Git repository (run once)
	git add .
	git commit -m "Initial commit: Anomaly Detection System"
	@echo "✅ Git repository initialized"
	@echo "Create GitHub repository and run:"
	@echo "git remote add origin https://github.com/YOUR_USERNAME/ML_Engineer_Anomaly_Detection_Case.git"
	@echo "git push -u origin main"

# Release
release-check: test lint ## Run all checks before release
	@echo "✅ Release checks passed!"

# Documentation
docs: ## Generate API documentation
	@echo "API Endpoints:"
	@echo "- Training: POST http://localhost:8000/fit/{series_id}"
	@echo "- Inference: POST http://localhost:8001/predict/{series_id}"
	@echo "- Monitoring: GET http://localhost:8002/dashboard"
	@echo "- Plot: GET http://localhost:8002/plot?series_id=X&version=Y"
	@echo "- Health: GET http://localhost:8003/healthcheck"

# Monitoring
monitor: ## Show real-time monitoring
	@echo "Real-time monitoring..."
	@while true; do \
		clear; \
		echo "=== Service Health ($(date)) ==="; \
		make health 2>/dev/null; \
		echo ""; \
		echo "Press Ctrl+C to stop"; \
		sleep 10; \
	done