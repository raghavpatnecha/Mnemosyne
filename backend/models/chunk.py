"""
DocumentChunk Model - Text chunks with embeddings for vector search
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from backend.database import Base


class DocumentChunk(Base):
    """
    Document chunk model - text segments with vector embeddings

    Attributes:
        id: Unique chunk identifier (UUID)
        document_id: Foreign key to documents table
        collection_id: Foreign key to collections table (for fast filtering)
        user_id: Foreign key to users table (for ownership checks)

        content: Chunk text content
        chunk_index: Sequential index within document (0-based)

        embedding: Vector embedding (1536 dimensions for text-embedding-3-large)

        metadata: General metadata (source, page, etc.)
        chunk_metadata: Chonkie-specific metadata (type, tokens, boundaries)

        created_at: Chunk creation timestamp

    Relationships:
        document: Parent document (many-to-one)
        collection: Parent collection (many-to-one)
        user: Chunk owner (many-to-one)

    Vector Search:
        - embedding column uses pgvector extension
        - Supports cosine similarity search
        - Index created via migration

    Uniqueness:
        - (document_id, chunk_index) is unique per document

    Cascade Delete:
        - Deleting a document deletes all its chunks
        - Deleting a collection deletes all its document chunks
    """

    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    # Vector embedding (1536 dimensions for text-embedding-3-large)
    embedding = Column(Vector(1536), nullable=False)

    # Metadata
    metadata = Column(JSON, default=dict)
    chunk_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")
    collection = relationship("Collection")
    user = relationship("User")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
