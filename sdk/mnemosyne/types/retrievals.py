"""Type definitions for Retrievals API"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal
from uuid import UUID


# Retrieval modes supported by the API
RetrievalMode = Literal["semantic", "keyword", "hybrid", "hierarchical", "graph"]


class RetrievalRequest(BaseModel):
    """Request schema for retrieval endpoint"""

    query: str = Field(..., min_length=1, max_length=2000, description="Search query")
    mode: RetrievalMode = Field(default="hybrid", description="Retrieval mode")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    collection_id: Optional[UUID] = Field(None, description="Filter by collection ID")
    metadata_filter: Optional[Dict] = Field(None, description="Filter by document metadata")


class DocumentInfo(BaseModel):
    """Document information in chunk result"""

    id: str
    title: Optional[str]
    filename: Optional[str]
    metadata: Dict = Field(default_factory=dict)


class ChunkResult(BaseModel):
    """Individual chunk result from retrieval"""

    chunk_id: str
    content: str
    chunk_index: int
    score: float
    metadata: Dict = Field(default_factory=dict, description="Chunk metadata")
    chunk_metadata: Dict = Field(default_factory=dict, description="Additional chunk metadata")
    document: DocumentInfo
    collection_id: str


class RetrievalResponse(BaseModel):
    """Response schema for retrieval endpoint"""

    query: str
    mode: RetrievalMode
    results: list[ChunkResult]
    total_results: int
    processing_time_ms: float = Field(description="Query processing time in milliseconds")
