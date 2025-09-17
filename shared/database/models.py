"""
Database models for persisting ML models and metadata
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime, timezone
from .database import Base

class TrainedModel(Base):
    """Table for storing trained ML models"""
    __tablename__ = "trained_models"
    
    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(String, index=True, nullable=False)  # Removed unique constraint
    model_type = Column(String, default="anomaly_detection", nullable=False)
    
    # Model parameters
    mean = Column(Float, nullable=False)
    std = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    
    # Model metadata
    model_version = Column(String, default="v1")
    training_points = Column(Integer, nullable=False)
    training_data_stats = Column(JSON)  # Store training statistics
    
    # Timestamps (Unix format)
    created_at = Column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()))
    updated_at = Column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()))
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('series_id', 'model_version', name='uq_series_version'),
    )

class PredictionLog(Base):
    """Table for logging predictions"""
    __tablename__ = "prediction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(String, index=True, nullable=False)
    
    # Prediction data
    timestamp = Column(Integer, nullable=False)  # Unix timestamp of data point
    value = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    deviation = Column(Float, nullable=False)
    
    # Model used
    model_version = Column(String, nullable=False)
    
    # Prediction metadata
    predicted_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()))

class TrainingData(Base):
    """Table for storing training time series data"""
    __tablename__ = "training_data"
    
    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(String, nullable=False, index=True)
    model_version = Column(String, nullable=False)
    
    # Training data points (stored as JSON array)
    timestamps = Column(JSON, nullable=False)  # Array of Unix timestamps
    values = Column(JSON, nullable=False)      # Array of float values
    
    # Metadata
    data_points_count = Column(Integer, nullable=False)
    created_at = Column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()))
    
    # Composite index for efficient querying
    __table_args__ = (
        {"schema": None},  # Default schema
    )

# ServiceHealth table removida - monitoramento será feito externamente
