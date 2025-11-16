"""Type definitions for Collections API"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID


class CollectionCreate(BaseModel):
    """Schema for creating a new collection"""

    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, description="Optional description")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Flexible metadata")
    config: Optional[Dict] = Field(default_factory=dict, description="Collection configuration")


class CollectionUpdate(BaseModel):
    """Schema for updating a collection (all fields optional)"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict] = None
    config: Optional[Dict] = None


class CollectionResponse(BaseModel):
    """Schema for collection responses"""

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    metadata: Dict = Field(default_factory=dict)
    config: Dict = Field(default_factory=dict)
    document_count: int = Field(default=0, description="Number of documents in collection")
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CollectionListResponse(BaseModel):
    """Schema for paginated list of collections"""

    data: list[CollectionResponse]
    pagination: Dict = Field(
        description="Pagination info",
        example={
            "total": 100,
            "limit": 20,
            "offset": 0,
            "has_more": True,
        },
    )
