"""
Test configuration and constants
"""
import os

# Service URLs for testing
TRAINING_SERVICE_URL = os.getenv("TRAINING_SERVICE_URL", "http://localhost:8000")
INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:8001")
MONITORING_SERVICE_URL = os.getenv("MONITORING_SERVICE_URL", "http://localhost:8002")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost")

# Test data constants
TEST_SERIES_PREFIX = "test_sensor"
DEFAULT_THRESHOLD = 3.0

# Docker Compose environments
DOCKER_COMPOSE_TEST = "docker-compose.test.yml"  # VM simulation
DOCKER_COMPOSE_LOCAL = "docker-compose.local.yml"  # Simple local development

# Test timeouts
DEFAULT_TIMEOUT = 30
TRAINING_TIMEOUT = 60
INFERENCE_TIMEOUT = 5
