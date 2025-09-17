from abc import ABC, abstractmethod
from typing import Any, Self, Optional, Union
from datetime import datetime, timezone

class BaseMLModel(ABC):
    """Base class for all ML algorithms with delegate pattern support"""
    
    def __init__(self):
        self.is_trained: bool = False
        self.training_timestamp: Optional[datetime] = None
        self.model_version: str = "v1"
        
        # Store training data for delegate pattern (generic)
        self._training_data: Optional[Any] = None
    
    @abstractmethod
    def fit(self, data: Any) -> Self:
        """Train the model with provided data"""
        pass
    
    @abstractmethod
    def predict(self, data: Any) -> Any:
        """Make predictions using the trained model"""
        pass
    
    @abstractmethod
    def get_model_stats(self) -> dict:
        """Get model-specific statistics - implement in subclasses"""
        pass
    
    def validate_training_data(self, data: Any) -> None:
        """Common training data validations - override in subclasses"""
        if data is None:
            raise ValueError("Training data cannot be None")
    
    def validate_model_trained(self) -> None:
        """Validate that model is trained before prediction"""
        if not self.is_trained:
            raise ValueError("Model not trained - call fit() first")
    
    def _mark_as_trained(self) -> None:
        """Mark model as trained and set timestamp"""
        self.is_trained = True
        self.training_timestamp = datetime.now(timezone.utc)
    
    def _store_training_data(self, data: Any) -> None:
        """Store training data for delegate pattern - call in fit()"""
        self._training_data = data
    
    def get_model_info(self) -> dict:
        """Get model metadata"""
        return {
            "is_trained": self.is_trained,
            "training_timestamp": int(self.training_timestamp.timestamp()) if self.training_timestamp else None,
            "model_version": self.model_version
        }
    
    def has_training_data(self) -> bool:
        """Check if training data is stored"""
        return self._training_data is not None
    
    def get_training_data_copy(self) -> Any:
        """Get a copy of the training data (generic)"""
        if self._training_data is None:
            raise ValueError("Model not trained - no training data available")
        return self._training_data
    
    # Abstract methods for model-specific retraining
    def can_retrain(self) -> bool:
        """Check if model supports retraining with stored data"""
        return self.has_training_data()
    
    def retrain(self, **kwargs) -> Self:
        """Retrain model with stored data and new parameters - override in subclasses"""
        if not self.has_training_data():
            raise ValueError("No training data available for retraining")
        return self.fit(self._training_data)
