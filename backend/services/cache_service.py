"""
Redis Caching Service for performance optimization

Caches embeddings and search results to reduce latency and API costs.
Expected performance improvement: 50-70% with good cache hit rates.
"""

from typing import List, Dict, Optional, Any
import json
import hashlib
import logging
from backend.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis caching for embeddings and search results

    Cache Keys:
    - embedding:{hash} -> vector embedding (24h TTL)
    - search:{hash} -> search results (1h TTL)
    - query_reform:{hash} -> reformulated query (24h TTL)

    Performance Impact:
    - Embedding cache hit: 0ms vs 100-200ms (OpenAI API)
    - Search cache hit: 5ms vs 50-100ms (DB query)
    - Expected hit rate: 40-60% (depends on query diversity)
    """

    def __init__(self):
        """Initialize Redis connection"""
        self.redis = None
        self.enabled = settings.CACHE_ENABLED

        if self.enabled:
            try:
                import redis
                self.redis = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=False,  # Binary data for embeddings
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis.ping()
                logger.info(f"Cache service connected to Redis: {settings.REDIS_URL}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
                self.redis = None
                self.enabled = False

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text

        Args:
            text: Text to get embedding for

        Returns:
            Embedding vector or None if not cached
        """
        if not self.enabled or not self.redis:
            return None

        try:
            key = self._make_embedding_key(text)
            data = self.redis.get(key)

            if data:
                embedding = json.loads(data.decode('utf-8'))
                logger.debug(f"Embedding cache HIT for text hash: {self._hash(text)[:8]}")
                return embedding

            logger.debug(f"Embedding cache MISS for text hash: {self._hash(text)[:8]}")
            return None

        except Exception as e:
            logger.error(f"Error getting embedding from cache: {e}")
            return None

    def set_embedding(
        self,
        text: str,
        embedding: List[float],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache embedding for text

        Args:
            text: Text that was embedded
            embedding: Embedding vector
            ttl: Time to live in seconds (default: CACHE_EMBEDDING_TTL)

        Returns:
            True if cached successfully
        """
        if not self.enabled or not self.redis:
            return False

        try:
            key = self._make_embedding_key(text)
            ttl = ttl or settings.CACHE_EMBEDDING_TTL

            # Serialize embedding to JSON
            data = json.dumps(embedding).encode('utf-8')

            # Set with TTL
            self.redis.setex(key, ttl, data)

            logger.debug(f"Cached embedding for text hash: {self._hash(text)[:8]}")
            return True

        except Exception as e:
            logger.error(f"Error setting embedding in cache: {e}")
            return False

    def get_search_results(
        self,
        query: str,
        params: Dict[str, Any]
    ) -> Optional[List[Dict]]:
        """
        Get cached search results

        Args:
            query: Search query
            params: Search parameters (mode, top_k, filters, etc.)

        Returns:
            Cached search results or None
        """
        if not self.enabled or not self.redis:
            return None

        try:
            key = self._make_search_key(query, params)
            data = self.redis.get(key)

            if data:
                results = json.loads(data.decode('utf-8'))
                logger.debug(f"Search cache HIT for query: {query[:30]}...")
                return results

            logger.debug(f"Search cache MISS for query: {query[:30]}...")
            return None

        except Exception as e:
            logger.error(f"Error getting search results from cache: {e}")
            return None

    def set_search_results(
        self,
        query: str,
        params: Dict[str, Any],
        results: List[Dict],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache search results

        Args:
            query: Search query
            params: Search parameters
            results: Search results to cache
            ttl: Time to live in seconds (default: CACHE_SEARCH_TTL)

        Returns:
            True if cached successfully
        """
        if not self.enabled or not self.redis:
            return False

        try:
            key = self._make_search_key(query, params)
            ttl = ttl or settings.CACHE_SEARCH_TTL

            # Serialize results to JSON
            data = json.dumps(results).encode('utf-8')

            # Set with TTL
            self.redis.setex(key, ttl, data)

            logger.debug(f"Cached search results for query: {query[:30]}...")
            return True

        except Exception as e:
            logger.error(f"Error setting search results in cache: {e}")
            return False

    def get_reformulated_query(self, query: str, mode: str) -> Optional[str]:
        """Get cached reformulated query"""
        if not self.enabled or not self.redis:
            return None

        try:
            key = f"query_reform:{self._hash(query + mode)}"
            data = self.redis.get(key)

            if data:
                reformulated = data.decode('utf-8')
                logger.debug(f"Query reformulation cache HIT")
                return reformulated

            return None

        except Exception as e:
            logger.error(f"Error getting reformulated query from cache: {e}")
            return None

    def set_reformulated_query(
        self,
        query: str,
        mode: str,
        reformulated: str,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache reformulated query"""
        if not self.enabled or not self.redis:
            return False

        try:
            key = f"query_reform:{self._hash(query + mode)}"
            ttl = ttl or settings.CACHE_EMBEDDING_TTL  # Same TTL as embeddings

            self.redis.setex(key, ttl, reformulated.encode('utf-8'))
            logger.debug(f"Cached reformulated query")
            return True

        except Exception as e:
            logger.error(f"Error setting reformulated query in cache: {e}")
            return False

    def invalidate_search_cache(self, user_id: str) -> int:
        """
        Invalidate all search cache for a user

        Called when user's documents change

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.redis:
            return 0

        try:
            pattern = f"search:*user:{user_id}*"
            keys = self.redis.keys(pattern)

            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} search cache entries for user {user_id}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Error invalidating search cache: {e}")
            return 0

    def clear_all(self) -> bool:
        """Clear all cache (use with caution)"""
        if not self.enabled or not self.redis:
            return False

        try:
            self.redis.flushdb()
            logger.warning("Cleared all cache")
            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled or not self.redis:
            return {"enabled": False}

        try:
            info = self.redis.info()
            return {
                "enabled": True,
                "total_keys": info.get("db0", {}).get("keys", 0),
                "used_memory": info.get("used_memory_human"),
                "hit_rate": info.get("keyspace_hits", 0) / max(
                    info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1),
                    1
                )
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"enabled": True, "error": str(e)}

    # Private helper methods

    def _make_embedding_key(self, text: str) -> str:
        """Generate cache key for embedding"""
        text_hash = self._hash(text)
        return f"embedding:{text_hash}"

    def _make_search_key(self, query: str, params: Dict[str, Any]) -> str:
        """Generate cache key for search results"""
        # Sort params for consistent hashing
        params_str = json.dumps(params, sort_keys=True)
        combined = f"{query}:{params_str}"
        key_hash = self._hash(combined)
        return f"search:{key_hash}"

    def _hash(self, text: str) -> str:
        """
        Generate hash for cache key

        Issue #9 fix: Use full SHA-256 hash (64 chars) to prevent collisions
        Previous 16-char truncation had 64-bit space with ~1000 collisions at 1M queries
        Full hash provides 256-bit space with negligible collision probability
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def is_available(self) -> bool:
        """Check if cache is available"""
        return self.enabled and self.redis is not None
