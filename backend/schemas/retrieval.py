"""
Pydantic Schemas for Retrieval endpoints
Request/Response validation
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import UUID
from enum import Enum


class RetrievalMode(str, Enum):
    """Search mode"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class RetrievalRequest(BaseModel):
    """Request schema for retrieval endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    mode: RetrievalMode = Field(default=RetrievalMode.SEMANTIC, description="Search mode")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")
    collection_id: Optional[UUID] = Field(None, description="Filter by collection")
    rerank: bool = Field(default=False, description="Enable reranking (future)")
    metadata_filter: Optional[Dict] = Field(None, description="Metadata filters")


class DocumentInfo(BaseModel):
    """Document metadata in search results"""
    id: str
    title: Optional[str]
    filename: Optional[str]


class ChunkResult(BaseModel):
    """Single chunk result"""
    chunk_id: str
    content: str
    chunk_index: int
    score: float = Field(..., description="Relevance score (0-1)")
    metadata: Dict
    chunk_metadata: Dict
    document: DocumentInfo
    collection_id: str


class RetrievalResponse(BaseModel):
    """Response schema for retrieval endpoint"""
    results: List[ChunkResult]
    query: str
    mode: str
    total_results: int
