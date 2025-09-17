from pydantic import Field
from typing import Optional
from ..core.base_models import BaseAPIModel, BaseResponseModel

class HealthMetrics(BaseAPIModel):
    """Performance metrics for health monitoring"""
    avg: Optional[float] = Field(None, description="Average response time")
    p95: Optional[float] = Field(None, description="95th percentile response time")
    p99: Optional[float] = Field(None, description="99th percentile response time")
    count: Optional[int] = Field(None, description="Number of requests measured")

class SystemHealthResponse(BaseResponseModel):
    """Comprehensive system health response"""
    status: str = Field(..., description="Overall system status")
    series_trained: int = Field(..., description="Number of trained series")
    inference_latency_ms: HealthMetrics = Field(..., description="Inference performance metrics")
    training_latency_ms: HealthMetrics = Field(..., description="Training performance metrics")
    system_resources: Optional[dict] = Field(None, description="System resource usage")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "series_trained": 15,
                "inference_latency_ms": {"avg": 45.2, "p95": 87.1, "p99": 120.5, "count": 1000},
                "training_latency_ms": {"avg": 234.7, "p95": 456.2, "p99": 678.9, "count": 25},
                "system_resources": {"cpu_usage": 45.2, "memory_usage": 67.8},
                "timestamp": "2024-01-01T12:00:00Z",
                "model_version": "v1"
            }
        }

# Backwards compatibility alias
HealthCheckResponse = SystemHealthResponse