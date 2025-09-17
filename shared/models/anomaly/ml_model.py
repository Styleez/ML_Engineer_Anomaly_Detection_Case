import numpy as np
from typing import Optional
from ...core.data_models import TimeSeries, DataPoint
from ...core.timeseries_ml_base import TimeSeriesMLModel

class AnomalyDetectionModel(TimeSeriesMLModel):
    """3-sigma anomaly detection model using statistical thresholds"""
    
    def __init__(self, threshold: float = 3.0):
        super().__init__()
        self.threshold = threshold
        self.model_type = "anomaly_detection"
        
        # Anomaly-specific computed state
        self.mean: Optional[float] = None
        self.std: Optional[float] = None
    
    def fit(self, data: TimeSeries) -> "AnomalyDetectionModel":
        """Train the anomaly detection model with time series data"""
        self.validate_training_data(data)
        
        # Store training data (inherited from base class)
        self._store_training_data(data)
        
        # Anomaly-specific training logic
        values_array = data.get_values_array()
        
        self.mean = float(np.mean(values_array))
        self.std = float(np.std(values_array))

        # Additional validation: ensure std > 0
        if self.std == 0:
            raise ValueError("Standard deviation is zero - cannot detect anomalies")
        
        self._mark_as_trained()
        return self

    def predict(self, data_point: DataPoint) -> bool:
        """Predict if a data point is an anomaly using 3-sigma rule"""
        self.validate_model_trained()
        
        if not isinstance(data_point, DataPoint):
            raise ValueError("Data must be a DataPoint object")
        
        # 3-sigma anomaly detection
        return abs(data_point.value - self.mean) > self.threshold * self.std
    
    def predict_with_details(self, data_point: DataPoint) -> dict:
        """Predict with additional details for API responses"""
        self.validate_model_trained()
        
        if not isinstance(data_point, DataPoint):
            raise ValueError("Data must be a DataPoint object")
        
        deviation = abs(data_point.value - self.mean) / self.std
        is_anomaly = deviation > self.threshold
        
        return {
            "anomaly": is_anomaly,
            "deviation": deviation,
            "confidence": min(deviation / self.threshold, 1.0) if is_anomaly else 1.0,
            "threshold_used": self.threshold
        }
    
    def predict_time_series(self, data: TimeSeries) -> list[dict]:
        """Predict anomalies for an entire time series"""
        self.validate_model_trained()
        
        results = []
        for data_point in data.data:
            prediction = self.predict_with_details(data_point)
            results.append({
                "timestamp": data_point.timestamp,
                "value": data_point.value,
                **prediction
            })
        
        return results
    
    def get_model_stats(self) -> dict:
        """Get anomaly-specific model statistics"""
        if not self.is_trained:
            return {"model_type": self.model_type, "is_trained": False}
        
        base_stats = {
            "model_type": self.model_type,
            "mean": self.mean,
            "std": self.std,
            "threshold": self.threshold,
            "training_points": self.training_length,  # Inherited delegate property
            **self.get_model_info()  # Inherited method
        }
        
        # Include training data statistics using inherited delegate pattern
        base_stats["training_data"] = self.training_statistics
        
        return base_stats
    
    def retrain(self, threshold: Optional[float] = None) -> "AnomalyDetectionModel":
        """Retrain model with new threshold using stored training data"""
        if threshold is not None:
            self.threshold = threshold
        
        # Use inherited retrain method
        return super().retrain()
    
    @classmethod
    def from_api_request(cls, request_data: dict, threshold: float = 3.0):
        """Create model and TimeSeries from API request data"""
        return super().from_api_request(request_data, threshold=threshold)
