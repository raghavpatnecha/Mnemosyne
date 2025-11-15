"""
User Model - Authentication and user management
"""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class User(Base):
    """
    User model for authentication and API key ownership

    Attributes:
        id: Unique user identifier (UUID)
        email: User email (unique, indexed for fast lookup)
        hashed_password: Bcrypt hashed password
        is_active: Whether user can authenticate
        is_superuser: Admin privileges
        created_at: Account creation timestamp
        updated_at: Last modification timestamp

    Relationships:
        api_keys: User's API keys (one-to-many)
        collections: User's document collections (one-to-many)
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
