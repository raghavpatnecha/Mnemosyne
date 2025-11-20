"""
Metadata Filter Validation
Prevents SQL injection and DoS attacks via metadata filters
"""

from typing import Dict, Optional, Set
from backend.core.exceptions import http_400_bad_request

# Whitelist of allowed metadata filter keys
# Only these keys can be used in metadata filters
ALLOWED_METADATA_KEYS: Set[str] = {
    "source",
    "page",
    "author",
    "category",
    "tags",
    "language",
    "type",
    "format",
    "status",
    "priority"
}

MAX_FILTER_VALUE_LENGTH = 256
MAX_FILTER_KEYS = 10


def validate_metadata_filter(metadata_filter: Optional[Dict]) -> Dict:
    """
    Validate metadata filter for security and performance

    Issue #1 fix: Prevents abuse via metadata filters by:
    - Whitelisting allowed keys
    - Limiting value lengths
    - Restricting number of filters

    Args:
        metadata_filter: User-provided metadata filter dict

    Returns:
        Validated metadata filter dict

    Raises:
        HTTPException: 400 if filter is invalid
    """
    if not metadata_filter:
        return {}

    if not isinstance(metadata_filter, dict):
        raise http_400_bad_request("metadata_filter must be an object/dict")

    if len(metadata_filter) > MAX_FILTER_KEYS:
        raise http_400_bad_request(
            f"Too many metadata filters (max {MAX_FILTER_KEYS}, got {len(metadata_filter)})"
        )

    validated = {}
    for key, value in metadata_filter.items():
        # Validate key
        if not isinstance(key, str):
            raise http_400_bad_request(f"Metadata filter key must be string, got {type(key).__name__}")

        if key not in ALLOWED_METADATA_KEYS:
            raise http_400_bad_request(
                f"Metadata filter key '{key}' not allowed. "
                f"Allowed keys: {', '.join(sorted(ALLOWED_METADATA_KEYS))}"
            )

        # Validate value
        if not isinstance(value, str):
            raise http_400_bad_request(
                f"Metadata filter value for '{key}' must be string, got {type(value).__name__}"
            )

        if len(value) > MAX_FILTER_VALUE_LENGTH:
            raise http_400_bad_request(
                f"Metadata filter value for '{key}' too long "
                f"(max {MAX_FILTER_VALUE_LENGTH} chars, got {len(value)})"
            )

        validated[key] = value

    return validated
