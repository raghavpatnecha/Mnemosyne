"""
Pydantic Schemas for Request/Response Validation

Collection Schemas:
    - CollectionBase: Base fields
    - CollectionCreate: POST /collections
    - CollectionUpdate: PATCH /collections/{id}
    - CollectionResponse: Single collection response
    - CollectionListResponse: List with pagination

Document Schemas:
    - DocumentBase: Base fields
    - DocumentCreate: POST /documents (with collection_id)
    - DocumentUpdate: PATCH /documents/{id}
    - DocumentResponse: Single document response
    - DocumentListResponse: List with pagination
"""

from backend.schemas.collection import (
    CollectionBase,
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse,
)

from backend.schemas.document import (
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
)

__all__ = [
    # Collection schemas
    "CollectionBase",
    "CollectionCreate",
    "CollectionUpdate",
    "CollectionResponse",
    "CollectionListResponse",
    # Document schemas
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentListResponse",
]
