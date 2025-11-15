"""
Pydantic Schemas for Collection endpoints
Request/Response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID


class CollectionBase(BaseModel):
    """Base schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, description="Optional description")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Flexible metadata")
    config: Optional[Dict] = Field(default_factory=dict, description="Collection configuration")


class CollectionCreate(CollectionBase):
    """Schema for creating a new collection"""
    pass


class CollectionUpdate(BaseModel):
    """Schema for updating a collection (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict] = None
    config: Optional[Dict] = None


class CollectionResponse(CollectionBase):
    """Schema for collection responses"""
    id: UUID
    user_id: UUID
    document_count: int = Field(default=0, description="Number of documents in collection")
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True  # Allow ORM mode (was orm_mode in Pydantic v1)


class CollectionListResponse(BaseModel):
    """Schema for paginated list of collections"""
    data: list[CollectionResponse]
    pagination: Dict = Field(
        description="Pagination info",
        example={
            "total": 100,
            "limit": 20,
            "offset": 0,
            "has_more": True
        }
    )
