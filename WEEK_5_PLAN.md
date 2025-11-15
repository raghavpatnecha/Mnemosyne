# Week 5 Implementation Plan - Advanced RAG Features & Production Polish

**Date:** 2025-11-15
**Branch:** claude/gather-info-01DoZyMRxPMNshGrrTZEEE2m
**Status:** Planning Phase

---

## Overview

Week 5 implements **advanced RAG features and production optimizations** to significantly improve retrieval accuracy, performance, and robustness. This week focuses on:

1. **Reranking** - Cross-encoder models for better result ordering
2. **Hybrid Search in Chat** - Upgrade from semantic-only to hybrid
3. **Redis Caching** - Cache embeddings and search results
4. **Rate Limiting** - Protect API with quotas
5. **Query Reformulation** - Improve query understanding
6. **Error Handling** - Production-grade retry logic

**Expected Improvements:**
- 15-25% better retrieval accuracy (with reranking)
- 50-70% faster response times (with caching)
- Production-ready reliability (rate limiting + error handling)

---

## Architecture Changes

### Before Week 5 (Current State):

```
Chat Request
    ↓
Embed Query (OpenAI)
    ↓
Vector Search (Semantic Only)
    ↓
Build Context
    ↓
Stream Response
```

### After Week 5 (Enhanced):

```
Chat Request
    ↓
Rate Limit Check
    ↓
Query Reformulation (Optional)
    ↓
Embed Query (with Redis Cache)
    ↓
Hybrid Search (Semantic + Keyword + RRF)
    ↓
Reranking (Flashrank Cross-Encoder)
    ↓
Cache Results (Redis)
    ↓
Build Context
    ↓
Stream Response (with Retry Logic)
```

---

## Implementation Steps

### Step 1: Reranking Service

**Goal:** Improve retrieval accuracy by 15-25% using cross-encoder reranking

**Files to Create:**
- `backend/services/reranker_service.py` (180 lines)

**Implementation:**

```python
class RerankerService:
    """
    Reranking service using Flashrank cross-encoder

    Flashrank is a local, fast cross-encoder model for reranking
    - No API calls (faster, cheaper)
    - 3-5x faster than Cohere rerank
    - Good quality for most use cases
    """

    def __init__(self):
        from flashrank import Ranker
        self.ranker = Ranker(model_name="ms-marco-MultiBERT-L-12")

    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Rerank chunks using cross-encoder

        Steps:
        1. Format chunks for Flashrank
        2. Run cross-encoder scoring
        3. Sort by score
        4. Return top_k
        """
        # Format passages
        passages = [
            {"id": i, "text": chunk["content"], "meta": chunk}
            for i, chunk in enumerate(chunks)
        ]

        # Rerank
        reranked = self.ranker.rerank(query, passages)

        # Extract top_k
        results = []
        for item in reranked[:top_k]:
            chunk = item["meta"]
            chunk["rerank_score"] = item["score"]
            results.append(chunk)

        return results
```

**Integration Points:**
- `backend/services/chat_service.py` - Add reranking after vector search
- `backend/api/retrievals.py` - Add rerank parameter
- `backend/schemas/retrieval.py` - Add rerank field to request

**Configuration:**
- `RERANK_ENABLED`: bool (default True)
- `RERANK_MODEL`: str (default "ms-marco-MultiBERT-L-12")
- `RERANK_TOP_K`: int (default 10)

**Dependencies:**
- `flashrank>=0.2.0` (add to pyproject.toml)

---

### Step 2: Hybrid Search in Chat

**Goal:** Upgrade chat from semantic-only to hybrid search for better accuracy

**Files to Update:**
- `backend/services/chat_service.py` (update retrieval logic)

**Changes:**

```python
# Before (semantic only):
results = self.search_service.semantic_search(
    query_embedding=embedding,
    user_id=user_id,
    collection_id=collection_id,
    top_k=top_k * 2  # Get more for reranking
)

# After (hybrid):
results = self.search_service.hybrid_search(
    query=user_message,
    query_embedding=embedding,
    user_id=user_id,
    collection_id=collection_id,
    top_k=top_k * 2,  # Get more for reranking
    mode="hybrid"  # New parameter
)

# Add reranking
if settings.RERANK_ENABLED:
    reranker = RerankerService()
    results = reranker.rerank(
        query=user_message,
        chunks=results,
        top_k=top_k
    )
```

**Configuration:**
- `CHAT_SEARCH_MODE`: str (default "hybrid")
- `CHAT_RERANK_ENABLED`: bool (default True)

---

### Step 3: Redis Caching Layer

**Goal:** Cache embeddings and search results for 50-70% performance improvement

**Files to Create:**
- `backend/services/cache_service.py` (150 lines)

**Implementation:**

```python
class CacheService:
    """
    Redis caching for embeddings and search results

    Cache Keys:
    - embedding:{hash(text)} -> vector embedding
    - search:{hash(query+params)} -> search results
    """

    def __init__(self):
        import redis
        self.redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=False  # Binary for embeddings
        )

    # Embedding Cache
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        key = f"embedding:{self._hash(text)}"
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    def set_embedding(self, text: str, embedding: List[float], ttl: int = 86400):
        """Cache embedding (24h TTL)"""
        key = f"embedding:{self._hash(text)}"
        self.redis.setex(key, ttl, json.dumps(embedding))

    # Search Result Cache
    def get_search_results(
        self,
        query: str,
        params: Dict
    ) -> Optional[List[Dict]]:
        """Get cached search results"""
        cache_key = self._make_search_key(query, params)
        data = self.redis.get(cache_key)
        if data:
            return json.loads(data)
        return None

    def set_search_results(
        self,
        query: str,
        params: Dict,
        results: List[Dict],
        ttl: int = 3600
    ):
        """Cache search results (1h TTL)"""
        cache_key = self._make_search_key(query, params)
        self.redis.setex(cache_key, ttl, json.dumps(results))

    def _hash(self, text: str) -> str:
        """Hash text for cache key"""
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _make_search_key(self, query: str, params: Dict) -> str:
        """Make search cache key"""
        key_data = f"{query}:{json.dumps(params, sort_keys=True)}"
        return f"search:{self._hash(key_data)}"
```

**Integration Points:**
- `backend/embeddings/openai_embedder.py` - Check cache before API call
- `backend/search/vector_search.py` - Cache search results
- `backend/services/chat_service.py` - Use cached embeddings

**Configuration:**
- `CACHE_ENABLED`: bool (default True)
- `CACHE_EMBEDDING_TTL`: int (default 86400 seconds = 24h)
- `CACHE_SEARCH_TTL`: int (default 3600 seconds = 1h)

**Performance Impact:**
- Embedding cache hit: 0ms vs 100-200ms (API call saved)
- Search cache hit: 5ms vs 50-100ms (DB query saved)
- Expected cache hit rate: 40-60% (depending on query diversity)

---

### Step 4: Rate Limiting & Quota Management

**Goal:** Protect API with per-user quotas and rate limits

**Files to Create:**
- `backend/middleware/rate_limiter.py` (120 lines)
- `backend/services/quota_service.py` (100 lines)

**Implementation:**

```python
# Rate Limiter Middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL
)

# Apply to endpoints
@router.post("/chat")
@limiter.limit("10/minute")  # 10 requests per minute
async def chat(...):
    ...

@router.post("/retrievals")
@limiter.limit("100/minute")  # 100 requests per minute
async def retrieve(...):
    ...

# Quota Service
class QuotaService:
    """
    Track and enforce user quotas

    Quotas:
    - Documents uploaded per month
    - Retrievals per month
    - Chat messages per month
    """

    def __init__(self, db: Session):
        self.db = db

    def check_quota(
        self,
        user_id: UUID,
        quota_type: str,
        amount: int = 1
    ) -> bool:
        """Check if user has quota available"""
        user = self.db.query(User).filter(User.id == user_id).first()

        if quota_type == "documents":
            if user.usage_documents + amount > user.quota_documents:
                raise HTTPException(
                    status_code=429,
                    detail=f"Document quota exceeded. Limit: {user.quota_documents}"
                )

        elif quota_type == "retrievals":
            if user.usage_retrievals + amount > user.quota_retrievals:
                raise HTTPException(
                    status_code=429,
                    detail=f"Retrieval quota exceeded. Limit: {user.quota_retrievals}"
                )

        return True

    def increment_usage(
        self,
        user_id: UUID,
        quota_type: str,
        amount: int = 1
    ):
        """Increment usage counter"""
        user = self.db.query(User).filter(User.id == user_id).first()

        if quota_type == "documents":
            user.usage_documents += amount
        elif quota_type == "retrievals":
            user.usage_retrievals += amount

        self.db.commit()
```

**Database Changes:**
- Add quota fields to User model (already exists from Week 1)
- Add usage tracking fields

**Integration:**
- All API endpoints check quotas before processing
- Usage incremented after successful requests

**Configuration:**
- `RATE_LIMIT_ENABLED`: bool (default True)
- `RATE_LIMIT_CHAT`: str (default "10/minute")
- `RATE_LIMIT_RETRIEVAL`: str (default "100/minute")
- `RATE_LIMIT_UPLOAD`: str (default "20/hour")

**Dependencies:**
- `slowapi>=0.1.9` (add to pyproject.toml)

---

### Step 5: Query Reformulation Service

**Goal:** Improve query understanding and retrieval accuracy

**Files to Create:**
- `backend/services/query_reformulation.py` (140 lines)

**Implementation:**

```python
class QueryReformulationService:
    """
    Query reformulation for better retrieval

    Techniques:
    1. Query expansion (add synonyms, related terms)
    2. Query clarification (fix typos, expand acronyms)
    3. Multi-query generation (generate related queries)
    """

    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def reformulate(
        self,
        query: str,
        mode: str = "expand"
    ) -> Union[str, List[str]]:
        """
        Reformulate query based on mode

        Modes:
        - expand: Add related terms
        - clarify: Fix typos, expand acronyms
        - multi: Generate 3-5 related queries
        """

        if mode == "expand":
            return await self._expand_query(query)
        elif mode == "clarify":
            return await self._clarify_query(query)
        elif mode == "multi":
            return await self._generate_multi_queries(query)

        return query

    async def _expand_query(self, query: str) -> str:
        """Expand query with related terms"""
        prompt = f"""Expand this search query by adding relevant synonyms and related terms.
Keep it concise (max 2-3 additional terms).

Original: {query}
Expanded:"""

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )

        return response.choices[0].message.content.strip()

    async def _generate_multi_queries(self, query: str) -> List[str]:
        """Generate multiple related queries"""
        prompt = f"""Generate 3 different ways to search for this information.
Make each query unique but related.

Original: {query}

1."""

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )

        # Parse response into list
        queries = [query]  # Include original
        lines = response.choices[0].message.content.strip().split("\n")
        for line in lines:
            if line.strip() and not line.strip().startswith("#"):
                # Clean up numbering
                clean = line.strip().lstrip("123456789. ")
                if clean:
                    queries.append(clean)

        return queries[:4]  # Original + 3 generated
```

**Integration:**
- Optional parameter in chat and retrieval APIs
- Configurable via request parameter `reformulate: bool`

**Configuration:**
- `QUERY_REFORMULATION_ENABLED`: bool (default False)
- `QUERY_REFORMULATION_MODE`: str (default "expand")

**Cost Considerations:**
- Each reformulation: ~100-200 tokens (~$0.00003)
- Disable by default, enable for premium users

---

### Step 6: Advanced Error Handling & Retry Logic

**Goal:** Production-grade reliability with automatic retries

**Files to Create:**
- `backend/utils/retry.py` (100 lines)
- `backend/utils/error_handlers.py` (120 lines)

**Implementation:**

```python
# Retry Logic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class RetryableService:
    """Base class for services with retry logic"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIError, TimeoutError))
    )
    async def _call_with_retry(self, func, *args, **kwargs):
        """Call function with automatic retry"""
        return await func(*args, **kwargs)

# Error Handlers
class ErrorHandler:
    """Centralized error handling"""

    @staticmethod
    async def handle_openai_error(error: Exception) -> Dict:
        """Handle OpenAI API errors"""
        if isinstance(error, RateLimitError):
            return {
                "error": "rate_limit",
                "message": "OpenAI rate limit exceeded. Please try again in a moment.",
                "retry_after": 60
            }
        elif isinstance(error, APIError):
            return {
                "error": "api_error",
                "message": "OpenAI API error. Please try again.",
                "details": str(error)
            }
        else:
            return {
                "error": "unknown",
                "message": "An unexpected error occurred."
            }

    @staticmethod
    async def handle_database_error(error: Exception) -> Dict:
        """Handle database errors"""
        if isinstance(error, IntegrityError):
            return {
                "error": "integrity_error",
                "message": "Data integrity violation."
            }
        else:
            return {
                "error": "database_error",
                "message": "Database error occurred."
            }
```

**Integration:**
- Apply retry logic to all external API calls
- Centralized error handling in middleware
- Proper logging with structured data

**Configuration:**
- `RETRY_ENABLED`: bool (default True)
- `RETRY_MAX_ATTEMPTS`: int (default 3)
- `RETRY_EXPONENTIAL_BASE`: int (default 2)

**Dependencies:**
- `tenacity>=8.0.0` (add to pyproject.toml)

---

## File Structure (New Files)

```
mnemosyne/
├── WEEK_5_PLAN.md                          # This file
│
├── backend/
│   ├── services/
│   │   ├── reranker_service.py             # Flashrank reranking (NEW)
│   │   ├── cache_service.py                # Redis caching (NEW)
│   │   ├── quota_service.py                # Quota management (NEW)
│   │   └── query_reformulation.py          # Query reformulation (NEW)
│   │
│   ├── middleware/
│   │   └── rate_limiter.py                 # Rate limiting (NEW)
│   │
│   └── utils/
│       ├── retry.py                        # Retry logic (NEW)
│       └── error_handlers.py               # Error handling (NEW)
```

**Files to Update:**
- `backend/services/chat_service.py` - Add hybrid search + reranking
- `backend/embeddings/openai_embedder.py` - Add caching
- `backend/search/vector_search.py` - Add caching
- `backend/config.py` - Add new settings
- `backend/main.py` - Register rate limiter middleware
- `pyproject.toml` - Add dependencies

---

## Configuration Changes

**Add to `backend/config.py`:**

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Reranking
    RERANK_ENABLED: bool = True
    RERANK_MODEL: str = "ms-marco-MultiBERT-L-12"
    RERANK_TOP_K: int = 10

    # Caching
    CACHE_ENABLED: bool = True
    CACHE_EMBEDDING_TTL: int = 86400  # 24 hours
    CACHE_SEARCH_TTL: int = 3600  # 1 hour

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_CHAT: str = "10/minute"
    RATE_LIMIT_RETRIEVAL: str = "100/minute"
    RATE_LIMIT_UPLOAD: str = "20/hour"

    # Query Reformulation
    QUERY_REFORMULATION_ENABLED: bool = False  # Premium feature
    QUERY_REFORMULATION_MODE: str = "expand"

    # Retry Logic
    RETRY_ENABLED: bool = True
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_EXPONENTIAL_BASE: int = 2
```

**Add to `.env.example`:**

```
# Reranking
RERANK_ENABLED=true
RERANK_MODEL=ms-marco-MultiBERT-L-12
RERANK_TOP_K=10

# Caching
CACHE_ENABLED=true
CACHE_EMBEDDING_TTL=86400
CACHE_SEARCH_TTL=3600

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_CHAT=10/minute
RATE_LIMIT_RETRIEVAL=100/minute
RATE_LIMIT_UPLOAD=20/hour

# Query Reformulation
QUERY_REFORMULATION_ENABLED=false
QUERY_REFORMULATION_MODE=expand

# Retry Logic
RETRY_ENABLED=true
RETRY_MAX_ATTEMPTS=3
RETRY_EXPONENTIAL_BASE=2
```

---

## Dependencies to Add

**Update `pyproject.toml`:**

```toml
[tool.poetry.dependencies]
# ... existing dependencies ...

# Week 5 additions
flashrank = "^0.2.0"           # Reranking
slowapi = "^0.1.9"             # Rate limiting
tenacity = "^8.0.0"            # Retry logic
redis = "^5.0.0"               # Already exists, ensure version
```

---

## Testing Strategy

### Unit Tests

1. **RerankerService:**
   - Test reranking logic
   - Test score ordering
   - Test top_k selection

2. **CacheService:**
   - Test embedding cache hit/miss
   - Test search cache hit/miss
   - Test TTL expiration

3. **QuotaService:**
   - Test quota checking
   - Test usage incrementing
   - Test quota exceeded errors

4. **QueryReformulationService:**
   - Test query expansion
   - Test multi-query generation
   - Test mode selection

### Integration Tests

1. **Chat with Reranking:**
   - Test end-to-end chat with reranking
   - Verify improved accuracy

2. **Caching Performance:**
   - Test cache hit performance
   - Measure speed improvement

3. **Rate Limiting:**
   - Test rate limit enforcement
   - Test error responses

4. **Quota Management:**
   - Test quota checking
   - Test quota exceeded scenarios

### Performance Tests

1. **Latency:**
   - Measure p50, p95, p99 latencies
   - Compare with/without caching

2. **Cache Hit Rate:**
   - Track cache hit percentage
   - Optimize TTL values

3. **Throughput:**
   - Test concurrent requests
   - Verify rate limiting works

---

## Success Criteria

1. ✓ Reranking service implemented with Flashrank
2. ✓ Hybrid search enabled in chat API
3. ✓ Redis caching working for embeddings and results
4. ✓ Rate limiting active on all endpoints
5. ✓ Quota management enforced
6. ✓ Query reformulation service (optional feature)
7. ✓ Retry logic on all external API calls
8. ✓ Error handling with proper logging
9. ✓ 15-25% improvement in retrieval accuracy
10. ✓ 50-70% reduction in average latency (with cache hits)

---

## Performance Expectations

### Before Week 5:
- Average chat latency: 4-7s
- Embedding generation: 100-200ms per query
- Search latency: 50-100ms
- No retry logic
- No rate limiting

### After Week 5:
- Average chat latency: 2-4s (with caching)
- Embedding generation: 5ms (cached) or 100-200ms (miss)
- Search latency: 5ms (cached) or 50-100ms (miss)
- Reranking: +100-150ms
- Automatic retries on failures
- Rate limiting active

**Net Improvement:**
- 40-60% faster with good cache hit rate
- 15-25% more accurate with reranking
- Production-ready reliability

---

## Implementation Timeline

**Day 1: Reranking + Hybrid Search**
- Create RerankerService
- Update ChatService to use hybrid search
- Add reranking to retrieval pipeline
- Test improvements

**Day 2: Redis Caching**
- Create CacheService
- Integrate with OpenAIEmbedder
- Integrate with VectorSearchService
- Measure performance gains

**Day 3: Rate Limiting + Quotas**
- Add SlowAPI middleware
- Create QuotaService
- Integrate with all endpoints
- Test rate limiting

**Day 4: Query Reformulation + Error Handling**
- Create QueryReformulationService
- Create retry utilities
- Create error handlers
- Add structured logging

**Day 5: Testing + Documentation**
- Write unit tests
- Write integration tests
- Update API documentation
- Create Week 5 summary

**Total: 5 days, 25-30 hours**

---

## Notes

### Why Flashrank over Cohere Rerank?

**Flashrank (Local):**
- ✅ No API calls (faster, cheaper)
- ✅ 3-5x faster than Cohere
- ✅ No rate limits
- ✅ Privacy (no data sent externally)
- ❌ Slightly lower quality than Cohere

**Cohere Rerank (API):**
- ✅ Better quality
- ❌ Costs $1 per 1000 rerank operations
- ❌ API latency (~200-300ms)
- ❌ Rate limits

**Decision:** Use Flashrank by default, allow Cohere as premium option

### Caching Strategy

**What to Cache:**
- ✅ Query embeddings (high hit rate for common queries)
- ✅ Search results (high hit rate for similar searches)
- ❌ LLM responses (too diverse, low hit rate)

**TTL Values:**
- Embeddings: 24h (semantic meaning doesn't change)
- Search results: 1h (allow for data updates)

### Rate Limiting Strategy

**Tiers:**
- Free: 10 chat/min, 100 retrieval/min, 20 upload/hour
- Pro: 50 chat/min, 500 retrieval/min, 100 upload/hour
- Enterprise: Custom

**Implementation:** SlowAPI with Redis backend

---

## Risks & Mitigations

**Risk 1:** Flashrank model download size (~400MB)
- **Mitigation:** Download during Docker build, not runtime

**Risk 2:** Redis memory usage with caching
- **Mitigation:** Set TTL, use LRU eviction policy

**Risk 3:** Query reformulation adds latency
- **Mitigation:** Make it optional, cache reformulations

**Risk 4:** Rate limiting too strict
- **Mitigation:** Start conservative, adjust based on usage

---

## Summary

Week 5 transforms Mnemosyne from a functional RAG system to a **production-ready platform** with advanced features:

1. **Better Accuracy:** Reranking + hybrid search
2. **Better Performance:** Redis caching
3. **Better Reliability:** Retry logic + error handling
4. **Production Ready:** Rate limiting + quotas

**Next:** After Week 5, we'll have a solid foundation for Week 6+ (SDKs, connectors, advanced features).
