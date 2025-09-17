from pydantic import Field
from typing import List
from ...core.base_models import BaseAPIModel, BaseMLResponseModel

class PlotDataPoint(BaseAPIModel):
    """Data point for anomaly visualization"""
    timestamp: int = Field(..., description="Unix timestamp")
    value: float = Field(..., description="Data point value")
    is_anomaly: bool = Field(..., description="Whether this point is an anomaly")
    deviation: float = Field(default=0.0, description="Standard deviations from mean")

class AnomalyPlotResponse(BaseMLResponseModel):
    """Visualization response for anomaly detection"""
    series_id: str = Field(..., description="Series identifier")
    data_points: List[PlotDataPoint] = Field(..., description="Data points with anomaly flags")
    model_stats: dict = Field(..., description="Model statistics (mean, std, threshold)")
    summary: dict = Field(default_factory=dict, description="Summary statistics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "series_id": "sensor_001",
                "data_points": [
                    {"timestamp": 1694336400, "value": 42.5, "is_anomaly": False, "deviation": 0.2},
                    {"timestamp": 1694336460, "value": 50.1, "is_anomaly": True, "deviation": 3.2}
                ],
                "model_stats": {"mean": 42.1, "std": 1.5, "threshold": 3.0},
                "summary": {"total_points": 100, "anomalies_count": 5, "anomaly_rate": 0.05},
                "model_version": "v1",
                "timestamp": 1704110400
            }
        }

# Backwards compatibility alias
PlotResponse = AnomalyPlotResponse