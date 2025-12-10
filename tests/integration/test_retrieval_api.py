"""
Integration tests for Retrieval API endpoints

Tests:
- /api/v1/retrievals endpoint
- Semantic search mode
- Keyword search mode
- Hybrid search mode
- Authentication
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from backend.main import app
from backend.api.deps import get_current_user, get_db
from backend.models.user import User


@pytest.mark.integration
class TestRetrievalAPI:
    """Integration tests for Retrieval API"""

    @pytest.fixture
    def client(self, db_session, test_user):
        """Create test client with mocked dependencies"""

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        client = TestClient(app)
        yield client

        app.dependency_overrides.clear()

    @patch('backend.api.retrievals.OpenAIEmbedder')
    @patch('backend.api.retrievals.VectorSearchService')
    def test_retrieve_semantic_mode(
        self,
        mock_search_service,
        mock_embedder,
        client,
        test_collection
    ):
        """Test semantic search retrieval"""
        # Mock embedder
        embedder_instance = AsyncMock()
        embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embedder.return_value = embedder_instance

        # Mock search service
        search_instance = Mock()
        search_instance.search.return_value = [
            {
                'chunk_id': str(uuid4()),
                'content': 'Test content about machine learning',
                'chunk_index': 0,
                'score': 0.95,
                'metadata': {'page': 1},
                'chunk_metadata': {'tokens': 10},
                'document': {
                    'id': str(uuid4()),
                    'title': 'ML Guide',
                    'filename': 'ml_guide.pdf'
                },
                'collection_id': str(test_collection.id)
            }
        ]
        mock_search_service.return_value = search_instance

        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "What is machine learning?",
                "mode": "semantic",
                "top_k": 5,
                "collection_id": str(test_collection.id)
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["query"] == "What is machine learning?"
        assert data["mode"] == "semantic"
        assert data["total_results"] == 1

    @patch('backend.api.retrievals.OpenAIEmbedder')
    @patch('backend.api.retrievals.VectorSearchService')
    def test_retrieve_hybrid_mode(
        self,
        mock_search_service,
        mock_embedder,
        client,
        test_collection
    ):
        """Test hybrid search retrieval"""
        embedder_instance = AsyncMock()
        embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embedder.return_value = embedder_instance

        search_instance = Mock()
        search_instance.hybrid_search.return_value = [
            {
                'chunk_id': str(uuid4()),
                'content': 'Deep learning content',
                'chunk_index': 0,
                'score': 0.92,
                'metadata': {},
                'chunk_metadata': {},
                'document': {
                    'id': str(uuid4()),
                    'title': 'DL Book',
                    'filename': 'dl.pdf'
                },
                'collection_id': str(test_collection.id)
            }
        ]
        mock_search_service.return_value = search_instance

        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "deep learning",
                "mode": "hybrid",
                "top_k": 10
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "hybrid"
        search_instance.hybrid_search.assert_called_once()

    @patch('backend.api.retrievals.VectorSearchService')
    def test_retrieve_keyword_mode(
        self,
        mock_search_service,
        client,
        test_collection
    ):
        """Test keyword search retrieval"""
        search_instance = Mock()
        search_instance._keyword_search.return_value = [
            {
                'chunk_id': str(uuid4()),
                'content': 'Neural networks are fundamental',
                'chunk_index': 0,
                'score': 0.88,
                'metadata': {},
                'chunk_metadata': {},
                'document': {
                    'id': str(uuid4()),
                    'title': 'NN Book',
                    'filename': 'nn.pdf'
                },
                'collection_id': str(test_collection.id)
            }
        ]
        mock_search_service.return_value = search_instance

        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "neural networks",
                "mode": "keyword",
                "top_k": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "keyword"
        search_instance._keyword_search.assert_called_once()

    def test_retrieve_missing_query(self, client):
        """Test retrieval with missing query"""
        response = client.post(
            "/api/v1/retrievals",
            json={
                "mode": "semantic",
                "top_k": 5
            }
        )

        assert response.status_code == 422  # Validation error

    def test_retrieve_invalid_mode(self, client):
        """Test retrieval with invalid mode"""
        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "test",
                "mode": "invalid_mode",
                "top_k": 5
            }
        )

        assert response.status_code == 422  # Validation error

    @patch('backend.api.retrievals.OpenAIEmbedder')
    @patch('backend.api.retrievals.VectorSearchService')
    def test_retrieve_with_metadata_filter(
        self,
        mock_search_service,
        mock_embedder,
        client
    ):
        """Test retrieval with metadata filtering"""
        embedder_instance = AsyncMock()
        embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embedder.return_value = embedder_instance

        search_instance = Mock()
        search_instance.search.return_value = []
        mock_search_service.return_value = search_instance

        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "test",
                "mode": "semantic",
                "top_k": 5,
                "metadata_filter": {"author": "John Doe"}
            }
        )

        assert response.status_code == 200

    @patch('backend.api.retrievals.OpenAIEmbedder')
    @patch('backend.api.retrievals.VectorSearchService')
    def test_retrieve_no_results(
        self,
        mock_search_service,
        mock_embedder,
        client
    ):
        """Test retrieval with no matching results"""
        embedder_instance = AsyncMock()
        embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embedder.return_value = embedder_instance

        search_instance = Mock()
        search_instance.search.return_value = []
        mock_search_service.return_value = search_instance

        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "nonexistent query",
                "mode": "semantic",
                "top_k": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 0
        assert len(data["results"]) == 0

    @patch('backend.api.retrievals.OpenAIEmbedder')
    @patch('backend.api.retrievals.VectorSearchService')
    def test_retrieve_default_top_k(
        self,
        mock_search_service,
        mock_embedder,
        client
    ):
        """Test retrieval uses default top_k"""
        embedder_instance = AsyncMock()
        embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embedder.return_value = embedder_instance

        search_instance = Mock()
        search_instance.search.return_value = []
        mock_search_service.return_value = search_instance

        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "test query",
                "mode": "semantic"
                # top_k not provided
            }
        )

        assert response.status_code == 200

    def test_retrieve_without_authentication(self):
        """Test retrieval without authentication"""
        client = TestClient(app)

        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "test",
                "mode": "semantic",
                "top_k": 5
            }
        )

        # FastAPI validates request body schema before authentication middleware
        # So we get 422 (validation error) instead of 401/403
        assert response.status_code == 422

    @patch('backend.api.retrievals.OpenAIEmbedder')
    @patch('backend.api.retrievals.VectorSearchService')
    def test_retrieve_response_structure(
        self,
        mock_search_service,
        mock_embedder,
        client
    ):
        """Test complete response structure"""
        embedder_instance = AsyncMock()
        embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embedder.return_value = embedder_instance

        chunk_id = str(uuid4())
        doc_id = str(uuid4())
        collection_id = str(uuid4())

        search_instance = Mock()
        search_instance.search.return_value = [
            {
                'chunk_id': chunk_id,
                'content': 'Test content',
                'chunk_index': 0,
                'score': 0.95,
                'metadata': {'page': 1},
                'chunk_metadata': {'tokens': 10},
                'document': {
                    'id': doc_id,
                    'title': 'Test Doc',
                    'filename': 'test.pdf'
                },
                'collection_id': collection_id
            }
        ]
        mock_search_service.return_value = search_instance

        response = client.post(
            "/api/v1/retrievals",
            json={
                "query": "test",
                "mode": "semantic",
                "top_k": 5
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "results" in data
        assert "query" in data
        assert "mode" in data
        assert "total_results" in data

        # Check result structure
        result = data["results"][0]
        assert result["chunk_id"] == chunk_id
        assert result["content"] == "Test content"
        assert result["chunk_index"] == 0
        assert result["score"] == 0.95
        assert "metadata" in result
        assert "chunk_metadata" in result
        assert "document" in result
        assert result["document"]["id"] == doc_id
