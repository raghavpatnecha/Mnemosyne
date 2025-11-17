"""Synchronous Mnemosyne SDK client"""

import time
from typing import Optional, Any, Dict
import httpx
from ._base_client import BaseClient
from .resources import (
    AuthResource,
    CollectionsResource,
    DocumentsResource,
    RetrievalsResource,
    ChatResource,
)


class Client(BaseClient):
    """
    Synchronous client for Mnemosyne RAG API.

    This client provides access to all Mnemosyne API resources with automatic
    retry logic, error handling, and connection management.

    Example:
        >>> client = Client(api_key="mn_...")
        >>> collection = client.collections.create(name="Research Papers")
        >>> client.close()

        # Or using context manager:
        >>> with Client(api_key="mn_...") as client:
        ...     collection = client.collections.create(name="Research Papers")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000/api/v1",
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        """
        Initialize synchronous Mnemosyne client.

        Args:
            api_key: Mnemosyne API key (required)
            base_url: Base URL for API (default: http://localhost:8000/api/v1)
            timeout: Request timeout in seconds (default: 60.0)
            max_retries: Maximum number of retries for failed requests (default: 3)

        Raises:
            ValueError: If api_key is empty

        Example:
            >>> client = Client(api_key="mn_...")
            >>> # or with custom settings:
            >>> client = Client(
            ...     api_key="mn_...",
            ...     base_url="https://api.mnemosyne.ai/api/v1",
            ...     timeout=120.0,
            ...     max_retries=5
            ... )
        """
        super().__init__(api_key, base_url, timeout, max_retries)

        # Initialize HTTP client
        self._http_client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True,
        )

        # Initialize resource instances
        self.auth = AuthResource(self)
        self.collections = CollectionsResource(self)
        self.documents = DocumentsResource(self)
        self.retrievals = RetrievalsResource(self)
        self.chat = ChatResource(self)

    def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            path: Request path (e.g., "/collections")
            **kwargs: Additional arguments passed to httpx (json, params, etc.)

        Returns:
            httpx.Response: Successful response

        Raises:
            AuthenticationError: Invalid API key (401)
            PermissionError: Insufficient permissions (403)
            NotFoundError: Resource not found (404)
            ValidationError: Invalid request (422)
            RateLimitError: Rate limit exceeded (429)
            APIError: Server error or other failures
        """
        # Ensure headers are set
        if "headers" not in kwargs:
            kwargs["headers"] = self._get_headers()

        url = path if path.startswith("http") else f"{self.base_url}{path}"
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = self._http_client.request(method, url, **kwargs)

                # Check if we should retry
                if self._should_retry(response, None):
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        time.sleep(delay)
                        continue

                # Handle errors (raises exceptions)
                self._handle_error(response)
                return response

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    time.sleep(delay)
                    continue
                else:
                    from .exceptions import APIError
                    raise APIError(f"Request failed after {self.max_retries} retries: {str(e)}")

        # Should not reach here, but handle gracefully
        if last_exception:
            from .exceptions import APIError
            raise APIError(f"Request failed: {str(last_exception)}")

        return response
