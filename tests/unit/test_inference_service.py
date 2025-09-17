"""
Unit tests for Inference Service
"""
import os
import sys

# Configure test environment to use Docker containers
os.environ["ENVIRONMENT"] = "test"

# Import test configuration
from tests.config import DATABASE_URL
os.environ["DATABASE_URL"] = DATABASE_URL

import pytest
import requests
from unittest.mock import patch, MagicMock
import json

# Add services to path
inference_service_path = os.path.join(os.path.dirname(__file__), "..", "..", "services", "inference_service")
sys.path.insert(0, inference_service_path)

# Load inference service module globally
import importlib.util
import sys
spec = importlib.util.spec_from_file_location(
    "inference_main", 
    os.path.join(inference_service_path, "main.py")
)
inference_main = importlib.util.module_from_spec(spec)
# Register module in sys.modules for patches to work
sys.modules['inference_main'] = inference_main
spec.loader.exec_module(inference_main)

@pytest.fixture
def inference_client(environment_variables):
    """Inference service test client - connects to running Docker service"""
    from tests.config import INFERENCE_SERVICE_URL
    return INFERENCE_SERVICE_URL

class TestInferenceService:
    """Inference Service unit tests"""
    

    def test_predict_cache_miss(self, inference_client, sample_prediction_data):
        """Test prediction when model not in cache"""
        import uuid
        
        # Use unique series ID that definitely doesn't exist
        unique_series_id = f"nonexistent_{uuid.uuid4().hex[:8]}"
        
        with patch('inference_main.redis_client') as mock_redis:
            mock_redis.get.return_value = None  # Cache miss

            response = requests.post(
                f"{inference_client}/predict/{unique_series_id}",
                json=sample_prediction_data
            )

            # Debug: print response details if error
            if response.status_code != 404:
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")

            assert response.status_code == 404  # Model not found

    def test_predict_invalid_data(self, inference_client, sample_series_id):
        """Test prediction with invalid data"""
        invalid_data = {
            "timestamp": "invalid_timestamp",
            "value": "not_a_number"
        }
        
        response = requests.post(
            f"{inference_client}/predict/{sample_series_id}",
            json=invalid_data
        )
        
        assert response.status_code == 422


    def test_healthcheck(self, inference_client):
        """Test inference service health check"""
        response = requests.get(f"{inference_client}/healthcheck")
            
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields in healthcheck response
        assert data["service"] == "inference"
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "redis_connection" in data
        assert "database_connection" in data
        assert "metrics" in data


    def test_predict_anomaly_detection(self, inference_client):
        """Test anomaly detection logic - first train model, then predict"""
        from tests.config import TRAINING_SERVICE_URL
        import uuid
        
        # Use unique series ID for this test
        unique_series_id = f"anomaly_test_{uuid.uuid4().hex[:8]}"
        
        # First, train a model with varied data (to avoid std=0)
        training_data = {
            "timestamps": [1700000000, 1700000060, 1700000120, 1700000180],
            "values": [42.0, 42.2, 41.8, 42.1],  # Some variation for valid std
            "threshold": 3.0
        }
        
        # Train the model
        train_response = requests.post(
            f"{TRAINING_SERVICE_URL}/fit/{unique_series_id}",
            json=training_data
        )
        assert train_response.status_code == 200
        
        # Test normal value (should not be anomaly)
        normal_data = {"timestamp": "1700000240", "value": 42.1}
        response = requests.post(
            f"{inference_client}/predict/{unique_series_id}", 
            json=normal_data
        )
        assert response.status_code == 200
        data = response.json()
        assert "anomaly" in data
        assert not data["anomaly"]  # Should not be anomaly
        
        # Test anomalous value (should be anomaly)
        anomaly_data = {"timestamp": "1700000300", "value": 50.0}  # Far from mean
        response = requests.post(
            f"{inference_client}/predict/{unique_series_id}", 
            json=anomaly_data
        )
        assert response.status_code == 200
        data = response.json()
        assert "anomaly" in data
        assert data["anomaly"]  # Should be anomaly
