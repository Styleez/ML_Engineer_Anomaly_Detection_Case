"""
Unit tests for Inference Service
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import sys
import os

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
    """Inference service test client"""
    return TestClient(inference_main.app)

class TestInferenceService:
    """Inference Service unit tests"""
    
    def test_predict_with_cached_model(self, inference_client, sample_prediction_data, sample_series_id):
        """Test prediction with cached model"""
        # Mock cached model data
        cached_model = {
            "mean": 42.2,
            "std": 0.25,
            "threshold": 3.0,
            "version": "1.0",
            "training_points": 100
        }
        
        with patch('inference_main.redis_client') as mock_redis:
            mock_redis.get.side_effect = lambda key: json.dumps(cached_model) if "model:" in key else None
            mock_redis.setex.return_value = True
            
            response = inference_client.post(
                f"/predict/{sample_series_id}",
                json=sample_prediction_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "anomaly" in data
            assert data["model_version"] == "1.0"
            assert isinstance(data["anomaly"], bool)

    def test_predict_cache_miss(self, inference_client, sample_prediction_data, sample_series_id):
        """Test prediction when model not in cache"""
        with patch('inference_main.redis_client') as mock_redis:
            mock_redis.get.return_value = None  # Cache miss

            response = inference_client.post(
                f"/predict/{sample_series_id}",
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
        
        response = inference_client.post(
            f"/predict/{sample_series_id}",
            json=invalid_data
        )
        
        assert response.status_code == 422

    def test_predict_caches_result(self, inference_client, sample_prediction_data, sample_series_id):
        """Test that prediction result is cached"""
        # Mock cached model data
        cached_model = {
            "mean": 42.2,
            "std": 0.25,
            "threshold": 3.0,
            "version": "1.0",
            "training_points": 100
        }
        
        with patch('inference_main.redis_client') as mock_redis:
            mock_redis.get.side_effect = lambda key: json.dumps(cached_model) if "model:" in key else None
            mock_redis.setex.return_value = True
            
            response = inference_client.post(
                f"/predict/{sample_series_id}",
                json=sample_prediction_data
            )
            
            assert response.status_code == 200
            
            # Verify result was cached
            mock_redis.setex.assert_called()
            cache_call = mock_redis.setex.call_args
            assert cache_call[0][1] == 300  # TTL of 5 minutes

    def test_healthcheck(self, inference_client):
        """Test inference service health check"""
        with patch('inference_main.redis_client') as mock_redis:
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {"keyspace_hits": 100, "keyspace_misses": 10}
            
            response = inference_client.get("/healthcheck")
            
        assert response.status_code == 200
        data = response.json()
        # New OpenAPI spec format
        assert "series_trained" in data
        assert "inference_latency_ms" in data
        assert "training_latency_ms" in data
        assert isinstance(data["series_trained"], int)
        assert "avg" in data["inference_latency_ms"]
        assert "p95" in data["inference_latency_ms"]

    def test_healthcheck_redis_error(self, inference_client):
        """Test health check when Redis is down"""
        with patch('inference_main.redis_client') as mock_redis:
            import redis
            mock_redis.ping.side_effect = redis.RedisError("Redis connection failed")
            
            response = inference_client.get("/healthcheck")
            assert response.status_code == 503

    def test_predict_anomaly_detection(self, inference_client, sample_series_id):
        """Test anomaly detection logic"""
        # Mock model with specific parameters
        cached_model = {
            "mean": 42.0,
            "std": 1.0,
            "threshold": 3.0,
            "version": "1.0",
            "training_points": 100
        }
        
        with patch('inference_main.redis_client') as mock_redis:
            mock_redis.get.side_effect = lambda key: json.dumps(cached_model) if "model:" in key else None
            mock_redis.setex.return_value = True
            
            # Test normal value (should not be anomaly)
            normal_data = {"timestamp": "1700000000", "value": 42.5}
            response = inference_client.post(f"/predict/{sample_series_id}", json=normal_data)
            assert response.status_code == 200
            assert not response.json()["anomaly"]
            
            # Test anomalous value (should be anomaly)
            anomaly_data = {"timestamp": "1700000000", "value": 50.0}  # 8 std devs from mean
            response = inference_client.post(f"/predict/{sample_series_id}", json=anomaly_data)
            assert response.status_code == 200
            assert response.json()["anomaly"]
