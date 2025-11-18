"""
File storage system
Supports both local filesystem and S3-compatible storage
"""

from backend.storage.base import StorageBackend
from backend.storage.local import LocalStorage
from backend.storage.s3 import S3Storage
from backend.storage.factory import get_storage_backend, storage_backend

__all__ = [
    "StorageBackend",
    "LocalStorage",
    "S3Storage",
    "get_storage_backend",
    "storage_backend"
]
