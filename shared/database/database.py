"""
Centralized database connection and configuration
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
from typing import Generator
from .config import db_config

# Get database configuration
config = db_config.get_config()

# SQLAlchemy Setup
engine = create_engine(
    config["url"],
    pool_pre_ping=True,
    pool_size=config["pool_size"],
    max_overflow=config["max_overflow"],
    echo=config["echo"]
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_database():
    """Initialize database - create tables"""
    Base.metadata.create_all(bind=engine)

def close_database():
    """Close database connections"""
    engine.dispose()
