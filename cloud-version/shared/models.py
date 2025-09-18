"""
Modelos simplificados para versão Cloud
"""
from pydantic import BaseModel, Field
from typing import List
import numpy as np


class DataPoint(BaseModel):
    timestamp: int = Field(..., description="Unix timestamp")
    value: float = Field(..., description="Time series value")


class TrainRequest(BaseModel):
    timestamps: List[int] = Field(..., description="Unix timestamps")
    values: List[float] = Field(..., description="Time series values") 
    threshold: float = Field(default=3.0, description="Anomaly threshold (sigma)")
    
    def validate_data(self):
        """Validate training data"""
        if len(self.timestamps) != len(self.values):
            raise ValueError("Timestamps and values must have same length")
        if len(self.timestamps) < 2:
            raise ValueError("Need at least 2 data points")
        if self.threshold <= 0:
            raise ValueError("Threshold must be positive")
        # Sort by timestamp
        sorted_data = sorted(zip(self.timestamps, self.values))
        self.timestamps, self.values = zip(*sorted_data)


class TrainResponse(BaseModel):
    series_id: str
    version: str  
    points_used: int
    model_stats: dict


class PredictRequest(BaseModel):
    timestamp: str = Field(..., description="Unix timestamp as string")
    value: float = Field(..., description="Value to check for anomaly")


class PredictResponse(BaseModel):
    anomaly: bool
    model_version: str


class SimpleAnomalyModel:
    """Simplified 3-sigma anomaly detection model"""
    
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold
        self.mean = None
        self.std = None
        self.is_trained = False
        
    def fit(self, values: List[float]):
        """Train model with values"""
        if len(values) < 2:
            raise ValueError("Need at least 2 values")
            
        self.mean = float(np.mean(values))
        self.std = float(np.std(values))
        
        # Std=0 is handled in predict(), not an error
        self.is_trained = True
        
    def predict(self, value: float) -> bool:
        """Predict if value is anomaly"""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        # Handle zero standard deviation (all values identical)
        if self.std == 0:
            return value != self.mean
            
        return abs(value - self.mean) > self.threshold * self.std
    
    def get_stats(self) -> dict:
        """Get model statistics"""
        return {
            "mean": self.mean,
            "std": self.std, 
            "threshold": self.threshold,
            "is_trained": self.is_trained
        }
