"""
API Routes and Endpoints

Routers:
    - auth: Authentication (register, API keys)
    - collections: Collection CRUD
    - documents: Document CRUD
    - retrievals: Semantic search and retrieval
    - chat: Conversational retrieval with RAG
"""

from backend.api import auth, collections, documents, retrievals, chat

__all__ = ["auth", "collections", "documents", "retrievals", "chat"]
