"""
Test configuration and constants
"""
import os

# Database configuration for tests (from docker-compose.test.yml)
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"), 
    "user": os.getenv("DB_USER", "anomaly_user"),
    "password": os.getenv("DB_PASSWORD", "test_password"),
    "database": os.getenv("DB_NAME", "anomaly_detection")
}

# Build database URL from config
DATABASE_URL = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"

# Service URLs for testing (from docker-compose.test.yml ports)
TRAINING_SERVICE_URL = os.getenv("TRAINING_SERVICE_URL", "http://localhost:8000")
INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:8001") 
MONITORING_SERVICE_URL = os.getenv("MONITORING_SERVICE_URL", "http://localhost:8002")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:80")

# Test data constants
TEST_SERIES_PREFIX = "test_sensor"
DEFAULT_THRESHOLD = 3.0

# Test timeouts
DEFAULT_TIMEOUT = 30
TRAINING_TIMEOUT = 60
INFERENCE_TIMEOUT = 5
