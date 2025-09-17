from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class BaseAPIModel(BaseModel):
    """Base model for all API interactions"""
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True
    )

class BaseRequestModel(BaseAPIModel):
    """Base for all API requests"""
    def validate_common_constraints(self) -> None:
        """Override in subclasses for common validation logic"""
        pass

class BaseResponseModel(BaseAPIModel):
    """Base for all API responses"""
    timestamp: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()), description="Unix timestamp")
    
class BaseMLRequestModel(BaseRequestModel):
    """Base for ML-related requests"""
    pass

class BaseMLResponseModel(BaseResponseModel):
    """Base for ML-related responses"""
    model_version: str = Field(..., description="Version of the trained model")
    
class BaseErrorModel(BaseAPIModel):
    """Base for error responses"""
    detail: str = Field(..., description="Error description")
    error_type: Optional[str] = Field(None, description="Type of error")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional error context")