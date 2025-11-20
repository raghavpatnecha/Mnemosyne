"""
Database session management for Mnemosyne
SQLAlchemy setup with async support
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

# Create database engine
# pool_pre_ping: Verify connections before using them
# echo: Log all SQL statements when DEBUG=True
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI endpoints to get database session
    Automatically closes session after request

    Issue #4 & #14 fix: Added explicit rollback on exceptions
    to prevent dirty sessions and transaction pollution
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Rollback any pending transaction on error
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """
    Create all tables in the database
    Called during application startup

    Note: Import models here to ensure they're registered with Base.metadata
    """
    # Import models so they're registered with Base.metadata
    from backend.models import User, APIKey, Collection, Document  # noqa: F401

    Base.metadata.create_all(bind=engine)
