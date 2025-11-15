"""
Unit tests for QueryReformulationService

Tests:
- Query expansion
- Query clarification
- Multi-query generation
- Context-aware reformulation
- Caching behavior
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from backend.services.query_reformulation import QueryReformulationService


@pytest.mark.unit
@pytest.mark.asyncio
class TestQueryReformulationService:
    """Test suite for QueryReformulationService"""

    @patch('backend.services.query_reformulation.settings')
    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    def test_init(self, mock_cache_class, mock_openai_class, mock_settings):
        """Test service initialization"""
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.QUERY_REFORMULATION_ENABLED = True

        service = QueryReformulationService()

        assert service.enabled is True
        mock_openai_class.assert_called_once_with(api_key="test_key")

    @patch('backend.services.query_reformulation.settings')
    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_reformulate_disabled(self, mock_cache_class, mock_openai_class, mock_settings):
        """Test reformulation when disabled"""
        mock_settings.QUERY_REFORMULATION_ENABLED = False

        service = QueryReformulationService()
        service.enabled = False

        result = await service.reformulate("test query", mode="expand")

        assert result == "test query"

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_expand_query(self, mock_cache_class, mock_openai_class):
        """Test query expansion"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(
                content="ML models machine learning algorithms"
            ))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(return_value=None)
        service.cache.set_reformulated_query = Mock(return_value=True)

        result = await service.reformulate("ML models", mode="expand")

        assert result == "ML models machine learning algorithms"
        mock_client.chat.completions.create.assert_called_once()
        service.cache.set_reformulated_query.assert_called_once()

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_clarify_query(self, mock_cache_class, mock_openai_class):
        """Test query clarification"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(
                content="Retrieval Augmented Generation implementation"
            ))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(return_value=None)
        service.cache.set_reformulated_query = Mock(return_value=True)

        result = await service.reformulate("RAG implmntation", mode="clarify")

        assert "Retrieval Augmented Generation" in result
        mock_client.chat.completions.create.assert_called_once()

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_multi_query_generation(self, mock_cache_class, mock_openai_class):
        """Test multi-query generation"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(
                content="What is Retrieval Augmented Generation?\nExplain RAG architecture\nHow does RAG work?"
            ))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(return_value=None)
        service.cache.set_reformulated_query = Mock(return_value=True)

        result = await service.reformulate("How does RAG work?", mode="multi")

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "How does RAG work?" in result  # Original query included

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_reformulate_cache_hit(self, mock_cache_class, mock_openai_class):
        """Test reformulation with cache hit"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(
            return_value="cached expanded query"
        )

        result = await service.reformulate("test query", mode="expand")

        assert result == "cached expanded query"
        # Should not call OpenAI API
        mock_client.chat.completions.create.assert_not_called()

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_reformulate_multi_cache_hit(self, mock_cache_class, mock_openai_class):
        """Test multi-query reformulation with cache hit"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(
            return_value="query1|query2|query3"
        )

        result = await service.reformulate("test query", mode="multi")

        assert isinstance(result, list)
        assert result == ["query1", "query2", "query3"]

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_reformulate_unknown_mode(self, mock_cache_class, mock_openai_class):
        """Test reformulation with unknown mode"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(return_value=None)

        result = await service.reformulate("test query", mode="unknown")

        assert result == "test query"

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_reformulate_with_context(self, mock_cache_class, mock_openai_class):
        """Test context-aware reformulation"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(
                content="context-aware reformulated query"
            ))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True

        history = [
            {"role": "user", "content": "What is RAG?"},
            {"role": "assistant", "content": "RAG stands for Retrieval Augmented Generation..."}
        ]

        result = await service.reformulate_with_context(
            "How does it work?",
            history,
            mode="expand"
        )

        assert result == "context-aware reformulated query"
        mock_client.chat.completions.create.assert_called_once()

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_reformulate_with_empty_context(self, mock_cache_class, mock_openai_class):
        """Test reformulation with empty conversation history"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(return_value=None)
        service.cache.set_reformulated_query = Mock(return_value=True)

        # Mock _expand_query
        service._expand_query = AsyncMock(return_value="expanded query")

        result = await service.reformulate_with_context(
            "test query",
            [],
            mode="expand"
        )

        # Should fall back to regular reformulate
        assert result == "expanded query"

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_reformulate_error_handling(self, mock_cache_class, mock_openai_class):
        """Test error handling during reformulation"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock OpenAI to raise error
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(return_value=None)

        result = await service.reformulate("test query", mode="expand")

        # Should return original query on error
        assert result == "test query"

    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    async def test_multi_query_error_handling(self, mock_cache_class, mock_openai_class):
        """Test error handling for multi-query mode"""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        service = QueryReformulationService()
        service.client = mock_client
        service.enabled = True
        service.cache.get_reformulated_query = Mock(return_value=None)

        result = await service.reformulate("test query", mode="multi")

        # Should return list with original query on error
        assert result == ["test query"]

    @patch('backend.services.query_reformulation.settings')
    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    def test_is_available(self, mock_cache_class, mock_openai_class, mock_settings):
        """Test availability check"""
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.QUERY_REFORMULATION_ENABLED = True

        service = QueryReformulationService()
        service.enabled = True

        assert service.is_available() is True

    @patch('backend.services.query_reformulation.settings')
    @patch('backend.services.query_reformulation.AsyncOpenAI')
    @patch('backend.services.query_reformulation.CacheService')
    def test_is_available_disabled(self, mock_cache_class, mock_openai_class, mock_settings):
        """Test availability when disabled"""
        mock_settings.QUERY_REFORMULATION_ENABLED = False

        service = QueryReformulationService()
        service.enabled = False

        assert service.is_available() is False
