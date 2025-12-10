"""
DocumentChunk Model - Text chunks with embeddings for vector search

Search Architecture:
- embedding: Vector column for semantic search (pgvector cosine similarity)
- search_content: Normalized text for full-text search (slashes/hyphens → spaces)
- search_vector: Pre-computed tsvector for fast indexed FTS
- GIN index on search_vector for O(log n) lookups
- pg_trgm index on search_content for fuzzy/partial matching
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableDict
from pgvector.sqlalchemy import Vector
import uuid
import re

from backend.database import Base


def normalize_for_search(text: str) -> str:
    """
    Normalize text for full-text search indexing.

    Transforms compound terms so each component is searchable:
    - "Myndro/Moodahead" → "Myndro Moodahead"
    - "React-Native" → "React Native"
    - "AWS_Lambda" → "AWS Lambda"

    This is applied at INDEX TIME, not query time, following
    the standard RAG practice of normalizing during ingestion.

    Args:
        text: Raw text content

    Returns:
        Normalized text suitable for tsvector indexing
    """
    # Replace compound separators with spaces
    normalized = re.sub(r'[/\-_]', ' ', text)
    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


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

    # Search-optimized content (normalized at index time)
    # Compound terms like "Myndro/Moodahead" become "Myndro Moodahead"
    # This column is used for full-text search instead of raw content
    search_content = Column(Text, nullable=True)

    # Pre-computed tsvector for fast full-text search
    # Generated from search_content, indexed with GIN
    search_vector = Column(TSVECTOR, nullable=True)

    # Vector embedding (1536 dimensions for text-embedding-3-large)
    embedding = Column(Vector(1536), nullable=False)

    # Metadata (MutableDict tracks in-place JSON changes)
    metadata_ = Column("metadata", MutableDict.as_mutable(JSON), default=dict)  # metadata is reserved by SQLAlchemy
    chunk_metadata = Column(MutableDict.as_mutable(JSON), default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indexes for full-text search (created via migration)
    # GIN index on search_vector for O(log n) FTS lookups
    # pg_trgm GIN index on search_content for fuzzy matching
    __table_args__ = (
        Index('idx_chunk_search_vector', 'search_vector', postgresql_using='gin'),
    )

    # Relationships
    document = relationship("Document", back_populates="chunks")
    collection = relationship("Collection")
    user = relationship("User")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
