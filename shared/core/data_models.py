from typing import Sequence, List
from pydantic import BaseModel, Field, field_validator
import numpy as np

class DataPoint(BaseModel):
    timestamp: int = Field(..., description="Unix timestamp of the time the data point was collected")
    value: float = Field(..., description="Value of the time series measured at time `timestamp`")
    
    def __eq__(self, other):
        """Enable comparison between DataPoints"""
        if not isinstance(other, DataPoint):
            return False
        return self.timestamp == other.timestamp and self.value == other.value
    
    def __hash__(self):
        """Enable DataPoint to be used in sets"""
        return hash((self.timestamp, self.value))

class TimeSeries(BaseModel):
    data: Sequence[DataPoint] = Field(..., description="List of datapoints, ordered in time, of subsequent measurements of some quantity")
    
    @field_validator('data')
    @classmethod
    def validate_data_points(cls, v):
        """Validate TimeSeries data"""
        if not v:
            raise ValueError("TimeSeries cannot be empty")
        
        # Check if timestamps are sorted
        timestamps = [dp.timestamp for dp in v]
        if timestamps != sorted(timestamps):
            raise ValueError("DataPoints must be sorted by timestamp")
        
        return v
    
    @classmethod
    def from_lists(cls, timestamps: List[int], values: List[float]) -> "TimeSeries":
        """Create TimeSeries from separate timestamp and value lists"""
        if len(timestamps) != len(values):
            raise ValueError("Timestamps and values must have the same length")
        
        data_points = [DataPoint(timestamp=ts, value=val) for ts, val in zip(timestamps, values)]
        return cls(data=data_points)
    
    @property
    def values(self) -> List[float]:
        """Extract just the values from the time series"""
        return [dp.value for dp in self.data]
    
    @property
    def timestamps(self) -> List[int]:
        """Extract just the timestamps from the time series"""
        return [dp.timestamp for dp in self.data]
    
    @property
    def length(self) -> int:
        """Get the length of the time series"""
        return len(self.data)
    
    def get_values_array(self) -> np.ndarray:
        """Get values as numpy array for ML operations"""
        return np.array(self.values)
    
    def get_timestamps_array(self) -> np.ndarray:
        """Get timestamps as numpy array"""
        return np.array(self.timestamps)
    
    def validate_for_training(self, min_points: int = 2) -> None:
        """Validate if time series is suitable for training"""
        if self.length < min_points:
            raise ValueError(f"Insufficient training data (minimum {min_points} points required, got {self.length})")
        
        # Check for constant values
        unique_values = set(self.values)
        if len(unique_values) == 1:
            raise ValueError("Constant values detected - cannot train model")
    
    def get_statistics(self) -> dict:
        """Get basic statistics of the time series"""
        values_array = self.get_values_array()
        return {
            "count": self.length,
            "mean": float(np.mean(values_array)),
            "std": float(np.std(values_array)),
            "min": float(np.min(values_array)),
            "max": float(np.max(values_array)),
            "start_time": self.timestamps[0],
            "end_time": self.timestamps[-1]
        }