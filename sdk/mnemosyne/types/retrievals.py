"""Type definitions for Retrievals API"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal
from uuid import UUID


# Retrieval modes supported by the API
RetrievalMode = Literal["semantic", "keyword", "hybrid", "hierarchical", "graph"]


class RetrievalRequest(BaseModel):
    """Request schema for retrieval endpoint"""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    mode: RetrievalMode = Field(default="hybrid", description="Retrieval mode")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    collection_id: Optional[UUID] = Field(None, description="Filter by collection ID")
    rerank: bool = Field(default=False, description="Enable reranking with configured reranker")
    enable_graph: bool = Field(
        default=False,
        description="Enhance results with LightRAG knowledge graph (adds relationships and context)"
    )
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
    mode: str
    results: list[ChunkResult]
    total_results: int
    graph_enhanced: bool = Field(
        default=False,
        description="Whether results were enhanced with knowledge graph"
    )
    graph_context: Optional[str] = Field(
        None,
        description="Additional context from knowledge graph (if graph enhancement enabled)"
    )
