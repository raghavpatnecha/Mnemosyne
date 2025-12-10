"""Retrievals resource implementation"""

from typing import Optional, Dict, TYPE_CHECKING
from uuid import UUID
from ..types.retrievals import (
    RetrievalMode,
    RetrievalRequest,
    RetrievalResponse,
)

if TYPE_CHECKING:
    from ..client import Client
    from ..async_client import AsyncClient


class RetrievalsResource:
    """Synchronous Retrievals resource"""

    def __init__(self, client: "Client"):
        self._client = client

    def retrieve(
        self,
        query: str,
        mode: RetrievalMode = "hybrid",
        top_k: int = 10,
        collection_id: Optional[UUID] = None,
        document_type: Optional[str] = None,
        rerank: bool = False,
        enable_graph: bool = False,
        metadata_filter: Optional[Dict] = None,
    ) -> RetrievalResponse:
        """
        Retrieve relevant chunks using various search modes.

        Args:
            query: Search query (1-1000 characters)
            mode: Retrieval mode - semantic, keyword, hybrid, hierarchical, or graph
            top_k: Number of results to return (1-100, default: 10)
            collection_id: Filter by collection UUID
            document_type: Filter by document type (legal, academic, qa, table, book, email, manual, presentation, resume, general)
            rerank: Enable reranking with configured reranker (default: False)
            enable_graph: Enhance results with LightRAG knowledge graph (default: False)
                         Combines base retrieval with graph context for complex queries.
                         Improves accuracy by 35-80% for relationship-based questions.
            metadata_filter: Filter by document metadata

        Returns:
            RetrievalResponse: Search results with chunks, scores, and optional graph context

        Raises:
            ValidationError: Invalid query or parameters
            APIError: Search failed

        Example:
            ```python
            # Standard hybrid search
            results = client.retrievals.retrieve("What is RAG?", mode="hybrid")

            # Filter by document type
            results = client.retrievals.retrieve(
                "termination clause",
                mode="hybrid",
                document_type="legal"
            )

            # HybridRAG: Combine semantic search with knowledge graph
            results = client.retrievals.retrieve(
                "How do proteins interact with diseases?",
                mode="semantic",
                enable_graph=True
            )
            print(results.graph_context)  # Relationship insights
            ```
        """
        data = RetrievalRequest(
            query=query,
            mode=mode,
            top_k=top_k,
            collection_id=collection_id,
            document_type=document_type,
            rerank=rerank,
            enable_graph=enable_graph,
            metadata_filter=metadata_filter,
        ).model_dump(mode='json', exclude_unset=True)

        response = self._client.request("POST", "/retrievals", json=data)
        return RetrievalResponse(**response.json())


class AsyncRetrievalsResource:
    """Asynchronous Retrievals resource"""

    def __init__(self, client: "AsyncClient"):
        self._client = client

    async def retrieve(
        self,
        query: str,
        mode: RetrievalMode = "hybrid",
        top_k: int = 10,
        collection_id: Optional[UUID] = None,
        document_type: Optional[str] = None,
        rerank: bool = False,
        enable_graph: bool = False,
        metadata_filter: Optional[Dict] = None,
    ) -> RetrievalResponse:
        """
        Retrieve relevant chunks using various search modes (async).

        Args:
            query: Search query (1-1000 characters)
            mode: Retrieval mode - semantic, keyword, hybrid, hierarchical, or graph
            top_k: Number of results to return (1-100, default: 10)
            collection_id: Filter by collection UUID
            document_type: Filter by document type (legal, academic, qa, table, book, email, manual, presentation, resume, general)
            rerank: Enable reranking with configured reranker (default: False)
            enable_graph: Enhance results with LightRAG knowledge graph (default: False)
            metadata_filter: Filter by document metadata

        Returns:
            RetrievalResponse: Search results with chunks, scores, and optional graph context
        """
        data = RetrievalRequest(
            query=query,
            mode=mode,
            top_k=top_k,
            collection_id=collection_id,
            document_type=document_type,
            rerank=rerank,
            enable_graph=enable_graph,
            metadata_filter=metadata_filter,
        ).model_dump(mode='json', exclude_unset=True)

        response = await self._client.request("POST", "/retrievals", json=data)
        return RetrievalResponse(**response.json())
