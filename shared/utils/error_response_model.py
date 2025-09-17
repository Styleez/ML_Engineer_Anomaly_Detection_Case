from pydantic import Field
from typing import Optional, Dict, Any
from ...core.base_models import BaseErrorModel

class StandardErrorResponse(BaseErrorModel):
    """Standard error response extending base error model"""
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Insufficient training data (minimum 2 points)",
                "error_type": "validation_error",
                "context": {"min_points": 2, "provided_points": 1}
            }
        }

class ValidationErrorResponse(BaseErrorModel):
    """Validation-specific error response"""
    error_type: str = Field(default="validation_error", description="Error type")
    field_errors: Optional[Dict[str, str]] = Field(None, description="Field-specific errors")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Data validation failed",
                "error_type": "validation_error",
                "field_errors": {"timestamps": "Must be integers", "values": "Must be floats"},
                "context": {"invalid_fields": 2}
            }
        }

class ModelErrorResponse(BaseErrorModel):
    """ML model-specific error response"""
    error_type: str = Field(default="model_error", description="Error type")
    model_state: Optional[str] = Field(None, description="Current model state")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Model not trained - call fit() first",
                "error_type": "model_error",
                "model_state": "untrained",
                "context": {"required_action": "training"}
            }
        }

# Backwards compatibility alias
ErrorResponse = StandardErrorResponse