"""
Unit tests for Plot Service
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os

# Add services to path
monitoring_service_path = os.path.join(os.path.dirname(__file__), "..", "..", "services", "monitoring_service")
sys.path.insert(0, monitoring_service_path)

# Load monitoring service module globally
import importlib.util
spec = importlib.util.spec_from_file_location(
    "monitoring_main", 
    os.path.join(monitoring_service_path, "main.py")
)
monitoring_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitoring_main)

@pytest.fixture
def monitoring_client(override_get_db, environment_variables):
    """Monitoring service test client"""
    from shared.database.database import get_db
    monitoring_main.app.dependency_overrides[get_db] = override_get_db
    return TestClient(monitoring_main.app)

class TestMonitoringService:
    """Monitoring Service unit tests (plot functionality)"""
    
    def test_get_plot_success(self, monitoring_client, trained_model_in_db):
        """Test successful plot data retrieval"""
        series_id = trained_model_in_db["series_id"]
        response = monitoring_client.get(f"/plot?series_id={series_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["series_id"] == series_id
        assert data["version"] == "1.0"
        assert len(data["timestamps"]) == 4
        assert len(data["values"]) == 4
        assert data["data_points_count"] == 4

    def test_get_plot_specific_version(self, monitoring_client, trained_model_in_db):
        """Test plot data retrieval with specific version"""
        series_id = trained_model_in_db["series_id"]
        response = monitoring_client.get(f"/plot?series_id={series_id}&version=1.0")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"

    def test_get_plot_nonexistent_series(self, monitoring_client):
        """Test plot data retrieval for nonexistent series"""
        response = monitoring_client.get("/plot?series_id=nonexistent_series")
        
        # Debug: print response details if error
        if response.status_code != 404:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        
        assert response.status_code == 404

    def test_get_plot_nonexistent_version(self, monitoring_client, trained_model_in_db):
        """Test plot data retrieval for nonexistent version"""
        series_id = trained_model_in_db["series_id"]
        response = monitoring_client.get(f"/plot?series_id={series_id}&version=999.0")
        
        assert response.status_code == 404

    def test_get_plot_missing_series_id(self, monitoring_client):
        """Test plot data retrieval without series_id parameter"""
        response = monitoring_client.get("/plot")
        
        assert response.status_code == 422  # Missing required parameter

    def test_healthcheck(self, monitoring_client):
        """Test plot service health check"""
        response = monitoring_client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "plot"
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_get_plot_data_structure(self, monitoring_client, trained_model_in_db):
        """Test plot data has correct structure"""
        series_id = trained_model_in_db["series_id"]
        response = monitoring_client.get(f"/plot?series_id={series_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = ["series_id", "version", "timestamps", "values", "data_points_count"]
        for field in required_fields:
            assert field in data
        
        # Check data types
        assert isinstance(data["timestamps"], list)
        assert isinstance(data["values"], list)
        assert isinstance(data["data_points_count"], int)
        assert len(data["timestamps"]) == len(data["values"])

    def test_get_plot_most_recent_version(self, monitoring_client, test_db, sample_series_id):
        """Test that plot returns most recent version when version not specified"""
        from shared.database.models import TrainingData
        
        # Create multiple versions
        old_data = TrainingData(
            series_id=sample_series_id,
            model_version="1.0",
            timestamps=[1700000000, 1700000060],
            values=[42.1, 42.3],
            data_points_count=2,
            created_at=1700000000
        )
        test_db.add(old_data)
        
        new_data = TrainingData(
            series_id=sample_series_id,
            model_version="2.0",
            timestamps=[1700000000, 1700000060, 1700000120],
            values=[42.1, 42.3, 41.9],
            data_points_count=3,
            created_at=1700001000  # More recent
        )
        test_db.add(new_data)
        test_db.commit()
        
        response = monitoring_client.get(f"/plot?series_id={sample_series_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0"  # Should return most recent
        assert data["data_points_count"] == 3
