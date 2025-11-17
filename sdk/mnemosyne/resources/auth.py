"""Auth resource implementation"""

from typing import TYPE_CHECKING
from ..types.auth import RegisterRequest, RegisterResponse

if TYPE_CHECKING:
    from ..client import Client
    from ..async_client import AsyncClient


class AuthResource:
    """Synchronous Auth resource"""

    def __init__(self, client: "Client"):
        self._client = client

    def register(self, email: str, password: str) -> RegisterResponse:
        """
        Register a new user and receive API key.

        **IMPORTANT**: The API key is only returned once. Save it securely!

        Args:
            email: User email address
            password: Password (minimum 8 characters)

        Returns:
            RegisterResponse: User ID, email, and API key

        Raises:
            ValidationError: Invalid email or password too short
            APIError: Email already registered (400) or server error

        Example:
            >>> from mnemosyne import Client
            >>> # Note: Don't need API key for registration
            >>> client = Client(api_key="not_needed_for_register")
            >>> response = client.auth.register(
            ...     email="user@example.com",
            ...     password="secure_password_123"
            ... )
            >>> print(f"API Key: {response.api_key}")
            >>> # Save this API key securely!
            >>> # Now create a new client with the API key
            >>> client = Client(api_key=response.api_key)
        """
        data = RegisterRequest(email=email, password=password).model_dump()

        # Don't use authentication for registration endpoint
        response = self._client._http_client.post(
            f"{self._client.base_url}/auth/register",
            json=data,
            timeout=self._client.timeout,
        )

        # Handle errors
        self._client._handle_error(response)

        return RegisterResponse(**response.json())


class AsyncAuthResource:
    """Asynchronous Auth resource"""

    def __init__(self, client: "AsyncClient"):
        self._client = client

    async def register(self, email: str, password: str) -> RegisterResponse:
        """Register a new user and receive API key (async)"""
        data = RegisterRequest(email=email, password=password).model_dump()

        # Don't use authentication for registration endpoint
        response = await self._client._http_client.post(
            f"{self._client.base_url}/auth/register",
            json=data,
            timeout=self._client.timeout,
        )

        # Handle errors
        self._client._handle_error(response)

        return RegisterResponse(**response.json())
