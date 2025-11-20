"""Base client implementation with shared logic for sync and async clients"""

import time
from typing import Optional, Any, Dict
import httpx
from .version import __version__
from .exceptions import (
    AuthenticationError,
    PermissionError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    APIError,
)


class BaseClient:
    """
    Base client with shared logic for HTTP requests and error handling.

    This class provides:
    - HTTP client management
    - Authentication headers
    - Error handling and exception mapping
    - Retry logic with exponential backoff
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000/api/v1",
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        """
        Initialize base client.

        Args:
            api_key: Mnemosyne API key (required)
            base_url: Base URL for API (default: http://localhost:8000/api/v1)
            timeout: Request timeout in seconds (default: 60.0)
            max_retries: Maximum number of retries for failed requests (default: 3)

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("api_key is required")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Will be set by subclasses
        self._http_client: Optional[httpx.Client] = None

    def _get_headers(self, include_content_type: bool = True) -> Dict[str, str]:
        """
        Get authentication and default headers for requests

        Args:
            include_content_type: Whether to include Content-Type: application/json
                                 (default: True, set to False for multipart uploads)

        Returns:
            Dict of headers including Authorization and User-Agent
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": f"mnemosyne-python/{__version__}",
        }

        if include_content_type:
            headers["Content-Type"] = "application/json"

        return headers

    def _handle_error(self, response: httpx.Response) -> None:
        """
        Handle error responses and raise appropriate exceptions.

        Args:
            response: HTTP response object

        Raises:
            AuthenticationError: For 401 responses
            PermissionError: For 403 responses
            NotFoundError: For 404 responses
            ValidationError: For 422 responses
            RateLimitError: For 429 responses
            APIError: For other error responses
        """
        if response.is_success:
            return

        status_code = response.status_code
        try:
            error_data = response.json()
            message = error_data.get("detail", response.text)
        except Exception:
            message = response.text or f"HTTP {status_code} error"

        # Map status codes to exception types
        if status_code == 401:
            raise AuthenticationError(message, status_code)
        elif status_code == 403:
            raise PermissionError(message, status_code)
        elif status_code == 404:
            raise NotFoundError(message, status_code)
        elif status_code == 422:
            raise ValidationError(message, status_code)
        elif status_code == 429:
            raise RateLimitError(message, status_code)
        else:
            raise APIError(message, status_code)

    def _should_retry(self, response: Optional[httpx.Response], exception: Optional[Exception]) -> bool:
        """
        Determine if a request should be retried.

        Args:
            response: HTTP response (if available)
            exception: Exception raised (if any)

        Returns:
            bool: True if request should be retried
        """
        # Retry on network errors
        if exception and isinstance(exception, (httpx.RequestError, httpx.TimeoutException)):
            return True

        # Retry on 5xx server errors and 429 rate limits
        if response and response.status_code in (429, 500, 502, 503, 504):
            return True

        return False

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current retry attempt (0-indexed)

        Returns:
            float: Delay in seconds
        """
        return min(2 ** attempt, 16)  # Max 16 seconds

    def _prepare_request_url(self, path: str) -> str:
        """
        Prepare full URL from path

        Args:
            path: Request path (e.g., "/collections") or full URL

        Returns:
            str: Full URL for request
        """
        return path if path.startswith("http") else f"{self.base_url}{path}"

    def _should_retry_attempt(self, attempt: int, response: Optional[httpx.Response], exception: Optional[Exception]) -> bool:
        """
        Determine if we should retry and how long to wait

        Args:
            attempt: Current retry attempt (0-indexed)
            response: HTTP response (if available)
            exception: Exception raised (if any)

        Returns:
            bool: True if should retry (and not on last attempt)
        """
        if attempt >= self.max_retries - 1:
            return False

        return self._should_retry(response, exception)

    def close(self) -> None:
        """Close the HTTP client"""
        if self._http_client:
            self._http_client.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False
