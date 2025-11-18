"""
Abstract base class for storage backends
Defines the interface for file storage systems (local, S3, etc.)
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Union, Optional
from uuid import UUID
from pathlib import Path


class StorageBackend(ABC):
    """Abstract base class for file storage backends"""

    @abstractmethod
    def save(
        self,
        file: Union[BinaryIO, bytes],
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        filename: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Save file to storage with user-scoped path

        Args:
            file: File object or bytes to save
            user_id: Owner user ID
            collection_id: Collection ID
            document_id: Document ID
            filename: Original filename
            content_type: MIME type (optional)

        Returns:
            str: Storage path/key for the saved file
        """
        pass

    @abstractmethod
    def save_extracted_content(
        self,
        content: bytes,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        content_type: str,
        filename: str
    ) -> str:
        """
        Save extracted content (images, text, etc.) from document processing

        Args:
            content: Content bytes to save
            user_id: Owner user ID
            collection_id: Collection ID
            document_id: Document ID
            content_type: Type of content (e.g., 'image/png', 'text/plain')
            filename: Filename for the extracted content

        Returns:
            str: Storage path/key for the saved content
        """
        pass

    @abstractmethod
    def get_url(
        self,
        storage_path: str,
        user_id: UUID,
        expires_in: int = 3600
    ) -> str:
        """
        Get accessible URL for stored file

        Args:
            storage_path: Path/key returned by save()
            user_id: Owner user ID (for verification)
            expires_in: URL expiration time in seconds (for pre-signed URLs)

        Returns:
            str: Accessible URL (local file path or pre-signed S3 URL)
        """
        pass

    @abstractmethod
    def read(self, storage_path: str, user_id: UUID) -> bytes:
        """
        Read file content

        Args:
            storage_path: Path/key of the file
            user_id: Owner user ID (for verification)

        Returns:
            bytes: File content
        """
        pass

    @abstractmethod
    def delete(self, storage_path: str, user_id: UUID):
        """
        Delete file from storage

        Args:
            storage_path: Path/key of the file
            user_id: Owner user ID (for verification)
        """
        pass

    @abstractmethod
    def delete_collection(self, user_id: UUID, collection_id: UUID):
        """
        Delete all files for a collection

        Args:
            user_id: Owner user ID
            collection_id: Collection ID
        """
        pass

    @abstractmethod
    def delete_user_data(self, user_id: UUID):
        """
        Delete all files for a user (when user is deleted)

        Args:
            user_id: User ID to delete data for
        """
        pass

    @abstractmethod
    def exists(self, storage_path: str, user_id: UUID) -> bool:
        """
        Check if file exists

        Args:
            storage_path: Path/key of the file
            user_id: Owner user ID (for verification)

        Returns:
            bool: True if file exists and belongs to user
        """
        pass

    def get_lightrag_path(self, user_id: UUID, collection_id: UUID) -> str:
        """
        Get path for LightRAG working directory

        Args:
            user_id: Owner user ID
            collection_id: Collection ID

        Returns:
            str: Path for LightRAG working directory
        """
        return f"users/{user_id}/collections/{collection_id}/lightrag"

    @abstractmethod
    def get_local_path(self, storage_path: str, user_id: UUID) -> str:
        """
        Get local filesystem path for the file.
        For LocalStorage: returns absolute path
        For S3Storage: downloads to temp directory and returns temp path

        Args:
            storage_path: Path/key of the file
            user_id: Owner user ID (for verification)

        Returns:
            str: Local filesystem path (may be temporary)
        """
        pass
