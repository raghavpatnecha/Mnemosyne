"""
Middleware Components

Provides cross-cutting concerns like rate limiting, authentication, and logging.
"""

from backend.middleware.rate_limiter import limiter, setup_rate_limiting

__all__ = ["limiter", "setup_rate_limiting"]
