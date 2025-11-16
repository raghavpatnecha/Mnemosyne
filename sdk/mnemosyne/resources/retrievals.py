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
        metadata_filter: Optional[Dict] = None,
    ) -> RetrievalResponse:
        """
        Retrieve relevant chunks using various search modes.

        Args:
            query: Search query (1-2000 characters)
            mode: Retrieval mode - semantic, keyword, hybrid, hierarchical, or graph
            top_k: Number of results to return (1-50, default: 10)
            collection_id: Filter by collection UUID
            metadata_filter: Filter by document metadata

        Returns:
            RetrievalResponse: Search results with chunks and scores

        Raises:
            ValidationError: Invalid query or parameters
            APIError: Search failed
        """
        data = RetrievalRequest(
            query=query,
            mode=mode,
            top_k=top_k,
            collection_id=collection_id,
            metadata_filter=metadata_filter,
        ).model_dump(exclude_unset=True)

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
        metadata_filter: Optional[Dict] = None,
    ) -> RetrievalResponse:
        """Retrieve relevant chunks using various search modes (async)"""
        data = RetrievalRequest(
            query=query,
            mode=mode,
            top_k=top_k,
            collection_id=collection_id,
            metadata_filter=metadata_filter,
        ).model_dump(exclude_unset=True)

        response = await self._client.request("POST", "/retrievals", json=data)
        return RetrievalResponse(**response.json())
