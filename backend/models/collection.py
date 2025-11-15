"""
Collection Model - Logical grouping of documents
"""

from sqlalchemy import Column, String, Text, ForeignKey, JSON, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class Collection(Base):
    """
    Collection model - logical grouping of documents

    Attributes:
        id: Unique collection identifier (UUID)
        user_id: Foreign key to users table
        name: Collection name (unique per user)
        description: Optional description
        metadata: Flexible JSON metadata (tags, categories, etc.)
        config: Collection-specific configuration (chunk_size, embedding_model, etc.)
        created_at: Collection creation timestamp
        updated_at: Last modification timestamp

    Relationships:
        user: Owner of this collection (many-to-one)
        documents: Documents in this collection (one-to-many, cascade delete)

    Uniqueness:
        - (user_id, name) is unique - user cannot have duplicate collection names

    Cascade Delete:
        - Deleting a collection deletes all its documents
    """

    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_collection_name'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    metadata = Column(JSON, default=dict)
    config = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="collections")
    documents = relationship("Document", back_populates="collection", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Collection(id={self.id}, name={self.name}, user_id={self.user_id})>"
