#!/usr/bin/env python3
"""
Database initialization script - Direct table creation
Forget Alembic, let's just create the damn tables directly!
"""
import sys
import os
import time
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add shared path for imports
sys.path.append('/app/shared')
sys.path.append('/app')

def wait_for_database():
    """Wait for PostgreSQL to be ready"""
    try:
        import psycopg2
        from psycopg2 import OperationalError
    except ImportError:
        logger.error("psycopg2 not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        import psycopg2
        from psycopg2 import OperationalError
    
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'database'),
                port=os.getenv('DB_PORT', '5432'),
                user=os.getenv('DB_USER', 'anomaly_user'),
                password=os.getenv('DB_PASSWORD', 'test_password'),
                database=os.getenv('DB_NAME', 'anomaly_detection')
            )
            conn.close()
            logger.info("✅ Database is ready!")
            return True
        except OperationalError as e:
            retry_count += 1
            logger.info(f"⏳ Waiting for database... (attempt {retry_count}/{max_retries}) - {e}")
            time.sleep(2)
    
    logger.error("❌ Database not ready after maximum retries")
    return False

def setup_alembic_config():
    """Set up Alembic configuration"""
    # Set environment variable for database URL
    if not os.getenv('DATABASE_URL'):
        db_host = os.getenv('DB_HOST', 'database')
        db_port = os.getenv('DB_PORT', '5432')
        db_user = os.getenv('DB_USER', 'anomaly_user')
        db_password = os.getenv('DB_PASSWORD', 'test_password')
        db_name = os.getenv('DB_NAME', 'anomaly_detection')
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        os.environ['DATABASE_URL'] = database_url
        logger.info(f"Set DATABASE_URL: {database_url}")

def create_tables_directly():
    """Create tables directly using SQLAlchemy"""
    try:
        logger.info("🔨 Creating tables directly with SQLAlchemy...")
        
        # Import SQLAlchemy models
        from shared.database.database import engine, Base
        from shared.database.models import TrainedModel, PredictionLog, TrainingData
        
        # Drop all existing tables first (clean slate)
        logger.info("🗑️  Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        
        # Create all tables from models
        logger.info("🏗️  Creating tables from SQLAlchemy models...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ All tables created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

def verify_tables():
    """Verify that tables were created correctly"""
    try:
        from shared.database.database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        actual_tables = inspector.get_table_names()
        
        expected_tables = ['trained_models', 'prediction_logs', 'training_data']
        
        logger.info(f"🔍 Tables found in database: {actual_tables}")
        
        for table in expected_tables:
            if table in actual_tables:
                logger.info(f"  ✅ {table}")
            else:
                logger.warning(f"  ⚠️  {table} (missing)")
        
        return len(actual_tables) > 0
        
    except Exception as e:
        logger.error(f"❌ Error verifying tables: {str(e)}")
        return False

def main():
    """Main initialization function"""
    logger.info("🚀 Starting database initialization - DIRECT TABLE CREATION!")
    
    # Wait for database to be ready
    if not wait_for_database():
        sys.exit(1)
    
    # Set up database configuration
    setup_alembic_config()
    
    # Create tables directly
    if not create_tables_directly():
        sys.exit(1)
    
    # Verify tables were created
    if not verify_tables():
        logger.warning("⚠️  Some tables may be missing")
    
    logger.info("✅ Database initialization completed successfully!")

if __name__ == "__main__":
    main()
