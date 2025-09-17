"""
Dataset loader utility for loading and converting real dataset files to the format expected by our API
"""
import pandas as pd
import os
from datetime import datetime
from typing import List, Tuple, Dict, Any
from pathlib import Path

class DatasetLoader:
    """Utility class for loading and converting dataset files"""
    
    def __init__(self, dataset_dir: str = "dataset"):
        """Initialize with dataset directory path"""
        self.dataset_dir = Path(dataset_dir)
        if not self.dataset_dir.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent
            self.dataset_dir = project_root / dataset_dir
        
        if not self.dataset_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    
    @staticmethod
    def convert_timestamp_to_unix(timestamp_str: str) -> int:
        """Convert timestamp string to Unix timestamp
        
        Supports formats:
        - 2011-07-01 00:00:01
        - 2011-07-01T00:00:01
        - ISO format variations
        """
        try:
            # Try parsing with space separator first
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # Try with T separator
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                # Try pandas for more flexible parsing
                dt = pd.to_datetime(timestamp_str)
        
        return int(dt.timestamp())
    
    def load_csv_dataset(self, filename: str, limit: int = None) -> Dict[str, Any]:
        """Load CSV dataset and convert to API format
        
        Args:
            filename: Name of CSV file in dataset directory
            limit: Optional limit on number of records to load
            
        Returns:
            Dict with 'timestamps', 'values', and metadata
        """
        file_path = self.dataset_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        
        # Load CSV
        df = pd.read_csv(file_path)
        
        # Limit records if specified
        if limit:
            df = df.head(limit)
        
        # Convert timestamps to Unix format
        unix_timestamps = []
        for ts in df['timestamp']:
            unix_ts = self.convert_timestamp_to_unix(str(ts))
            unix_timestamps.append(unix_ts)
        
        # Extract values
        values = df['value'].tolist()
        
        return {
            "timestamps": unix_timestamps,
            "values": values,
            "threshold": 3.0,  # Default 3-sigma threshold
            "metadata": {
                "source_file": filename,
                "total_points": len(unix_timestamps),
                "time_range": {
                    "start": min(unix_timestamps),
                    "end": max(unix_timestamps)
                },
                "value_range": {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values)
                }
            }
        }
    
    def get_available_datasets(self) -> List[str]:
        """Get list of available CSV files in dataset directory"""
        csv_files = []
        for file_path in self.dataset_dir.glob("*.csv"):
            csv_files.append(file_path.name)
        return sorted(csv_files)
    
    def load_training_sample(self, filename: str, sample_size: int = 100) -> Dict[str, Any]:
        """Load a sample of data suitable for training
        
        Args:
            filename: CSV file to load
            sample_size: Number of data points to include
            
        Returns:
            Training data in API format
        """
        return self.load_csv_dataset(filename, limit=sample_size)
    
    def load_prediction_samples(self, filename: str, start_idx: int = 100, count: int = 10) -> List[Dict[str, Any]]:
        """Load samples for prediction testing
        
        Args:
            filename: CSV file to load
            start_idx: Starting index (after training data)
            count: Number of prediction samples
            
        Returns:
            List of prediction samples
        """
        file_path = self.dataset_dir / filename
        df = pd.read_csv(file_path)
        
        # Get prediction samples
        prediction_data = df.iloc[start_idx:start_idx + count]
        
        samples = []
        for _, row in prediction_data.iterrows():
            unix_ts = self.convert_timestamp_to_unix(str(row['timestamp']))
            samples.append({
                "timestamp": str(unix_ts),
                "value": float(row['value'])
            })
        
        return samples


# Pre-configured dataset configurations
DATASET_CONFIGS = {
    "ambient_temperature": {
        "file": "ambient_temperature_system_failure.csv",
        "description": "Ambient temperature with system failures",
        "training_size": 150,
        "prediction_samples": 20
    },
    "cpu_utilization": {
        "file": "cpu_utilization_asg_misconfiguration.csv", 
        "description": "CPU utilization with ASG misconfigurations",
        "training_size": 200,
        "prediction_samples": 15
    },
    "machine_temperature": {
        "file": "machine_temperature.csv",
        "description": "Machine temperature sensor data",
        "training_size": 500,
        "prediction_samples": 30
    },
    "synthetic_cpu": {
        "file": "synthetic_cpu_spikes.csv",
        "description": "Synthetic CPU spike anomalies",
        "training_size": 100,
        "prediction_samples": 25
    },
    "synthetic_temperature": {
        "file": "synthetic_temperature_anomalies.csv",
        "description": "Synthetic temperature anomalies",
        "training_size": 100,
        "prediction_samples": 25
    }
}


def get_dataset_config(dataset_name: str) -> Dict[str, Any]:
    """Get configuration for a specific dataset"""
    if dataset_name not in DATASET_CONFIGS:
        available = list(DATASET_CONFIGS.keys())
        raise ValueError(f"Unknown dataset: {dataset_name}. Available: {available}")
    
    return DATASET_CONFIGS[dataset_name]
