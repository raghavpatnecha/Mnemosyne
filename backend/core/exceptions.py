"""
Custom exceptions for Mnemosyne API
"""

from fastapi import HTTPException, status


class MnemosyneException(Exception):
    """Base exception for Mnemosyne"""
    pass


class AuthenticationError(MnemosyneException):
    """Authentication failed"""
    pass


class PermissionError(MnemosyneException):
    """Insufficient permissions"""
    pass


class NotFoundError(MnemosyneException):
    """Resource not found"""
    pass


class DuplicateError(MnemosyneException):
    """Duplicate resource"""
    pass


# HTTP exception helpers
def http_401_unauthorized(detail: str = "Invalid authentication credentials"):
    """Raise 401 Unauthorized"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def http_403_forbidden(detail: str = "Not enough permissions"):
    """Raise 403 Forbidden"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def http_404_not_found(detail: str = "Resource not found"):
    """Raise 404 Not Found"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def http_400_bad_request(detail: str = "Bad request"):
    """Raise 400 Bad Request"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def http_409_conflict(detail: str = "Resource conflict"):
    """Raise 409 Conflict"""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )
