from pydantic import Field, ConfigDict
from typing import List
from ...core.base_models import BaseMLRequestModel, BaseMLResponseModel
from ...core.data_models import TimeSeries

class AnomalyTrainRequest(BaseMLRequestModel):
    """Training request for anomaly detection"""
    timestamps: List[int] = Field(..., description="Unix timestamps")
    values: List[float] = Field(..., description="Time series values")
    threshold: float = Field(default=3.0, description="Anomaly detection threshold (sigma)")
    
    def validate_common_constraints(self) -> None:
        """Validate training data constraints"""
        super().validate_common_constraints()
        
        if len(self.timestamps) != len(self.values):
            raise ValueError("Timestamps and values must have the same length")
        
        if len(self.timestamps) < 2:
            raise ValueError("Minimum 2 data points required for training")
        
        if self.threshold <= 0:
            raise ValueError("Threshold must be positive")
    
    def to_time_series(self) -> TimeSeries:
        """Convert request data to TimeSeries object"""
        return TimeSeries.from_lists(self.timestamps, self.values)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for model creation"""
        return {
            "timestamps": self.timestamps,
            "values": self.values
        }
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamps": [1694336400, 1694336460, 1694336520],
                "values": [42.5, 43.1, 41.8],
                "threshold": 3.0
            }
        }
    )

class AnomalyTrainResponse(BaseMLResponseModel):
    """Training response for anomaly detection"""
    series_id: str = Field(..., description="Identifier of the trained series")
    # model_version is inherited from BaseMLResponseModel
    points_used: int = Field(..., description="Number of data points used in training")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "series_id": "sensor_001",
                "version": "1.0",
                "points_used": 100,
                "timestamp": 1704110400,
                "version": "1.0"
            }
        }
    )

# Backwards compatibility aliases
TrainData = AnomalyTrainRequest
TrainResponse = AnomalyTrainResponse