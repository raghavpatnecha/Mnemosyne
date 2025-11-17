"""Unit tests for RetrievalsResource"""

import pytest
from pytest_httpx import HTTPXMock
from mnemosyne.types.retrievals import RetrievalResponse


def test_retrieve_semantic(client, httpx_mock: HTTPXMock, mock_retrieval_response):
    """Test semantic retrieval"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/retrievals",
        json=mock_retrieval_response,
    )

    results = client.retrievals.retrieve(
        query="test query",
        mode="semantic",
        top_k=10,
    )

    assert isinstance(results, RetrievalResponse)
    assert results.query == "test query"
    assert results.mode == "hybrid"  # from mock
    assert len(results.results) == 1
    assert results.results[0].score == 0.95


def test_retrieve_hybrid(client, httpx_mock: HTTPXMock, mock_retrieval_response):
    """Test hybrid retrieval"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/retrievals",
        json=mock_retrieval_response,
    )

    results = client.retrievals.retrieve(
        query="test query",
        mode="hybrid",
        top_k=5,
    )

    assert isinstance(results, RetrievalResponse)
    assert len(results.results) == 1


def test_retrieve_with_collection_filter(
    client, httpx_mock: HTTPXMock, collection_id, mock_retrieval_response
):
    """Test retrieval with collection filter"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/retrievals",
        json=mock_retrieval_response,
    )

    results = client.retrievals.retrieve(
        query="test query",
        mode="hybrid",
        top_k=10,
        collection_id=collection_id,
    )

    assert isinstance(results, RetrievalResponse)


def test_retrieve_with_metadata_filter(client, httpx_mock: HTTPXMock, mock_retrieval_response):
    """Test retrieval with metadata filter"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/retrievals",
        json=mock_retrieval_response,
    )

    results = client.retrievals.retrieve(
        query="test query",
        mode="hybrid",
        top_k=10,
        metadata_filter={"year": 2024},
    )

    assert isinstance(results, RetrievalResponse)


def test_retrieve_graph_mode(client, httpx_mock: HTTPXMock, mock_retrieval_response):
    """Test graph-based retrieval (LightRAG)"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/retrievals",
        json=mock_retrieval_response,
    )

    results = client.retrievals.retrieve(
        query="test query",
        mode="graph",
        top_k=10,
    )

    assert isinstance(results, RetrievalResponse)


def test_retrieve_hierarchical_mode(client, httpx_mock: HTTPXMock, mock_retrieval_response):
    """Test hierarchical retrieval"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/retrievals",
        json=mock_retrieval_response,
    )

    results = client.retrievals.retrieve(
        query="test query",
        mode="hierarchical",
        top_k=10,
    )

    assert isinstance(results, RetrievalResponse)
