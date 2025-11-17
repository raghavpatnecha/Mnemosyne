"""Unit tests for CollectionsResource"""

import pytest
from pytest_httpx import HTTPXMock
from mnemosyne.types.collections import CollectionResponse


def test_create_collection(client, httpx_mock: HTTPXMock, mock_collection_response):
    """Test collection creation"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/collections",
        json=mock_collection_response,
    )

    collection = client.collections.create(
        name="Test Collection",
        description="Test description",
        metadata={"test": "data"},
    )

    assert isinstance(collection, CollectionResponse)
    assert collection.name == "Test Collection"
    assert collection.description == "Test description"
    assert collection.metadata == {"test": "data"}


def test_list_collections(client, httpx_mock: HTTPXMock, mock_collection_response):
    """Test listing collections"""
    httpx_mock.add_response(
        method="GET",
        url="http://localhost:8000/collections?limit=20&offset=0",
        json={
            "data": [mock_collection_response],
            "pagination": {
                "total": 1,
                "limit": 20,
                "offset": 0,
                "has_more": False,
            },
        },
    )

    result = client.collections.list(limit=20, offset=0)

    assert len(result.data) == 1
    assert result.data[0].name == "Test Collection"
    assert result.pagination["total"] == 1


def test_get_collection(client, httpx_mock: HTTPXMock, collection_id, mock_collection_response):
    """Test getting a collection by ID"""
    httpx_mock.add_response(
        method="GET",
        url=f"http://localhost:8000/collections/{collection_id}",
        json=mock_collection_response,
    )

    collection = client.collections.get(collection_id)

    assert isinstance(collection, CollectionResponse)
    assert collection.name == "Test Collection"


def test_update_collection(client, httpx_mock: HTTPXMock, collection_id, mock_collection_response):
    """Test updating a collection"""
    updated_response = {**mock_collection_response, "name": "Updated Name"}

    httpx_mock.add_response(
        method="PATCH",
        url=f"http://localhost:8000/collections/{collection_id}",
        json=updated_response,
    )

    collection = client.collections.update(
        collection_id=collection_id,
        name="Updated Name",
    )

    assert collection.name == "Updated Name"


def test_delete_collection(client, httpx_mock: HTTPXMock, collection_id):
    """Test deleting a collection"""
    httpx_mock.add_response(
        method="DELETE",
        url=f"http://localhost:8000/collections/{collection_id}",
        status_code=204,
    )

    # Should not raise any exception
    client.collections.delete(collection_id)
