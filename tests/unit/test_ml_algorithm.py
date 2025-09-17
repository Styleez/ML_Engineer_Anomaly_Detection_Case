"""
Unit tests for ML Algorithm (Anomaly Detection)
"""
import pytest
import numpy as np
from shared.models.anomaly.ml_model import AnomalyDetectionModel
from shared.core.data_models import TimeSeries
import time

class TestAnomalyDetectionModel:
    """Tests for AnomalyDetectionModel"""
    
    def test_model_training_normal_data(self):
        """Test model training with normal data"""
        # Create sample time series
        timestamps = [int(time.time()) - 100 + i for i in range(10)]
        values = [42.0 + i * 0.1 for i in range(10)]
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel(threshold=3.0)
        model.fit(ts)
        
        assert model.is_trained
        assert model.mean is not None
        assert model.std is not None
        assert model.threshold == 3.0
    
    def test_prediction_normal_value(self):
        """Test prediction for normal value"""
        # Train model
        timestamps = [int(time.time()) - 100 + i for i in range(20)]
        values = [42.0 + np.random.normal(0, 0.5) for _ in range(20)]
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel(threshold=3.0)
        model.fit(ts)
        
        # Test normal value - convert to DataPoint
        from shared.core.data_models import DataPoint
        normal_point = DataPoint(timestamp=int(time.time()), value=42.1)
        prediction = model.predict_with_details(normal_point)
        
        assert not prediction["anomaly"]
        assert "deviation" in prediction
        assert "threshold_used" in prediction
        assert "confidence" in prediction
    
    def test_prediction_anomaly_value(self):
        """Test prediction for anomalous value"""
        # Train model with varied data (not constant)
        timestamps = [int(time.time()) - 100 + i for i in range(20)]
        values = [42.0 + i * 0.1 for i in range(20)]  # Slightly varying values
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel(threshold=2.0)
        model.fit(ts)
        
        # Test anomalous value (far from mean)
        from shared.core.data_models import DataPoint
        anomaly_point = DataPoint(timestamp=int(time.time()), value=100.0)
        prediction = model.predict_with_details(anomaly_point)
        
        assert prediction["anomaly"]
        assert abs(prediction["deviation"]) > 2.0
    
    def test_model_serialization(self):
        """Test model statistics retrieval"""
        timestamps = [int(time.time()) - 100 + i for i in range(10)]
        values = [42.0 + i * 0.1 for i in range(10)]
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel(threshold=3.0)
        model.fit(ts)
        
        stats = model.get_model_stats()
        
        assert "model_version" in stats
        assert "mean" in stats
        assert "std" in stats
        assert "threshold" in stats
        assert "training_points" in stats

class TestDataValidation:
    """Tests for data validation"""
    
    def test_valid_data(self):
        """Test with valid time series data"""
        timestamps = [1700000000, 1700000060, 1700000120]
        values = [42.1, 42.3, 41.9]
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel()
        model.fit(ts)
        
        assert model.is_trained
    
    def test_insufficient_data(self):
        """Test with insufficient data points"""
        timestamps = [1700000000]
        values = [42.1]
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel()
        
        with pytest.raises(ValueError):
            model.fit(ts)
    
    def test_constant_values(self):
        """Test with constant values (zero variance)"""
        timestamps = [1700000000, 1700000060, 1700000120]
        values = [42.0, 42.0, 42.0]
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel()
        
        with pytest.raises(ValueError):
            model.fit(ts)
    
    def test_mismatched_lengths(self):
        """Test TimeSeries creation with invalid data"""
        with pytest.raises(ValueError):
            # This should fail during TimeSeries validation
            TimeSeries(data=[
                {"timestamp": 1700000000, "value": 42.1},
                {"timestamp": 1700000060}  # Missing value
            ])
    
    def test_invalid_values(self):
        """Test with invalid values"""
        with pytest.raises(ValueError):
            TimeSeries(data=[
                {"timestamp": 1700000000, "value": "not_a_number"},
                {"timestamp": 1700000060, "value": 42.3}
            ])

class TestPerformance:
    """Performance tests"""
    
    def test_training_speed(self):
        """Test training performance"""
        # Generate larger dataset
        timestamps = [int(time.time()) - 1000 + i for i in range(1000)]
        values = [42.0 + np.random.normal(0, 2) for _ in range(1000)]
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel()
        
        start_time = time.time()
        model.fit(ts)
        training_time = time.time() - start_time
        
        # Training should be fast (< 1 second for 1000 points)
        assert training_time < 1.0
        assert model.is_trained
    
    def test_prediction_speed(self):
        """Test prediction performance"""
        # Train model
        timestamps = [int(time.time()) - 100 + i for i in range(100)]
        values = [42.0 + np.random.normal(0, 1) for _ in range(100)]
        
        ts = TimeSeries(data=[{"timestamp": t, "value": v} for t, v in zip(timestamps, values)])
        
        model = AnomalyDetectionModel()
        model.fit(ts)
        
        # Test prediction speed
        from shared.core.data_models import DataPoint
        test_point = DataPoint(timestamp=int(time.time()), value=42.5)
        
        start_time = time.time()
        for _ in range(100):
            model.predict_with_details(test_point)
        prediction_time = time.time() - start_time
        
        # 100 predictions should be very fast (< 0.1 seconds)
        assert prediction_time < 0.1