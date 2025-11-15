"""
SQLAlchemy Database Models

All models use UUID as primary key for better distribution and security.
All timestamps use server_default=func.now() for consistent timezone handling.

Models:
    - User: Authentication and user management
    - APIKey: API authentication tokens
    - Collection: Logical grouping of documents
    - Document: Uploaded files with metadata
    - DocumentChunk: Text chunks with vector embeddings

Relationships:
    User 1:N APIKey
    User 1:N Collection
    Collection 1:N Document
    Document 1:N DocumentChunk

Cascade Deletes:
    - Delete User → Delete all APIKeys, Collections, Documents, Chunks
    - Delete Collection → Delete all Documents, Chunks
    - Delete Document → Delete all Chunks
"""

from backend.models.user import User
from backend.models.api_key import APIKey
from backend.models.collection import Collection
from backend.models.document import Document
from backend.models.chunk import DocumentChunk

__all__ = ["User", "APIKey", "Collection", "Document", "DocumentChunk"]
