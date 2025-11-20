"""
Rate Limiting Middleware

Protects API endpoints from abuse using SlowAPI with Redis backend.
Provides per-endpoint rate limits based on user tier and request type.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from backend.config import settings
from backend.utils.sanitize import get_safe_api_key_display
import logging

logger = logging.getLogger(__name__)


# Initialize rate limiter with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL if settings.RATE_LIMIT_ENABLED else None,
    enabled=settings.RATE_LIMIT_ENABLED
)


def get_api_key_from_request(request: Request) -> str:
    """
    Extract API key from request for user-specific rate limiting

    Checks:
    1. Authorization header (Bearer token)
    2. X-API-Key header
    3. Query parameter api_key

    Returns:
        API key or IP address as fallback
    """
    # Check Authorization header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]

    # Check X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key

    # Check query parameter
    api_key = request.query_params.get("api_key")
    if api_key:
        return api_key

    # Fallback to IP address
    return get_remote_address(request)


def rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on API key or IP

    Format: "api_key:{key}" or "ip:{address}"
    """
    api_key = get_api_key_from_request(request)

    if api_key and api_key != get_remote_address(request):
        return f"api_key:{api_key}"

    return f"ip:{api_key}"


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors

    Returns:
        HTTPException with detailed error message
    """
    retry_after = exc.headers.get("Retry-After", "60")

    # Sanitize API key for logging (Issue #3 fix)
    api_key = get_api_key_from_request(request)
    safe_key = get_safe_api_key_display(api_key) if api_key != get_remote_address(request) else api_key

    logger.warning(
        f"Rate limit exceeded for {safe_key} "
        f"on {request.url.path}"
    )

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "retry_after": int(retry_after),
            "limit": str(exc),
            "endpoint": request.url.path
        },
        headers={"Retry-After": retry_after}
    )


# Rate limit decorators for different endpoints

def chat_rate_limit():
    """
    Rate limit for chat endpoints

    Default: 10 requests per minute
    Premium: 50 requests per minute
    """
    return limiter.limit(settings.RATE_LIMIT_CHAT)


def retrieval_rate_limit():
    """
    Rate limit for retrieval endpoints

    Default: 100 requests per minute
    Premium: 500 requests per minute
    """
    return limiter.limit(settings.RATE_LIMIT_RETRIEVAL)


def upload_rate_limit():
    """
    Rate limit for upload endpoints

    Default: 20 requests per hour
    Premium: 100 requests per hour
    """
    return limiter.limit(settings.RATE_LIMIT_UPLOAD)


def auth_rate_limit():
    """
    Rate limit for authentication endpoints

    Default: 5 requests per minute (strict to prevent brute force)
    """
    return limiter.limit("5/minute")


# Middleware setup function
def setup_rate_limiting(app):
    """
    Setup rate limiting middleware

    Args:
        app: FastAPI application instance
    """
    if settings.RATE_LIMIT_ENABLED:
        app.state.limiter = limiter
        app.add_exception_handler(
            RateLimitExceeded,
            custom_rate_limit_exceeded_handler
        )
        logger.info("Rate limiting enabled with Redis backend")
    else:
        logger.warning("Rate limiting disabled")
