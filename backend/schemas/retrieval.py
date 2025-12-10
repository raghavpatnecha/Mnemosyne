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
    GRAPH = "graph"  # LightRAG graph-based retrieval


class RetrievalRequest(BaseModel):
    """Request schema for retrieval endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    mode: RetrievalMode = Field(default=RetrievalMode.HYBRID, description="Search mode")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")
    collection_id: Optional[UUID] = Field(None, description="Filter by collection")
    document_type: Optional[str] = Field(
        None,
        description="Filter by document type (legal, academic, qa, table, book, email, manual, presentation, resume, general). "
        "Returns only chunks from documents processed with the specified domain processor."
    )
    rerank: bool = Field(default=True, description="Enable reranking with configured reranker")
    enable_graph: bool = Field(
        default=True,
        description="Enhance results with LightRAG knowledge graph (adds relationships and context)"
    )
    hierarchical: bool = Field(
        default=True,
        description="Enable two-tier hierarchical search (document-level first, then chunk-level within top documents)"
    )
    expand_context: bool = Field(
        default=True,
        description="Expand results with surrounding chunks for richer context (sentence window retrieval)"
    )
    metadata_filter: Optional[Dict] = Field(None, description="Metadata filters")


class DocumentInfo(BaseModel):
    """Document metadata in search results"""
    id: str
    title: Optional[str]
    filename: Optional[str]


class ContextWindow(BaseModel):
    """Context window metadata for expanded chunks"""
    original_index: int
    start_index: int
    end_index: int
    chunks_merged: int


class ChunkResult(BaseModel):
    """Single chunk result"""
    chunk_id: str
    content: str
    chunk_index: int
    score: float = Field(..., description="Relevance score (0-1)")
    rerank_score: Optional[float] = Field(
        None,
        description="Cross-encoder reranking score (0-1), higher is more relevant"
    )
    metadata: Dict
    chunk_metadata: Dict
    document: DocumentInfo
    collection_id: str
    expanded_content: Optional[str] = Field(
        None,
        description="Content with surrounding chunks merged for richer context"
    )
    context_window: Optional[ContextWindow] = Field(
        None,
        description="Metadata about the context window expansion"
    )


class GraphReference(BaseModel):
    """Reference from LightRAG knowledge graph"""
    reference_id: Optional[str] = Field(None, description="Reference identifier")
    file_path: Optional[str] = Field(None, description="Source file path")
    content: Optional[str] = Field(None, description="Referenced content snippet")


class RetrievalResponse(BaseModel):
    """Response schema for retrieval endpoint"""
    results: List[ChunkResult]
    query: str
    mode: str
    total_results: int
    graph_enhanced: bool = Field(
        default=False,
        description="Whether results were enhanced with knowledge graph"
    )
    graph_context: Optional[str] = Field(
        None,
        description="Additional context from knowledge graph (if graph enhancement enabled)"
    )
    graph_references: List[GraphReference] = Field(
        default_factory=list,
        description="Source references from knowledge graph"
    )
