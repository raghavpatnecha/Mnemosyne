"""
Content Type Detection Utility
Detects MIME type from file extension and content, with fallback chain
"""

import mimetypes
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Extension to MIME type mapping for types that mimetypes module doesn't handle well
EXTENSION_MIME_MAP = {
    # Email
    ".eml": "message/rfc822",
    ".msg": "application/vnd.ms-outlook",
    # Documents
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # Text
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".rst": "text/x-rst",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    # Data
    ".json": "application/json",
    ".jsonl": "application/jsonl",
    ".xml": "application/xml",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    # Audio
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    # Video
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    # Images
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


def detect_content_type(
    filename: str,
    content: Optional[bytes] = None,
    client_content_type: Optional[str] = None
) -> str:
    """
    Detect content type with fallback chain:
    1. File extension mapping (most reliable for known types)
    2. Python mimetypes module
    3. python-magic library (content-based detection)
    4. Client-provided content type (if not generic)
    5. Default to application/octet-stream

    Args:
        filename: Original filename with extension
        content: File content bytes (optional, for magic detection)
        client_content_type: Content-Type from HTTP request header

    Returns:
        Detected MIME type string
    """
    # Get file extension
    ext = Path(filename).suffix.lower()

    # 1. Try our extension mapping first (most reliable)
    if ext in EXTENSION_MIME_MAP:
        detected = EXTENSION_MIME_MAP[ext]
        logger.debug(f"Content type from extension map: {filename} -> {detected}")
        return detected

    # 2. Try Python's mimetypes module
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type and mime_type != "application/octet-stream":
        logger.debug(f"Content type from mimetypes: {filename} -> {mime_type}")
        return mime_type

    # 3. Try python-magic if content is provided
    if content:
        try:
            import magic
            detected = magic.from_buffer(content, mime=True)
            if detected and detected != "application/octet-stream":
                logger.debug(f"Content type from magic: {filename} -> {detected}")
                return detected
        except ImportError:
            logger.debug("python-magic not available, skipping content detection")
        except Exception as e:
            logger.debug(f"Magic detection failed: {e}")

    # 4. Use client-provided type if it's not generic
    if client_content_type and client_content_type != "application/octet-stream":
        logger.debug(f"Content type from client: {filename} -> {client_content_type}")
        return client_content_type

    # 5. Default fallback
    logger.warning(f"Could not detect content type for {filename}, using application/octet-stream")
    return "application/octet-stream"
