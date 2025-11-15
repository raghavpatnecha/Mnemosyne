"""
Security utilities for authentication
API key generation, hashing, password hashing
"""

import secrets
import hashlib
from passlib.context import CryptContext
from backend.config import settings

# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and its hash

    Returns:
        tuple: (api_key, key_hash)
            - api_key: Full key to show user (only once)
            - key_hash: SHA-256 hash to store in database

    Example:
        >>> key, hash = generate_api_key()
        >>> key
        'mn_test_abc123def456...'
        >>> hash
        'sha256:...'
    """
    # Generate secure random token
    random_token = secrets.token_urlsafe(32)

    # Create API key with prefix
    api_key = f"{settings.API_KEY_PREFIX}{random_token}"

    # Hash for storage
    key_hash = hash_api_key(api_key)

    return api_key, key_hash


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256

    Args:
        api_key: The API key to hash

    Returns:
        str: SHA-256 hash of the key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, key_hash: str) -> bool:
    """
    Verify an API key against its stored hash

    Args:
        api_key: The API key to verify
        key_hash: The stored hash to compare against

    Returns:
        bool: True if key matches hash
    """
    return hash_api_key(api_key) == key_hash


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        str: Bcrypt hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password
        hashed_password: Stored bcrypt hash

    Returns:
        bool: True if password matches hash
    """
    return pwd_context.verify(plain_password, hashed_password)
