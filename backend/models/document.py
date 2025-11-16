"""
Document Model - Uploaded files and their metadata
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from backend.database import Base


class Document(Base):
    """
    Document model - uploaded files with metadata

    Attributes:
        id: Unique document identifier (UUID)
        collection_id: Foreign key to collections table
        user_id: Foreign key to users table (for fast ownership checks)

        title: Document title (optional, defaults to filename)
        filename: Original filename
        content_type: MIME type (application/pdf, text/plain, etc.)
        size_bytes: File size in bytes

        content_hash: SHA-256 hash of file content (for deduplication)
        unique_identifier_hash: Hash of source identifier (URL, file path) for update detection

        status: Processing status (pending, processing, completed, failed)
        metadata: Flexible JSON metadata (author, tags, etc.)
        processing_info: Processing details (service used, time taken, etc.)

        created_at: Upload timestamp
        updated_at: Last modification timestamp

    Relationships:
        collection: Parent collection (many-to-one)
        user: Document owner (many-to-one)

    Week 1 Behavior:
        - status is always "pending" (no processing)
        - content_hash is calculated but no chunking/embedding yet
        - Week 2 will add processing pipeline

    Uniqueness:
        - content_hash is unique globally (prevents duplicate uploads)
        - unique_identifier_hash allows detecting re-uploads of same source

    Cascade Delete:
        - Deleting a collection deletes all its documents
        - Week 2+: Deleting a document deletes all its chunks
    """

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # File metadata
    title = Column(String(512))
    filename = Column(String(512))
    content_type = Column(String(255))
    size_bytes = Column(Integer)

    # Hashing for deduplication (from SurfSense pattern)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    unique_identifier_hash = Column(String(64), unique=True)

    # Processing status
    status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    metadata_ = Column("metadata", JSON, default=dict)  # metadata is reserved by SQLAlchemy
    processing_info = Column(JSON, default=dict)

    # Processing results (Week 2+)
    processed_at = Column(DateTime(timezone=True))
    chunk_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    error_message = Column(Text)

    # Hierarchical search (Phase 2)
    document_embedding = Column(Vector(1536), nullable=True)
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="documents")
    user = relationship("User")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
