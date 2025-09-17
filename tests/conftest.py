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
import redis
from unittest.mock import MagicMock

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

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
    return mock_redis

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
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(training_data)
    test_db.commit()
    
    # Return both model and unique series_id
    return {"model": model, "series_id": unique_series_id}

@pytest.fixture
def environment_variables():
    """Set test environment variables"""
    original_env = os.environ.copy()
    os.environ.update({
        "ENVIRONMENT": "test",
        "DATABASE_URL": TEST_DATABASE_URL,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "1"
    })
    yield
    os.environ.clear()
    os.environ.update(original_env)
