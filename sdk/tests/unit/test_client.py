"""Unit tests for Client class"""

import pytest
from pytest_httpx import HTTPXMock
from mnemosyne import Client, AuthenticationError, NotFoundError, ValidationError


def test_client_initialization():
    """Test client initialization"""
    client = Client(api_key="test_key")
    assert client.api_key == "test_key"
    assert client.base_url == "http://localhost:8000"
    assert client.timeout == 60.0
    assert client.max_retries == 3
    client.close()


def test_client_initialization_custom():
    """Test client initialization with custom settings"""
    client = Client(
        api_key="test_key",
        base_url="https://api.mnemosyne.ai",
        timeout=120.0,
        max_retries=5,
    )
    assert client.base_url == "https://api.mnemosyne.ai"
    assert client.timeout == 120.0
    assert client.max_retries == 5
    client.close()


def test_client_requires_api_key():
    """Test that API key is required"""
    with pytest.raises(ValueError, match="api_key is required"):
        Client(api_key="")


def test_client_context_manager():
    """Test client as context manager"""
    with Client(api_key="test_key") as client:
        assert client._http_client is not None
    # Client should be closed after context


def test_get_headers(client):
    """Test authentication headers"""
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer test_api_key_123"
    assert headers["Content-Type"] == "application/json"


def test_handle_error_401(client, httpx_mock: HTTPXMock):
    """Test 401 authentication error"""
    httpx_mock.add_response(
        method="GET",
        url="http://localhost:8000/collections",
        status_code=401,
        json={"detail": "Invalid API key"},
    )

    with pytest.raises(AuthenticationError, match="Invalid API key"):
        client.request("GET", "/collections")


def test_handle_error_404(client, httpx_mock: HTTPXMock):
    """Test 404 not found error"""
    httpx_mock.add_response(
        method="GET",
        url="http://localhost:8000/collections/123",
        status_code=404,
        json={"detail": "Collection not found"},
    )

    with pytest.raises(NotFoundError, match="Collection not found"):
        client.request("GET", "/collections/123")


def test_handle_error_422(client, httpx_mock: HTTPXMock):
    """Test 422 validation error"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/collections",
        status_code=422,
        json={"detail": "Invalid request data"},
    )

    with pytest.raises(ValidationError, match="Invalid request data"):
        client.request("POST", "/collections", json={"invalid": "data"})


def test_request_success(client, httpx_mock: HTTPXMock, mock_collection_response):
    """Test successful request"""
    httpx_mock.add_response(
        method="GET",
        url="http://localhost:8000/collections",
        json={"data": [mock_collection_response], "pagination": {}},
    )

    response = client.request("GET", "/collections")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
