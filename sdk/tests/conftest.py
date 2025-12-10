"""Pytest configuration and fixtures"""

import pytest
from uuid import uuid4
from mnemosyne import Client, AsyncClient


@pytest.fixture
def api_key():
    """Test API key"""
    return "test_api_key_123"


@pytest.fixture
def base_url():
    """Test base URL"""
    return "http://localhost:8000/api/v1"


@pytest.fixture
def client(api_key, base_url):
    """Create test client"""
    client = Client(api_key=api_key, base_url=base_url, max_retries=1)
    yield client
    client.close()


@pytest.fixture
def async_client(api_key, base_url):
    """Create test async client"""
    return AsyncClient(api_key=api_key, base_url=base_url, max_retries=1)


@pytest.fixture
def collection_id():
    """Test collection UUID as string"""
    return str(uuid4())


@pytest.fixture
def document_id():
    """Test document UUID as string"""
    return str(uuid4())


@pytest.fixture
def mock_collection_response(collection_id):
    """Mock collection response data"""
    return {
        "id": collection_id,  # Already string from fixture
        "user_id": str(uuid4()),
        "name": "Test Collection",
        "description": "Test description",
        "metadata": {"test": "data"},
        "config": {},
        "document_count": 0,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": None,
    }


@pytest.fixture
def mock_document_response(document_id, collection_id):
    """Mock document response data"""
    return {
        "id": document_id,  # Already string from fixture
        "collection_id": collection_id,  # Already string from fixture
        "user_id": str(uuid4()),
        "title": "Test Document",
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "content_hash": "abc123",
        "unique_identifier_hash": None,
        "status": "completed",
        "metadata_": {"test": "data"},
        "processing_info": {},
        "created_at": "2024-01-01T00:00:00",
        "updated_at": None,
    }


@pytest.fixture
def mock_retrieval_response():
    """Mock retrieval response data"""
    return {
        "query": "test query",
        "mode": "hybrid",
        "results": [
            {
                "chunk_id": "chunk_1",
                "content": "Test content",
                "chunk_index": 0,
                "score": 0.95,
                "metadata": {},
                "chunk_metadata": {},
                "document": {
                    "id": str(uuid4()),
                    "title": "Test Doc",
                    "filename": "test.pdf",
                    "metadata": {},
                },
                "collection_id": str(uuid4()),
            }
        ],
        "total_results": 1,
        "processing_time_ms": 42.0,
    }
