"""
Pydantic Schemas for Document endpoints
Request/Response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID


class DocumentBase(BaseModel):
    """Base schema with common fields"""
    title: Optional[str] = Field(None, max_length=512, description="Document title")
    filename: Optional[str] = Field(None, max_length=512, description="Original filename")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Flexible metadata")


class DocumentCreate(DocumentBase):
    """Schema for creating a document (used with multipart form data)"""
    collection_id: UUID = Field(..., description="Collection ID")


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata (all fields optional)"""
    title: Optional[str] = Field(None, max_length=512)
    metadata: Optional[Dict] = None


class DocumentResponse(DocumentBase):
    """Schema for document responses"""
    id: UUID
    collection_id: UUID
    user_id: UUID
    content_type: Optional[str] = Field(None, description="MIME type")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")
    content_hash: str = Field(..., description="SHA-256 hash of content")
    unique_identifier_hash: Optional[str] = Field(None, description="Hash of source identifier")
    status: str = Field(..., description="Processing status")
    processing_info: Optional[Dict] = Field(default_factory=dict, description="Processing details")
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for paginated list of documents"""
    data: list[DocumentResponse]
    pagination: Dict = Field(
        description="Pagination info",
        example={
            "total": 500,
            "limit": 20,
            "offset": 0,
            "has_more": True
        }
    )
