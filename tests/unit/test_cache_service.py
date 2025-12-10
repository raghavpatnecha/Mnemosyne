"""
Unit tests for CacheService

Tests:
- Redis connection initialization
- Embedding caching and retrieval
- Search results caching and retrieval
- Query reformulation caching
- Cache invalidation
- Cache statistics
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json

from backend.services.cache_service import CacheService


@pytest.mark.unit
class TestCacheService:
    """Test suite for CacheService"""

    @patch('backend.services.cache_service.settings')
    @patch('redis.from_url')
    def test_init_enabled(self, mock_from_url, mock_settings):
        """Test initialization with caching enabled"""
        mock_settings.CACHE_ENABLED = True
        mock_settings.REDIS_URL = "redis://localhost:6379/0"

        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_from_url.return_value = mock_redis_client

        service = CacheService()

        assert service.enabled is True
        assert service.redis is not None
        mock_redis_client.ping.assert_called_once()

    @patch('backend.services.cache_service.settings')
    def test_init_disabled(self, mock_settings):
        """Test initialization with caching disabled"""
        mock_settings.CACHE_ENABLED = False

        service = CacheService()

        assert service.enabled is False
        assert service.redis is None

    @patch('backend.services.cache_service.settings')
    @patch('redis.from_url')
    def test_init_connection_failure(self, mock_from_url, mock_settings):
        """Test initialization with Redis connection failure"""
        mock_settings.CACHE_ENABLED = True
        mock_settings.REDIS_URL = "redis://localhost:6379/0"

        mock_redis_client = MagicMock()
        mock_redis_client.ping.side_effect = Exception("Connection failed")
        mock_from_url.return_value = mock_redis_client

        service = CacheService()

        assert service.enabled is False
        assert service.redis is None

    def test_get_embedding_cache_hit(self, mock_redis):
        """Test getting cached embedding"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        embedding = [0.1, 0.2, 0.3]
        mock_redis.get.return_value = json.dumps(embedding).encode('utf-8')

        result = service.get_embedding("test text")

        assert result == embedding
        assert mock_redis.get.called

    def test_get_embedding_cache_miss(self, mock_redis):
        """Test cache miss for embedding"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        mock_redis.get.return_value = None

        result = service.get_embedding("test text")

        assert result is None

    def test_get_embedding_disabled(self):
        """Test getting embedding when cache is disabled"""
        service = CacheService()
        service.enabled = False
        service.redis = None

        result = service.get_embedding("test text")

        assert result is None

    @patch('backend.services.cache_service.settings')
    def test_set_embedding(self, mock_settings, mock_redis):
        """Test caching embedding"""
        mock_settings.CACHE_EMBEDDING_TTL = 86400

        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        embedding = [0.1, 0.2, 0.3]
        result = service.set_embedding("test text", embedding)

        assert result is True
        assert mock_redis.setex.called

    def test_set_embedding_disabled(self):
        """Test setting embedding when cache is disabled"""
        service = CacheService()
        service.enabled = False
        service.redis = None

        result = service.set_embedding("test", [0.1, 0.2])

        assert result is False

    def test_get_search_results_cache_hit(self, mock_redis):
        """Test getting cached search results"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        results = [{'chunk_id': '1', 'content': 'test'}]
        mock_redis.get.return_value = json.dumps(results).encode('utf-8')

        result = service.get_search_results(
            "test query",
            {"mode": "hybrid", "top_k": 10}
        )

        assert result == results

    def test_get_search_results_cache_miss(self, mock_redis):
        """Test cache miss for search results"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        mock_redis.get.return_value = None

        result = service.get_search_results(
            "test query",
            {"mode": "hybrid"}
        )

        assert result is None

    @patch('backend.services.cache_service.settings')
    def test_set_search_results(self, mock_settings, mock_redis):
        """Test caching search results"""
        mock_settings.CACHE_SEARCH_TTL = 3600

        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        results = [{'chunk_id': '1', 'content': 'test'}]
        result = service.set_search_results(
            "test query",
            {"mode": "hybrid"},
            results
        )

        assert result is True
        assert mock_redis.setex.called

    def test_get_reformulated_query_cache_hit(self, mock_redis):
        """Test getting cached reformulated query"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        reformulated = "expanded test query"
        mock_redis.get.return_value = reformulated.encode('utf-8')

        result = service.get_reformulated_query("test query", "expand")

        assert result == reformulated

    def test_get_reformulated_query_cache_miss(self, mock_redis):
        """Test cache miss for reformulated query"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        mock_redis.get.return_value = None

        result = service.get_reformulated_query("test query", "expand")

        assert result is None

    @patch('backend.services.cache_service.settings')
    def test_set_reformulated_query(self, mock_settings, mock_redis):
        """Test caching reformulated query"""
        mock_settings.CACHE_EMBEDDING_TTL = 86400

        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        result = service.set_reformulated_query(
            "test query",
            "expand",
            "expanded test query"
        )

        assert result is True
        assert mock_redis.setex.called

    def test_invalidate_search_cache(self, mock_redis):
        """Test invalidating search cache for a user"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        mock_redis.keys.return_value = ['key1', 'key2', 'key3']
        mock_redis.delete.return_value = 3

        result = service.invalidate_search_cache("user_123")

        assert result == 3
        mock_redis.keys.assert_called_once()
        mock_redis.delete.assert_called_once_with('key1', 'key2', 'key3')

    def test_invalidate_search_cache_no_keys(self, mock_redis):
        """Test invalidating cache when no keys exist"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        mock_redis.keys.return_value = []

        result = service.invalidate_search_cache("user_123")

        assert result == 0
        mock_redis.delete.assert_not_called()

    def test_clear_all(self, mock_redis):
        """Test clearing all cache"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        mock_redis.flushdb.return_value = True

        result = service.clear_all()

        assert result is True
        mock_redis.flushdb.assert_called_once()

    def test_clear_all_disabled(self):
        """Test clearing cache when disabled"""
        service = CacheService()
        service.enabled = False
        service.redis = None

        result = service.clear_all()

        assert result is False

    def test_get_stats(self, mock_redis):
        """Test getting cache statistics"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        stats = service.get_stats()

        assert stats['enabled'] is True
        assert 'total_keys' in stats
        assert 'used_memory' in stats
        assert 'hit_rate' in stats

    def test_get_stats_disabled(self):
        """Test getting stats when disabled"""
        service = CacheService()
        service.enabled = False
        service.redis = None

        stats = service.get_stats()

        assert stats['enabled'] is False

    def test_is_available(self, mock_redis):
        """Test checking cache availability"""
        service = CacheService()
        service.enabled = True
        service.redis = mock_redis

        assert service.is_available() is True

    def test_is_available_disabled(self):
        """Test availability when disabled"""
        service = CacheService()
        service.enabled = False
        service.redis = None

        assert service.is_available() is False

    def test_make_embedding_key(self):
        """Test embedding key generation"""
        service = CacheService()

        key1 = service._make_embedding_key("test text")
        key2 = service._make_embedding_key("test text")
        key3 = service._make_embedding_key("different text")

        assert key1 == key2  # Same text = same key
        assert key1 != key3  # Different text = different key
        assert key1.startswith("embedding:")

    def test_make_search_key(self):
        """Test search key generation"""
        service = CacheService()

        params1 = {"mode": "hybrid", "top_k": 10}
        params2 = {"top_k": 10, "mode": "hybrid"}  # Different order
        params3 = {"mode": "semantic", "top_k": 10}  # Different values

        key1 = service._make_search_key("query", params1)
        key2 = service._make_search_key("query", params2)
        key3 = service._make_search_key("query", params3)

        assert key1 == key2  # Same params (different order) = same key
        assert key1 != key3  # Different params = different key
        assert key1.startswith("search:")
