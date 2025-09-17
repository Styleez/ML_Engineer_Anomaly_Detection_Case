"""
Database configuration for different environments
"""
import os
from typing import Dict

class DatabaseConfig:
    """Database configuration class"""
    
    def __init__(self):
        self.configs = {
            "development": {
                "url": "postgresql://postgres:password@localhost:5432/anomaly_detection",
                "pool_size": 5,
                "max_overflow": 10,
                "echo": True
            },
            "production": {
                "url": os.getenv("DATABASE_URL", "postgresql://anomaly_user:password@10.0.2.10:5432/anomaly_detection"),
                "pool_size": int(os.getenv("DB_POOL_SIZE", 20)),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 40)),
                "pool_pre_ping": True,
                "pool_recycle": 3600,
                "echo": False
            },
            "test": {
                "url": os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/anomaly_detection_test"),
                "pool_size": 5,
                "max_overflow": 10,
                "echo": False
            }
        }
    
    def get_config(self, environment: str = None) -> Dict:
        """Get configuration for specific environment"""
        env = environment or os.getenv("ENVIRONMENT", "production")
        return self.configs.get(env, self.configs["production"])
    
    def get_database_url(self, environment: str = None) -> str:
        """Get database URL for specific environment"""
        config = self.get_config(environment)
        return config["url"]

# Global instance
db_config = DatabaseConfig()
