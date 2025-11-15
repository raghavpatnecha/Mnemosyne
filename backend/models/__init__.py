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
    - ChatSession: Conversation sessions with RAG
    - ChatMessage: Individual messages in conversations

Relationships:
    User 1:N APIKey
    User 1:N Collection
    User 1:N ChatSession
    Collection 1:N Document
    Document 1:N DocumentChunk
    ChatSession 1:N ChatMessage

Cascade Deletes:
    - Delete User → Delete all APIKeys, Collections, Documents, Chunks, ChatSessions
    - Delete Collection → Delete all Documents, Chunks
    - Delete Document → Delete all Chunks
    - Delete ChatSession → Delete all ChatMessages
"""

from backend.models.user import User
from backend.models.api_key import APIKey
from backend.models.collection import Collection
from backend.models.document import Document
from backend.models.chunk import DocumentChunk
from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage

__all__ = ["User", "APIKey", "Collection", "Document", "DocumentChunk", "ChatSession", "ChatMessage"]
