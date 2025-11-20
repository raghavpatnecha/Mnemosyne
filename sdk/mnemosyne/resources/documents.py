"""Documents resource implementation"""

import json
from pathlib import Path
from typing import Optional, Dict, Union, BinaryIO, TYPE_CHECKING
from uuid import UUID
from ..types.documents import (
    DocumentResponse,
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentUpdate,
)

if TYPE_CHECKING:
    from ..client import Client
    from ..async_client import AsyncClient


class DocumentsResource:
    """Synchronous Documents resource"""

    def __init__(self, client: "Client"):
        self._client = client

    def create(
        self,
        collection_id: UUID,
        file: Union[str, Path, BinaryIO],
        metadata: Optional[Dict] = None,
    ) -> DocumentResponse:
        """
        Upload a document to a collection.

        Args:
            collection_id: Collection UUID
            file: File path, Path object, or file-like object
            metadata: Optional metadata dictionary

        Returns:
            DocumentResponse: Created document with processing status

        Raises:
            NotFoundError: Collection not found
            ValidationError: Invalid file or metadata
            APIError: Upload failed
        """
        # Handle file input
        if isinstance(file, (str, Path)):
            file_obj = open(file, "rb")
            filename = Path(file).name
            close_file = True
        else:
            file_obj = file
            filename = getattr(file, "name", "file")
            close_file = False

        try:
            files = {"file": (filename, file_obj)}
            data = {
                "collection_id": str(collection_id),
                "metadata": json.dumps(metadata or {}),
            }

            # Use base headers without Content-Type (httpx handles multipart/form-data)
            headers = self._client._get_headers(include_content_type=False)
            response = self._client._http_client.post(
                f"{self._client.base_url}/documents",
                files=files,
                data=data,
                headers=headers,
                timeout=self._client.timeout,
            )
            self._client._handle_error(response)
            return DocumentResponse(**response.json())
        finally:
            if close_file:
                file_obj.close()

    def list(
        self,
        collection_id: UUID,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ) -> DocumentListResponse:
        """
        List documents with pagination and filtering.

        Args:
            collection_id: Collection UUID (required)
            limit: Number of results per page (1-100, default: 20)
            offset: Number of results to skip (default: 0)
            status_filter: Filter by status (pending, processing, completed, failed)

        Returns:
            DocumentListResponse: List of documents with pagination info
        """
        params = {
            "collection_id": str(collection_id),
            "limit": limit,
            "offset": offset
        }
        if status_filter:
            params["status"] = status_filter

        response = self._client.request("GET", "/documents", params=params)
        return DocumentListResponse(**response.json())

    def get(self, document_id: UUID) -> DocumentResponse:
        """
        Get a document by ID.

        Args:
            document_id: Document UUID

        Returns:
            DocumentResponse: Document details

        Raises:
            NotFoundError: Document not found
        """
        response = self._client.request("GET", f"/documents/{document_id}")
        return DocumentResponse(**response.json())

    def get_status(self, document_id: UUID) -> DocumentStatusResponse:
        """
        Get document processing status.

        Args:
            document_id: Document UUID

        Returns:
            DocumentStatusResponse: Processing status with chunk/token counts

        Raises:
            NotFoundError: Document not found
        """
        response = self._client.request("GET", f"/documents/{document_id}/status")
        return DocumentStatusResponse(**response.json())

    def update(
        self,
        document_id: UUID,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> DocumentResponse:
        """
        Update document metadata.

        Args:
            document_id: Document UUID
            title: New title
            metadata: New metadata

        Returns:
            DocumentResponse: Updated document

        Raises:
            NotFoundError: Document not found
            ValidationError: Invalid parameters
        """
        data = DocumentUpdate(
            title=title,
            metadata=metadata,
        ).model_dump(exclude_unset=True)

        response = self._client.request("PATCH", f"/documents/{document_id}", json=data)
        return DocumentResponse(**response.json())

    def delete(self, document_id: UUID) -> None:
        """
        Delete a document.

        Args:
            document_id: Document UUID

        Raises:
            NotFoundError: Document not found
        """
        self._client.request("DELETE", f"/documents/{document_id}")

    def get_url(self, document_id: UUID, expires_in: int = 3600) -> Dict:
        """
        Get access URL for document file.

        Args:
            document_id: Document UUID
            expires_in: URL expiration time in seconds (default: 3600 = 1 hour)

        Returns:
            Dict with url, expires_in, filename, content_type

        Raises:
            NotFoundError: Document not found
            ValidationError: File not found in storage
        """
        params = {"expires_in": expires_in}
        response = self._client.request("GET", f"/documents/{document_id}/url", params=params)
        return response.json()


class AsyncDocumentsResource:
    """Asynchronous Documents resource"""

    def __init__(self, client: "AsyncClient"):
        self._client = client

    async def create(
        self,
        collection_id: UUID,
        file: Union[str, Path, BinaryIO],
        metadata: Optional[Dict] = None,
    ) -> DocumentResponse:
        """Upload a document to a collection (async)"""
        # Handle file input
        if isinstance(file, (str, Path)):
            file_obj = open(file, "rb")
            filename = Path(file).name
            close_file = True
        else:
            file_obj = file
            filename = getattr(file, "name", "file")
            close_file = False

        try:
            files = {"file": (filename, file_obj)}
            data = {
                "collection_id": str(collection_id),
                "metadata": json.dumps(metadata or {}),
            }

            # Use base headers without Content-Type (httpx handles multipart/form-data)
            headers = self._client._get_headers(include_content_type=False)
            response = await self._client._http_client.post(
                f"{self._client.base_url}/documents",
                files=files,
                data=data,
                headers=headers,
                timeout=self._client.timeout,
            )
            self._client._handle_error(response)
            return DocumentResponse(**response.json())
        finally:
            if close_file:
                file_obj.close()

    async def list(
        self,
        collection_id: UUID,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ) -> DocumentListResponse:
        """List documents with pagination and filtering (async)"""
        params = {
            "collection_id": str(collection_id),
            "limit": limit,
            "offset": offset
        }
        if status_filter:
            params["status"] = status_filter

        response = await self._client.request("GET", "/documents", params=params)
        return DocumentListResponse(**response.json())

    async def get(self, document_id: UUID) -> DocumentResponse:
        """Get a document by ID (async)"""
        response = await self._client.request("GET", f"/documents/{document_id}")
        return DocumentResponse(**response.json())

    async def get_status(self, document_id: UUID) -> DocumentStatusResponse:
        """Get document processing status (async)"""
        response = await self._client.request("GET", f"/documents/{document_id}/status")
        return DocumentStatusResponse(**response.json())

    async def update(
        self,
        document_id: UUID,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> DocumentResponse:
        """Update document metadata (async)"""
        data = DocumentUpdate(
            title=title,
            metadata=metadata,
        ).model_dump(exclude_unset=True)

        response = await self._client.request("PATCH", f"/documents/{document_id}", json=data)
        return DocumentResponse(**response.json())

    async def delete(self, document_id: UUID) -> None:
        """Delete a document (async)"""
        await self._client.request("DELETE", f"/documents/{document_id}")

    async def get_url(self, document_id: UUID, expires_in: int = 3600) -> Dict:
        """
        Get access URL for document file (async).

        Args:
            document_id: Document UUID
            expires_in: URL expiration time in seconds (default: 3600 = 1 hour)

        Returns:
            Dict with url, expires_in, filename, content_type

        Raises:
            NotFoundError: Document not found
            ValidationError: File not found in storage
        """
        params = {"expires_in": expires_in}
        response = await self._client.request("GET", f"/documents/{document_id}/url", params=params)
        return response.json()
