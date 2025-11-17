"""Collections resource implementation"""

from typing import Optional, Dict, TYPE_CHECKING
from uuid import UUID
from ..types.collections import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse,
)

if TYPE_CHECKING:
    from ..client import Client
    from ..async_client import AsyncClient


class CollectionsResource:
    """Synchronous Collections resource"""

    def __init__(self, client: "Client"):
        self._client = client

    def create(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        config: Optional[Dict] = None,
    ) -> CollectionResponse:
        """
        Create a new collection.

        Args:
            name: Collection name (1-255 characters)
            description: Optional description
            metadata: Optional metadata dictionary
            config: Optional configuration dictionary

        Returns:
            CollectionResponse: Created collection with ID and timestamps

        Raises:
            AuthenticationError: Invalid API key
            ValidationError: Invalid parameters
            APIError: Server error
        """
        data = CollectionCreate(
            name=name,
            description=description,
            metadata=metadata or {},
            config=config or {},
        ).model_dump(exclude_unset=True)

        response = self._client.request("POST", "/collections", json=data)
        return CollectionResponse(**response.json())

    def list(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> CollectionListResponse:
        """
        List collections with pagination.

        Args:
            limit: Number of results per page (1-100, default: 20)
            offset: Number of results to skip (default: 0)

        Returns:
            CollectionListResponse: List of collections with pagination info
        """
        params = {"limit": limit, "offset": offset}
        response = self._client.request("GET", "/collections", params=params)
        return CollectionListResponse(**response.json())

    def get(self, collection_id: UUID) -> CollectionResponse:
        """
        Get a collection by ID.

        Args:
            collection_id: Collection UUID

        Returns:
            CollectionResponse: Collection details

        Raises:
            NotFoundError: Collection not found
        """
        response = self._client.request("GET", f"/collections/{collection_id}")
        return CollectionResponse(**response.json())

    def update(
        self,
        collection_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        config: Optional[Dict] = None,
    ) -> CollectionResponse:
        """
        Update a collection.

        Args:
            collection_id: Collection UUID
            name: New collection name
            description: New description
            metadata: New metadata
            config: New configuration

        Returns:
            CollectionResponse: Updated collection

        Raises:
            NotFoundError: Collection not found
            ValidationError: Invalid parameters
        """
        data = CollectionUpdate(
            name=name,
            description=description,
            metadata=metadata,
            config=config,
        ).model_dump(exclude_unset=True)

        response = self._client.request("PATCH", f"/collections/{collection_id}", json=data)
        return CollectionResponse(**response.json())

    def delete(self, collection_id: UUID) -> None:
        """
        Delete a collection.

        Args:
            collection_id: Collection UUID

        Raises:
            NotFoundError: Collection not found
        """
        self._client.request("DELETE", f"/collections/{collection_id}")


class AsyncCollectionsResource:
    """Asynchronous Collections resource"""

    def __init__(self, client: "AsyncClient"):
        self._client = client

    async def create(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        config: Optional[Dict] = None,
    ) -> CollectionResponse:
        """Create a new collection (async)"""
        data = CollectionCreate(
            name=name,
            description=description,
            metadata=metadata or {},
            config=config or {},
        ).model_dump(exclude_unset=True)

        response = await self._client.request("POST", "/collections", json=data)
        return CollectionResponse(**response.json())

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> CollectionListResponse:
        """List collections with pagination (async)"""
        params = {"limit": limit, "offset": offset}
        response = await self._client.request("GET", "/collections", params=params)
        return CollectionListResponse(**response.json())

    async def get(self, collection_id: UUID) -> CollectionResponse:
        """Get a collection by ID (async)"""
        response = await self._client.request("GET", f"/collections/{collection_id}")
        return CollectionResponse(**response.json())

    async def update(
        self,
        collection_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        config: Optional[Dict] = None,
    ) -> CollectionResponse:
        """Update a collection (async)"""
        data = CollectionUpdate(
            name=name,
            description=description,
            metadata=metadata,
            config=config,
        ).model_dump(exclude_unset=True)

        response = await self._client.request("PATCH", f"/collections/{collection_id}", json=data)
        return CollectionResponse(**response.json())

    async def delete(self, collection_id: UUID) -> None:
        """Delete a collection (async)"""
        await self._client.request("DELETE", f"/collections/{collection_id}")
