#!/usr/bin/env python3
"""
Simple script to run database migrations
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database.database import engine, Base

def run_migrations():
    """Run database migrations by creating all tables"""
    try:
        print("🔄 Running database migrations...")
        
        # Import all models to ensure they're registered
        from shared.database.models import TrainedModel, PredictionLog, TrainingData
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database migrations completed successfully!")
        print(f"📊 Database URL: {engine.url}")
        
        # Show created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
