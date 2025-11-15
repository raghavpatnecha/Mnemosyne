"""
Pydantic Schemas for Chat endpoints
Request/Response validation
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime


class Message(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    session_id: Optional[UUID] = Field(None, description="Session ID (creates new if not provided)")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    collection_id: Optional[UUID] = Field(None, description="Filter retrieval by collection")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    stream: bool = Field(default=True, description="Enable streaming (SSE)")


class Source(BaseModel):
    """Source chunk information"""
    chunk_id: str
    content: str
    document: Dict
    score: float


class ChatResponse(BaseModel):
    """Response schema for chat endpoint (non-streaming)"""
    session_id: UUID
    message: str
    sources: List[Source]


class ChatSessionResponse(BaseModel):
    """Chat session metadata"""
    id: UUID
    user_id: UUID
    collection_id: Optional[UUID]
    title: Optional[str]
    created_at: datetime
    last_message_at: Optional[datetime]
    message_count: int

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
