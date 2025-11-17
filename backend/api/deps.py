"""
FastAPI dependencies
Authentication, database session, etc.
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from backend.database import get_db
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.core.security import hash_api_key
from backend.core.exceptions import http_401_unauthorized


async def get_current_user(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from API key

    Args:
        authorization: Authorization header (format: "Bearer mn_test_...")
        db: Database session

    Returns:
        User: Authenticated user

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Validate header format
    if not authorization.startswith("Bearer "):
        raise http_401_unauthorized("Invalid authorization header format")

    # Extract API key
    api_key = authorization[7:]  # Remove "Bearer " prefix

    if not api_key:
        raise http_401_unauthorized("API key missing")

    # Hash the provided key
    key_hash = hash_api_key(api_key)

    # Find API key in database
    api_key_obj = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

    if not api_key_obj:
        raise http_401_unauthorized("Invalid API key")

    # Check if key is expired
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        raise http_401_unauthorized("API key expired")

    # Update last used timestamp
    api_key_obj.last_used_at = datetime.utcnow()
    db.commit()

    # Get user
    user = db.query(User).filter(User.id == api_key_obj.user_id).first()

    if not user:
        raise http_401_unauthorized("User not found")

    if not user.is_active:
        raise http_401_unauthorized("User account is inactive")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (convenience dependency)

    Args:
        current_user: User from get_current_user

    Returns:
        User: Active user

    Raises:
        HTTPException: 401 if user is inactive
    """
    if not current_user.is_active:
        raise http_401_unauthorized("Inactive user")

    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current superuser (admin only)

    Args:
        current_user: User from get_current_user

    Returns:
        User: Superuser

    Raises:
        HTTPException: 403 if user is not superuser
    """
    if not current_user.is_superuser:
        from backend.core.exceptions import http_403_forbidden
        raise http_403_forbidden("Superuser access required")

    return current_user


# ==============================================================================
# Service Singletons
# ==============================================================================
# Prevent expensive service re-initialization on every request
# Using lru_cache to create singleton instances


from functools import lru_cache


@lru_cache(maxsize=1)
def get_cache_service():
    """
    Get singleton CacheService instance

    Prevents Redis reconnection on every request

    Returns:
        CacheService: Singleton cache service
    """
    from backend.services.cache_service import CacheService
    return CacheService()


@lru_cache(maxsize=1)
def get_reranker_service():
    """
    Get singleton RerankerService instance

    Prevents model reloading on every request

    Returns:
        RerankerService: Singleton reranker service
    """
    from backend.services.reranker_service import RerankerService
    return RerankerService()


@lru_cache(maxsize=1)
def get_query_reformulation_service():
    """
    Get singleton QueryReformulationService instance

    Prevents OpenAI client re-initialization on every request

    Returns:
        QueryReformulationService: Singleton query reformulation service
    """
    from backend.services.query_reformulation import QueryReformulationService
    return QueryReformulationService()
