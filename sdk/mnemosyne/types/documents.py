"""Type definitions for Documents API"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID


class DocumentCreate(BaseModel):
    """Schema for creating a document (used with multipart form data)"""

    collection_id: UUID = Field(..., description="Collection ID")
    title: Optional[str] = Field(None, max_length=512, description="Document title")
    filename: Optional[str] = Field(None, max_length=512, description="Original filename")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Flexible metadata")


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata (all fields optional)"""

    title: Optional[str] = Field(None, max_length=512)
    metadata: Optional[Dict] = None


class DocumentResponse(BaseModel):
    """Schema for document responses"""

    id: UUID
    collection_id: UUID
    user_id: UUID
    title: Optional[str]
    filename: Optional[str]
    content_type: Optional[str] = Field(None, description="MIME type")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")
    content_hash: str = Field(..., description="SHA-256 hash of content")
    unique_identifier_hash: Optional[str] = Field(None, description="Hash of source identifier")
    status: str = Field(..., description="Processing status")
    metadata: Dict = Field(default_factory=dict, alias="metadata_")
    processing_info: Optional[Dict] = Field(default_factory=dict, description="Processing details")
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentListResponse(BaseModel):
    """Schema for paginated list of documents"""

    data: list[DocumentResponse]
    pagination: Dict = Field(
        description="Pagination info",
        example={
            "total": 500,
            "limit": 20,
            "offset": 0,
            "has_more": True,
        },
    )


class DocumentStatusResponse(BaseModel):
    """Schema for document processing status"""

    document_id: UUID
    status: str = Field(..., description="Processing status (pending, processing, completed, failed)")
    chunk_count: int = Field(default=0, description="Number of chunks created")
    total_tokens: int = Field(default=0, description="Total tokens processed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_info: Dict = Field(default_factory=dict, description="Processing details")
    created_at: datetime
    processed_at: Optional[datetime] = Field(None, description="Timestamp when processing completed")

    class Config:
        from_attributes = True
