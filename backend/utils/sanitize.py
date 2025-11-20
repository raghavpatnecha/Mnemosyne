"""
Security utility for sanitizing sensitive data in logs and errors
Prevents API keys and credentials from being exposed in logs
"""

from typing import Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

# Headers that contain sensitive information
SENSITIVE_HEADERS = {
    "authorization",
    "x-api-key",
    "cookie",
    "x-auth-token",
    "api-key",
    "apikey"
}

# Patterns to detect and redact sensitive data
SENSITIVE_PATTERNS = [
    (re.compile(r'(mn_[a-zA-Z0-9_]{32,})'), 'mn_***REDACTED***'),  # Mnemosyne API keys
    (re.compile(r'(sk-[a-zA-Z0-9]{32,})'), 'sk-***REDACTED***'),  # OpenAI keys
    (re.compile(r'(Bearer\s+[a-zA-Z0-9_\-\.]+)'), 'Bearer ***REDACTED***'),  # Bearer tokens
]


def sanitize_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive headers from dict

    Args:
        headers: Dictionary of headers

    Returns:
        Sanitized headers with sensitive values redacted
    """
    if not isinstance(headers, dict):
        return headers

    sanitized = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value

    return sanitized


def sanitize_string(text: str) -> str:
    """
    Remove sensitive patterns from string

    Args:
        text: String that may contain sensitive data

    Returns:
        Sanitized string with patterns redacted
    """
    if not isinstance(text, str):
        return text

    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def sanitize_dict(data: Dict[str, Any], sensitive_keys: set = None) -> Dict[str, Any]:
    """
    Recursively sanitize dictionary by removing sensitive keys

    Args:
        data: Dictionary to sanitize
        sensitive_keys: Set of keys to redact (defaults to common sensitive keys)

    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data

    if sensitive_keys is None:
        sensitive_keys = {"api_key", "apikey", "password", "secret", "token", "authorization"}

    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, sensitive_keys)
        elif isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        else:
            sanitized[key] = value

    return sanitized


def get_safe_api_key_display(api_key: str) -> str:
    """
    Get safe version of API key for logging (only prefix)

    Args:
        api_key: Full API key

    Returns:
        Safe display string (e.g., "mn_test_abc...***")
    """
    if not api_key or not isinstance(api_key, str):
        return "***INVALID***"

    if len(api_key) < 12:
        return "***REDACTED***"

    # Show prefix and first few chars only
    return f"{api_key[:12]}...***"
