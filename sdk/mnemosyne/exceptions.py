"""Exception classes for Mnemosyne SDK"""

from typing import Optional


class MnemosyneError(Exception):
    """Base exception for all Mnemosyne SDK errors"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(MnemosyneError):
    """Raised when API key is invalid or missing (401)"""
    pass


class PermissionError(MnemosyneError):
    """Raised when user lacks permission for resource (403)"""
    pass


class NotFoundError(MnemosyneError):
    """Raised when resource is not found (404)"""
    pass


class ValidationError(MnemosyneError):
    """Raised when request validation fails (422)"""
    pass


class RateLimitError(MnemosyneError):
    """Raised when rate limit is exceeded (429)"""
    pass


class APIError(MnemosyneError):
    """Raised for server errors (5xx) or unknown errors"""
    pass
