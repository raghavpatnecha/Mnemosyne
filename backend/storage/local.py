"""
Local file storage with content-based paths
Stores files using SHA-256 hash for deduplication
"""

import os
from pathlib import Path
from typing import BinaryIO, Union
from backend.config import settings


class LocalStorage:
    """Local file storage with content-based paths"""

    def __init__(self, base_path: str = settings.UPLOAD_DIR):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, file: Union[BinaryIO, bytes], content_hash: str) -> str:
        """
        Save file to local storage using content hash

        Args:
            file: File object or bytes to save
            content_hash: SHA-256 hash of content

        Returns:
            str: Relative path to saved file
        """
        subdir = content_hash[:2]
        file_dir = self.base_path / subdir
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / content_hash

        if isinstance(file, bytes):
            with open(file_path, "wb") as f:
                f.write(file)
        else:
            with open(file_path, "wb") as f:
                if hasattr(file, 'read'):
                    f.write(file.read())
                else:
                    f.write(file)

        return f"{subdir}/{content_hash}"

    def get_path(self, relative_path: str) -> Path:
        """Get absolute path from relative path"""
        return self.base_path / relative_path

    def exists(self, relative_path: str) -> bool:
        """Check if file exists"""
        return self.get_path(relative_path).exists()

    def read(self, relative_path: str) -> bytes:
        """Read file content"""
        path = self.get_path(relative_path)
        with open(path, "rb") as f:
            return f.read()

    def delete(self, relative_path: str):
        """Delete file"""
        path = self.get_path(relative_path)
        if path.exists():
            path.unlink()
