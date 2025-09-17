"""
Unit tests for Training Service
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
from unittest.mock import patch

# Add services to path
training_service_path = os.path.join(os.path.dirname(__file__), "..", "..", "services", "training_service")
sys.path.insert(0, training_service_path)

# Load training service module globally
import importlib.util
spec = importlib.util.spec_from_file_location(
    "training_main", 
    os.path.join(training_service_path, "main.py")
)
training_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(training_main)

@pytest.fixture
def training_client(environment_variables):
    """Training service test client - connects to running Docker service"""
    from tests.config import TRAINING_SERVICE_URL
    return TRAINING_SERVICE_URL

class TestTrainingService:
    """Training Service unit tests"""
    
    def test_fit_model_success(self, training_client, sample_training_data, sample_series_id):
        """Test successful model training"""
        response = requests.post(
            f"{training_client}/fit/{sample_series_id}",
            json=sample_training_data
        )
        
        # Debug: print response details if error
        if response.status_code != 200:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["series_id"] == sample_series_id
        assert data["points_used"] == 4
        assert "model_version" in data

    def test_fit_model_invalid_data(self, training_client, sample_series_id):
        """Test training with invalid data"""
        invalid_data = {
            "timestamps": [1700000000],
            "values": [42.1, 42.3],  # Mismatched lengths
            "threshold": 3.0
        }

        response = requests.post(
            f"{training_client}/fit/{sample_series_id}",
            json=invalid_data
        )

        # Debug: print response details if error
        if response.status_code != 422:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

        assert response.status_code == 422

    def test_fit_model_insufficient_data(self, training_client, sample_series_id):
        """Test training with insufficient data points"""
        insufficient_data = {
            "timestamps": [1700000000],
            "values": [42.1],
            "threshold": 3.0
        }
        
        response = requests.post(
            f"{training_client}/fit/{sample_series_id}",
            json=insufficient_data
        )
        
        assert response.status_code == 422

    def test_fit_model_constant_values(self, training_client, sample_series_id):
        """Test training with constant values (should fail)"""
        constant_data = {
            "timestamps": [1700000000, 1700000060, 1700000120],
            "values": [42.0, 42.0, 42.0],  # All same values
            "threshold": 3.0
        }
        
        response = requests.post(
            f"{training_client}/fit/{sample_series_id}",
            json=constant_data
        )
        
        assert response.status_code == 422  # Expecting 422 due to ValueError from ML model (constant values)

    def test_healthcheck(self, training_client):
        """Test training service health check"""
        response = requests.get(f"{training_client}/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields in healthcheck response
        assert data["service"] == "training"
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "database_connection" in data
        assert "metrics" in data

    def test_fit_model_creates_database_records(self, training_client, sample_training_data, test_db):
        """Test that training creates proper database records"""
        import uuid
        unique_series_id = f"test_sensor_db_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{training_client}/fit/{unique_series_id}",
            json=sample_training_data
        )

        # Debug: print response details if error
        if response.status_code != 200:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

        assert response.status_code == 200
        
        # Check model was saved
        from shared.database.models import TrainedModel, TrainingData
        model = test_db.query(TrainedModel).filter(TrainedModel.series_id == unique_series_id).first()
        assert model is not None
        assert model.mean is not None
        assert model.std is not None
        assert model.threshold == 3.0
        
        # Check training data was saved
        training_data = test_db.query(TrainingData).filter(TrainingData.series_id == unique_series_id).first()
        assert training_data is not None
        assert len(training_data.timestamps) == 4
        assert len(training_data.values) == 4
