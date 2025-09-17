"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.database import Base, get_db
from shared.database.models import TrainedModel, TrainingData, PredictionLog
from datetime import datetime, timezone
import time
import redis
from unittest.mock import MagicMock

# Import professional test configuration
from tests.config import DATABASE_URL

# Force test environment to use Docker containers
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = DATABASE_URL

TEST_DATABASE_URL = DATABASE_URL

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine with smart detection"""
    import sys
    
    # Check if we're running integration tests
    is_integration_test = any('integration' in str(arg) for arg in sys.argv)
    
    # Check if we're running service unit tests (these make HTTP calls to real services)
    is_service_unit_test = any(
        'test_plot_service.py' in str(arg) or 
        'test_training_service.py' in str(arg) or
        'test_inference_service.py' in str(arg)
        for arg in sys.argv
    )
    
    # Also check if we're running ALL unit tests (tests/unit/) - treat as service tests
    # because they include the service tests that need real database
    is_all_unit_tests = any('tests/unit' in str(arg) or 'tests\\unit' in str(arg) for arg in sys.argv)
    
    if is_all_unit_tests and not any('test_services_simplified.py' in str(arg) for arg in sys.argv):
        is_service_unit_test = True
    
    # These tests make HTTP calls to real services, so need real database
    if is_integration_test or is_service_unit_test:
        print("🔍 Service test detected - using existing PostgreSQL database")
        engine = create_engine(TEST_DATABASE_URL)
        yield engine
        # NO cleanup for service tests
        return
    
    # Pure unit tests (like test_services_simplified.py): Use isolated SQLite
    print("🔍 Pure unit test detected - using temporary SQLite database")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # SQLite in-memory is automatically cleaned up

@pytest.fixture
def test_db(test_engine):
    """Create test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture
def override_get_db(test_db):
    """Override database dependency"""
    def _get_test_db():
        yield test_db
    return _get_test_db

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.ping.return_value = True
    mock_redis.keys.return_value = []
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    return mock_redis

@pytest.fixture
def mock_external_connections(monkeypatch, mock_redis):
    """Mock external connections for unit tests only (when needed)"""
    
    # Mock Redis connections
    def mock_redis_connection(*args, **kwargs):
        return mock_redis
    
    # Apply patches
    monkeypatch.setattr("redis.Redis", mock_redis_connection)
    monkeypatch.setattr("redis.from_url", mock_redis_connection)

@pytest.fixture
def sample_training_data():
    """Sample training data for tests"""
    return {
        "timestamps": [1700000000, 1700000060, 1700000120, 1700000180],
        "values": [42.1, 42.3, 41.9, 42.5],
        "threshold": 3.0
    }

@pytest.fixture
def sample_prediction_data():
    """Sample prediction data for tests"""
    return {
        "timestamp": "1700000240",
        "value": 50.5
    }

@pytest.fixture
def sample_series_id():
    """Sample series ID for tests"""
    return "test_sensor_001"

@pytest.fixture
def trained_model_in_db(test_db, sample_series_id):
    """Create a trained model in test database"""
    from datetime import datetime
    import uuid
    
    # Use unique series_id to avoid conflicts
    unique_series_id = f"{sample_series_id}_{uuid.uuid4().hex[:8]}"
    
    model = TrainedModel(
        series_id=unique_series_id,
        model_type="anomaly_detection",
        mean=42.2,
        std=0.25,
        threshold=3.0,
        model_version="1.0",
        training_points=4,
        training_data_stats={
            "count": 4,
            "mean": 42.2,
            "std": 0.25,
            "min": 41.9,
            "max": 42.5
        }
    )
    test_db.add(model)
    
    training_data = TrainingData(
        series_id=unique_series_id,
        model_version="1.0",
        timestamps=[1700000000, 1700000060, 1700000120, 1700000180],
        values=[42.1, 42.3, 41.9, 42.5],
        data_points_count=4,
        created_at=int(time.time())
    )
    test_db.add(training_data)
    test_db.commit()
    
    # Return both model and unique series_id
    return {"model": model, "series_id": unique_series_id}

@pytest.fixture
def environment_variables():
    """Set test environment variables for local development tests"""
    original_env = os.environ.copy()
    
    # Force test environment settings
    test_env = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": TEST_DATABASE_URL,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "16379",  # Different port to avoid conflicts
        "REDIS_DB": "15",       # Different DB
        "TESTING": "true"       # Flag to indicate testing mode
    }
    
    # Update environment
    os.environ.update(test_env)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
