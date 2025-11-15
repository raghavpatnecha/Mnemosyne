"""
API Routes and Endpoints

Routers:
    - auth: Authentication (register, API keys)
    - collections: Collection CRUD
    - documents: Document CRUD
    - retrievals: Semantic search and retrieval
"""

from backend.api import auth, collections, documents, retrievals

__all__ = ["auth", "collections", "documents", "retrievals"]
