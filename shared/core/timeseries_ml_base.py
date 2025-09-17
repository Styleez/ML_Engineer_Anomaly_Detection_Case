"""
Base class specifically for ML models that work with TimeSeries data.
Provides TimeSeries-specific delegate pattern functionality.
"""
from typing import List, Optional
from .ml_base import BaseMLModel
from .data_models import TimeSeries

class TimeSeriesMLModel(BaseMLModel):
    """Base class for ML models that work with TimeSeries data"""
    
    def __init__(self):
        super().__init__()
        # TimeSeries-specific training data (typed)
        self._training_data: Optional[TimeSeries] = None
    
    def validate_training_data(self, data: TimeSeries) -> None:
        """Validate TimeSeries training data"""
        super().validate_training_data(data)
        
        if not isinstance(data, TimeSeries):
            raise ValueError("Data must be a TimeSeries object")
        
        # Use TimeSeries built-in validation with default minimum
        data.validate_for_training(min_points=2)
    
    # TimeSeries-specific delegate properties
    @property
    def training_values(self) -> List[float]:
        """Access training values directly"""
        if self._training_data is None:
            raise ValueError("Model not trained - no training data available")
        return self._training_data.values
    
    @property
    def training_timestamps(self) -> List[int]:
        """Access training timestamps directly"""
        if self._training_data is None:
            raise ValueError("Model not trained - no training data available")
        return self._training_data.timestamps
    
    @property
    def training_length(self) -> int:
        """Get number of training points"""
        if self._training_data is None:
            return 0
        return self._training_data.length
    
    @property
    def training_statistics(self) -> dict:
        """Get comprehensive training data statistics"""
        if self._training_data is None:
            return {}
        return self._training_data.get_statistics()
    
    def get_training_data_copy(self) -> TimeSeries:
        """Get a copy of the training data (TimeSeries-specific)"""
        if self._training_data is None:
            raise ValueError("Model not trained - no training data available")
        return self._training_data
    
    @classmethod
    def from_api_request(cls, request_data: dict, **model_kwargs):
        """Create model and TimeSeries from API request data - override in subclasses"""
        time_series = TimeSeries.from_lists(
            timestamps=request_data["timestamps"],
            values=request_data["values"]
        )
        
        model = cls(**model_kwargs)
        return model, time_series

