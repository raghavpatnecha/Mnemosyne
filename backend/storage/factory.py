"""
Storage backend factory
Creates appropriate storage backend based on configuration
"""

import logging
from backend.config import settings
from backend.storage.base import StorageBackend
from backend.storage.local import LocalStorage
from backend.storage.s3 import S3Storage

logger = logging.getLogger(__name__)


def get_storage_backend() -> StorageBackend:
    """
    Create and return the appropriate storage backend based on configuration

    Returns:
        StorageBackend: Configured storage backend (LocalStorage or S3Storage)

    Raises:
        ValueError: If STORAGE_BACKEND is not "local" or "s3"
    """
    backend_type = settings.STORAGE_BACKEND.lower()

    if backend_type == "local":
        logger.info(f"Using local file storage: {settings.UPLOAD_DIR}")
        return LocalStorage(base_path=settings.UPLOAD_DIR)

    elif backend_type == "s3":
        logger.info(f"Using S3 storage: bucket={settings.S3_BUCKET_NAME}, region={settings.S3_REGION}")

        # Build S3 config (only pass non-empty values)
        s3_config = {
            "bucket_name": settings.S3_BUCKET_NAME,
        }

        if settings.S3_ACCESS_KEY_ID:
            s3_config["aws_access_key_id"] = settings.S3_ACCESS_KEY_ID
        if settings.S3_SECRET_ACCESS_KEY:
            s3_config["aws_secret_access_key"] = settings.S3_SECRET_ACCESS_KEY
        if settings.S3_REGION:
            s3_config["region_name"] = settings.S3_REGION
        if settings.S3_ENDPOINT_URL:
            s3_config["endpoint_url"] = settings.S3_ENDPOINT_URL

        return S3Storage(**s3_config)

    else:
        raise ValueError(
            f"Invalid STORAGE_BACKEND: {backend_type}. Must be 'local' or 's3'"
        )


# Global storage backend instance (initialized on import)
storage_backend: StorageBackend = get_storage_backend()
