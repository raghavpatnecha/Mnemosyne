"""
SQLAlchemy Database Models

All models use UUID as primary key for better distribution and security.
All timestamps use server_default=func.now() for consistent timezone handling.

Models:
    - User: Authentication and user management
    - APIKey: API authentication tokens
    - Collection: Logical grouping of documents
    - Document: Uploaded files with metadata

Relationships:
    User 1:N APIKey
    User 1:N Collection
    Collection 1:N Document

Cascade Deletes:
    - Delete User → Delete all APIKeys, Collections, Documents
    - Delete Collection → Delete all Documents
"""

from backend.models.user import User
from backend.models.api_key import APIKey
from backend.models.collection import Collection
from backend.models.document import Document

__all__ = ["User", "APIKey", "Collection", "Document"]
