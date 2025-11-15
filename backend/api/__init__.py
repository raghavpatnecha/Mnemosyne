"""
API Routes and Endpoints

Routers:
    - auth: Authentication (register, API keys)
    - collections: Collection CRUD
    - documents: Document CRUD
"""

from backend.api import auth, collections, documents

__all__ = ["auth", "collections", "documents"]
