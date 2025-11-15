"""
API Key Model - API authentication tokens
"""

from sqlalchemy import Column, String, ARRAY, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class APIKey(Base):
    """
    API Key model for token-based authentication

    Attributes:
        id: Unique key identifier (UUID)
        user_id: Foreign key to users table
        key_hash: SHA-256 hash of the API key (for verification)
        key_prefix: First 10 chars of key (for identification, e.g., "mn_test_ab")
        name: Human-readable name for the key
        scopes: List of permission scopes
        expires_at: Optional expiration timestamp
        last_used_at: Last time key was used for authentication
        created_at: Key creation timestamp

    Relationships:
        user: Owner of this API key (many-to-one)

    Security:
        - API key is hashed with SHA-256 before storage
        - Original key is only shown once upon creation
        - key_prefix allows user to identify keys without exposing full value
    """

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)
    name = Column(String(255))
    scopes = Column(ARRAY(String), default=list)

    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, prefix={self.key_prefix}, user_id={self.user_id})>"
