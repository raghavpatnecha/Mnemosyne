"""
Local file storage with user-scoped paths
Implements StorageBackend interface for local filesystem
"""

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Union, Optional
from uuid import UUID
from backend.config import settings
from backend.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Local file storage with user-scoped paths"""

    def __init__(self, base_path: str = settings.UPLOAD_DIR):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_document_path(
        self,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        filename: str
    ) -> Path:
        """Generate user-scoped path for document"""
        return (
            self.base_path /
            "users" /
            str(user_id) /
            "collections" /
            str(collection_id) /
            "documents" /
            str(document_id) /
            filename
        )

    def _get_extracted_content_path(
        self,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        content_type: str,
        filename: str
    ) -> Path:
        """Generate path for extracted content (images, etc.)"""
        # Organize by content type: images/, text/, etc.
        type_dir = content_type.split('/')[0] + 's'  # 'image' -> 'images'
        return (
            self.base_path /
            "users" /
            str(user_id) /
            "collections" /
            str(collection_id) /
            "documents" /
            str(document_id) /
            type_dir /
            filename
        )

    def save(
        self,
        file: Union[BinaryIO, bytes],
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        filename: str,
        content_type: Optional[str] = None
    ) -> str:
        """Save file to user-scoped local storage"""
        file_path = self._get_document_path(user_id, collection_id, document_id, filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file, bytes):
            with open(file_path, "wb") as f:
                f.write(file)
        else:
            with open(file_path, "wb") as f:
                if hasattr(file, 'read'):
                    content = file.read()
                    # Reset file pointer if possible
                    if hasattr(file, 'seek'):
                        file.seek(0)
                    f.write(content)
                else:
                    f.write(file)

        # Return relative path from base_path
        return str(file_path.relative_to(self.base_path))

    def save_extracted_content(
        self,
        content: bytes,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        content_type: str,
        filename: str
    ) -> str:
        """Save extracted content (images, text, etc.)"""
        file_path = self._get_extracted_content_path(
            user_id, collection_id, document_id, content_type, filename
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(content)

        return str(file_path.relative_to(self.base_path))

    def get_url(
        self,
        storage_path: str,
        user_id: UUID,
        expires_in: int = 3600
    ) -> str:
        """
        Get file URL (for local storage, returns absolute file path)
        Note: In production with S3, this would return a pre-signed URL
        """
        absolute_path = self.base_path / storage_path

        # Verify path is within user's directory (security check)
        expected_prefix = self.base_path / "users" / str(user_id)
        try:
            absolute_path.relative_to(expected_prefix)
        except ValueError:
            raise PermissionError(f"Access denied: file does not belong to user {user_id}")

        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")

        return f"file://{absolute_path}"

    def read(self, storage_path: str, user_id: UUID) -> bytes:
        """Read file content with user verification"""
        absolute_path = self.base_path / storage_path

        # Verify path is within user's directory (security check)
        expected_prefix = self.base_path / "users" / str(user_id)
        try:
            absolute_path.relative_to(expected_prefix)
        except ValueError:
            raise PermissionError(f"Access denied: file does not belong to user {user_id}")

        with open(absolute_path, "rb") as f:
            return f.read()

    def exists(self, storage_path: str, user_id: UUID) -> bool:
        """Check if file exists and belongs to user"""
        absolute_path = self.base_path / storage_path

        # Verify path is within user's directory
        expected_prefix = self.base_path / "users" / str(user_id)
        try:
            absolute_path.relative_to(expected_prefix)
        except ValueError:
            return False

        return absolute_path.exists()

    def delete(self, storage_path: str, user_id: UUID):
        """Delete file with user verification"""
        absolute_path = self.base_path / storage_path

        # Verify path is within user's directory (security check)
        expected_prefix = self.base_path / "users" / str(user_id)
        try:
            absolute_path.relative_to(expected_prefix)
        except ValueError:
            raise PermissionError(f"Access denied: file does not belong to user {user_id}")

        if absolute_path.exists():
            absolute_path.unlink()

    def delete_collection(self, user_id: UUID, collection_id: UUID):
        """Delete all files for a collection"""
        collection_path = (
            self.base_path /
            "users" /
            str(user_id) /
            "collections" /
            str(collection_id)
        )

        if collection_path.exists() and collection_path.is_dir():
            shutil.rmtree(collection_path)

    def delete_user_data(self, user_id: UUID):
        """Delete all files for a user"""
        user_path = self.base_path / "users" / str(user_id)

        if user_path.exists() and user_path.is_dir():
            shutil.rmtree(user_path)

    def get_local_path(self, storage_path: str, user_id: UUID) -> str:
        """Get local filesystem path (already local, just return absolute path)"""
        # Normalize path separators for cross-platform compatibility
        # (Windows uploads may store backslashes, Docker/Linux uses forward slashes)
        normalized_path = storage_path.replace('\\', '/')
        absolute_path = self.base_path / normalized_path

        # Verify path is within user's directory (security check)
        expected_prefix = self.base_path / "users" / str(user_id)
        try:
            absolute_path.relative_to(expected_prefix)
        except ValueError:
            raise PermissionError(f"Access denied: file does not belong to user {user_id}")

        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")

        return str(absolute_path)
