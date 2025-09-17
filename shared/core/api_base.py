"""
API base utilities and common patterns for the anomaly detection system.
"""
from typing import Type, TypeVar, Generic
from .base_models import BaseMLRequestModel, BaseMLResponseModel, BaseErrorModel

T = TypeVar('T', bound=BaseMLRequestModel)
R = TypeVar('R', bound=BaseMLResponseModel)

class APIEndpointBase(Generic[T, R]):
    """Base class for API endpoint patterns"""
    
    def __init__(self, request_model: Type[T], response_model: Type[R]):
        self.request_model = request_model
        self.response_model = response_model
    
    def validate_request(self, data: dict) -> T:
        """Validate and parse request data"""
        request = self.request_model(**data)
        request.validate_common_constraints()
        return request
    
    def create_response(self, **kwargs) -> R:
        """Create standardized response"""
        return self.response_model(**kwargs)
    
    def create_error_response(self, detail: str, error_type: str = None, **context) -> BaseErrorModel:
        """Create standardized error response"""
        return BaseErrorModel(
            detail=detail,
            error_type=error_type,
            context=context if context else None
        )
