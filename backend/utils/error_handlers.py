"""
Centralized Error Handling

Provides consistent error handling and logging across the application.
Includes handlers for API errors, database errors, and custom exceptions.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from openai import APIError, RateLimitError, APITimeoutError
from sqlalchemy.exc import IntegrityError, OperationalError, DBAPIError
from typing import Dict, Any
import logging
import traceback

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling"""

    @staticmethod
    def handle_openai_error(error: Exception) -> Dict[str, Any]:
        """
        Handle OpenAI API errors

        Args:
            error: OpenAI exception

        Returns:
            Error dictionary with message and details
        """
        if isinstance(error, RateLimitError):
            logger.warning(f"OpenAI rate limit exceeded: {error}")
            return {
                "error": "rate_limit",
                "message": "OpenAI rate limit exceeded. Please try again in a moment.",
                "retry_after": 60,
                "provider": "openai"
            }

        elif isinstance(error, APITimeoutError):
            logger.warning(f"OpenAI API timeout: {error}")
            return {
                "error": "timeout",
                "message": "OpenAI API request timed out. Please try again.",
                "provider": "openai"
            }

        elif isinstance(error, APIError):
            logger.error(f"OpenAI API error: {error}")
            return {
                "error": "api_error",
                "message": "OpenAI API error occurred. Please try again.",
                "details": str(error),
                "provider": "openai"
            }

        else:
            logger.error(f"Unknown OpenAI error: {error}")
            return {
                "error": "unknown",
                "message": "An unexpected error occurred with OpenAI API.",
                "provider": "openai"
            }

    @staticmethod
    def handle_database_error(error: Exception) -> Dict[str, Any]:
        """
        Handle database errors

        Args:
            error: Database exception

        Returns:
            Error dictionary with message and details
        """
        if isinstance(error, IntegrityError):
            logger.warning(f"Database integrity error: {error}")
            return {
                "error": "integrity_error",
                "message": "Data integrity violation. Duplicate entry or constraint failed.",
                "details": str(error.orig) if hasattr(error, 'orig') else str(error)
            }

        elif isinstance(error, OperationalError):
            logger.error(f"Database operational error: {error}")
            return {
                "error": "database_error",
                "message": "Database connection or operational error.",
                "details": str(error.orig) if hasattr(error, 'orig') else str(error)
            }

        elif isinstance(error, DBAPIError):
            logger.error(f"Database API error: {error}")
            return {
                "error": "database_error",
                "message": "Database error occurred.",
                "details": str(error.orig) if hasattr(error, 'orig') else str(error)
            }

        else:
            logger.error(f"Unknown database error: {error}")
            return {
                "error": "unknown",
                "message": "An unexpected database error occurred."
            }

    @staticmethod
    def handle_validation_error(error: Exception) -> Dict[str, Any]:
        """
        Handle Pydantic validation errors

        Args:
            error: Validation exception

        Returns:
            Error dictionary with validation details
        """
        logger.warning(f"Validation error: {error}")
        return {
            "error": "validation_error",
            "message": "Request validation failed.",
            "details": str(error)
        }

    @staticmethod
    def handle_not_found_error(resource: str, identifier: str) -> Dict[str, Any]:
        """
        Handle resource not found errors

        Args:
            resource: Resource type (e.g., "document", "user")
            identifier: Resource identifier

        Returns:
            Error dictionary
        """
        logger.warning(f"{resource} not found: {identifier}")
        return {
            "error": "not_found",
            "message": f"{resource.capitalize()} not found.",
            "resource": resource,
            "identifier": identifier
        }

    @staticmethod
    def handle_permission_error(resource: str, action: str) -> Dict[str, Any]:
        """
        Handle permission/authorization errors

        Args:
            resource: Resource type
            action: Action attempted

        Returns:
            Error dictionary
        """
        logger.warning(f"Permission denied: {action} on {resource}")
        return {
            "error": "permission_denied",
            "message": f"You don't have permission to {action} this {resource}.",
            "resource": resource,
            "action": action
        }

    @staticmethod
    def handle_generic_error(error: Exception) -> Dict[str, Any]:
        """
        Handle generic/unknown errors

        Args:
            error: Exception

        Returns:
            Error dictionary
        """
        logger.error(f"Unexpected error: {error}\n{traceback.format_exc()}")
        return {
            "error": "internal_error",
            "message": "An unexpected error occurred. Please try again.",
            "type": type(error).__name__
        }


# Global exception handlers for FastAPI

async def openai_error_handler(request: Request, exc: APIError):
    """FastAPI exception handler for OpenAI errors"""
    error_data = ErrorHandler.handle_openai_error(exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_data
    )


async def database_error_handler(request: Request, exc: IntegrityError):
    """FastAPI exception handler for database errors"""
    error_data = ErrorHandler.handle_database_error(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_data
    )


async def generic_error_handler(request: Request, exc: Exception):
    """FastAPI exception handler for generic errors"""
    error_data = ErrorHandler.handle_generic_error(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_data
    )


# Setup function for FastAPI app
def setup_error_handlers(app):
    """
    Setup global error handlers for FastAPI app

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(APIError, openai_error_handler)
    app.add_exception_handler(IntegrityError, database_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    logger.info("Error handlers registered")
