from pydantic import Field, ConfigDict
from ...core.base_models import BaseMLRequestModel, BaseMLResponseModel
from ...core.data_models import DataPoint

class AnomalyPredictRequest(BaseMLRequestModel):
    """Prediction request for anomaly detection"""
    timestamp: str = Field(..., description="Timestamp of the data point")
    value: float = Field(..., description="Value to check for anomaly")
    
    def validate_common_constraints(self) -> None:
        """Validate prediction data constraints"""
        super().validate_common_constraints()
        
        # Validate timestamp format
        try:
            int(self.timestamp)  # Validate it's a valid unix timestamp
        except ValueError:
            raise ValueError("Invalid timestamp format - must be unix timestamp")
    
    def to_data_point(self) -> DataPoint:
        """Convert request to DataPoint object"""
        return DataPoint(
            timestamp=int(self.timestamp),
            value=self.value
        )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "1694336580",
                "value": 45.2
            }
        }
    )

class AnomalyPredictResponse(BaseMLResponseModel):
    """Prediction response for anomaly detection"""
    anomaly: bool = Field(..., description="Whether the data point is an anomaly")
    model_version: str = Field(..., description="Version of the model used for prediction")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "anomaly": True,
                "model_version": "1.0",
                "timestamp": 1704110400,
                "version": "1.0"
            }
        }
    )

# Backwards compatibility aliases
PredictData = AnomalyPredictRequest
PredictResponse = AnomalyPredictResponse