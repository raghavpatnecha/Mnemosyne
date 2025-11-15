"""
Unit tests for OpenAIEmbedder

Tests:
- Single text embedding with caching
- Batch embedding generation
- Cache hit and miss scenarios
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from backend.embeddings.openai_embedder import OpenAIEmbedder


@pytest.mark.unit
@pytest.mark.asyncio
class TestOpenAIEmbedder:
    """Test suite for OpenAIEmbedder"""

    @patch('backend.embeddings.openai_embedder.settings')
    @patch('backend.embeddings.openai_embedder.AsyncOpenAI')
    @patch('backend.embeddings.openai_embedder.CacheService')
    def test_init(self, mock_cache_class, mock_openai_class, mock_settings):
        """Test embedder initialization"""
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.EMBEDDING_MODEL = "text-embedding-3-large"
        mock_settings.EMBEDDING_DIMENSIONS = 1536

        embedder = OpenAIEmbedder()

        assert embedder.model == "text-embedding-3-large"
        assert embedder.dimensions == 1536
        mock_openai_class.assert_called_once_with(api_key="test_key")

    @patch('backend.embeddings.openai_embedder.AsyncOpenAI')
    @patch('backend.embeddings.openai_embedder.CacheService')
    async def test_embed_batch(self, mock_cache_class, mock_openai_class):
        """Test batch embedding generation"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock embeddings response
        mock_response = MagicMock()
        mock_item1 = MagicMock()
        mock_item1.embedding = [0.1] * 1536
        mock_item2 = MagicMock()
        mock_item2.embedding = [0.2] * 1536
        mock_response.data = [mock_item1, mock_item2]

        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        embedder = OpenAIEmbedder()
        embedder.client = mock_client

        texts = ["text 1", "text 2"]
        embeddings = await embedder.embed_batch(texts)

        assert len(embeddings) == 2
        assert embeddings[0] == [0.1] * 1536
        assert embeddings[1] == [0.2] * 1536
        mock_client.embeddings.create.assert_called_once()

    @patch('backend.embeddings.openai_embedder.AsyncOpenAI')
    @patch('backend.embeddings.openai_embedder.CacheService')
    async def test_embed_batch_large(self, mock_cache_class, mock_openai_class):
        """Test batch embedding with batching (>100 texts)"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock embeddings response
        def create_mock_response(texts):
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1] * 1536)
                for _ in texts
            ]
            return mock_response

        mock_client.embeddings.create = AsyncMock(side_effect=create_mock_response)

        embedder = OpenAIEmbedder()
        embedder.client = mock_client

        # 150 texts should trigger 2 batches
        texts = [f"text {i}" for i in range(150)]
        embeddings = await embedder.embed_batch(texts)

        assert len(embeddings) == 150
        # Should be called twice (100 + 50)
        assert mock_client.embeddings.create.call_count == 2

    @patch('backend.embeddings.openai_embedder.AsyncOpenAI')
    async def test_embed_cache_hit(self, mock_openai_class):
        """Test embedding with cache hit"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        embedder = OpenAIEmbedder()
        embedder.client = mock_client

        # Mock cache hit
        cached_embedding = [0.5] * 1536
        embedder.cache.get_embedding = Mock(return_value=cached_embedding)

        embedding = await embedder.embed("test text")

        assert embedding == cached_embedding
        # Should not call OpenAI API
        mock_client.embeddings.create.assert_not_called()

    @patch('backend.embeddings.openai_embedder.AsyncOpenAI')
    async def test_embed_cache_miss(self, mock_openai_class):
        """Test embedding with cache miss"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock embeddings response
        mock_response = MagicMock()
        mock_item = MagicMock()
        mock_item.embedding = [0.1] * 1536
        mock_response.data = [mock_item]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        embedder = OpenAIEmbedder()
        embedder.client = mock_client

        # Mock cache miss
        embedder.cache.get_embedding = Mock(return_value=None)
        embedder.cache.set_embedding = Mock(return_value=True)

        embedding = await embedder.embed("test text")

        assert embedding == [0.1] * 1536
        # Should call OpenAI API
        mock_client.embeddings.create.assert_called_once()
        # Should cache result
        embedder.cache.set_embedding.assert_called_once_with(
            "test text",
            [0.1] * 1536
        )

    @patch('backend.embeddings.openai_embedder.AsyncOpenAI')
    @patch('backend.embeddings.openai_embedder.CacheService')
    async def test_embed_batch_with_model_params(self, mock_cache_class, mock_openai_class):
        """Test batch embedding with correct model parameters"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_item = MagicMock()
        mock_item.embedding = [0.1] * 1536
        mock_response.data = [mock_item]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        embedder = OpenAIEmbedder()
        embedder.client = mock_client
        embedder.model = "text-embedding-3-large"
        embedder.dimensions = 1536

        await embedder.embed_batch(["test"])

        mock_client.embeddings.create.assert_called_with(
            model="text-embedding-3-large",
            input=["test"],
            dimensions=1536
        )

    @patch('backend.embeddings.openai_embedder.AsyncOpenAI')
    @patch('backend.embeddings.openai_embedder.CacheService')
    async def test_embed_empty_text(self, mock_cache_class, mock_openai_class):
        """Test embedding empty text"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_item = MagicMock()
        mock_item.embedding = [0.0] * 1536
        mock_response.data = [mock_item]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        embedder = OpenAIEmbedder()
        embedder.client = mock_client
        embedder.cache.get_embedding = Mock(return_value=None)

        embedding = await embedder.embed("")

        assert len(embedding) == 1536
        mock_client.embeddings.create.assert_called_once()
