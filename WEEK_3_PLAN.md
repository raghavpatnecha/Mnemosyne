# Week 3 Implementation Plan - Vector Search + Retrieval API

**Goal:** Implement semantic search, hybrid search, and retrieval API endpoint for querying processed documents

**Status:** Planning
**Duration:** 5-7 days
**Dependencies:** Week 2 (document processing, pgvector embeddings)

---

## Overview

Week 3 focuses on **retrieval and search**:
- Vector similarity search using pgvector (cosine distance)
- Query embedding generation
- Retrieval API endpoint (POST /api/v1/retrievals)
- Hybrid search (semantic + full-text with RRF)
- Result ranking and scoring
- Metadata filtering
- NO chat API yet (Week 4)
- NO LightRAG yet (Week 4)

---

## Architecture

```
Query (POST /retrievals)
    ↓
Embed query (OpenAI text-embedding-3-large)
    ↓
Branch by mode:
    ├─ semantic: Vector search only (pgvector cosine similarity)
    ├─ keyword: Full-text search only (PostgreSQL ts_vector)
    └─ hybrid: Both searches + RRF (Reciprocal Rank Fusion)
    ↓
Apply filters (collection_id, metadata, user ownership)
    ↓
Rank and score results
    ↓
Return top_k chunks with metadata
```

---

## Database Requirements

### Existing Tables (from Week 2):
- `document_chunks`: Has embedding column (Vector 1536)
- Index: `idx_chunks_embedding` (ivfflat for cosine similarity)

### New Indexes Needed:
```sql
-- Full-text search index for hybrid mode
CREATE INDEX idx_chunks_content_fts ON document_chunks
    USING gin(to_tsvector('english', content));
```

---

## Implementation Steps (6 Steps)

### Step 1: Vector Search Service (Day 1, Morning)

**Priority:** CRITICAL - Core search functionality
**Time:** 3-4 hours

**Implementation:**

**1. Create `backend/search/vector_search.py`:**
```python
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.models.chunk import DocumentChunk
from backend.models.document import Document
from uuid import UUID


class VectorSearchService:
    """Vector similarity search using pgvector"""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query_embedding: List[float],
        collection_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        top_k: int = 10,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using cosine similarity

        Args:
            query_embedding: Query embedding vector (1536 dims)
            collection_id: Filter by collection
            user_id: Filter by user ownership
            top_k: Number of results
            metadata_filter: Metadata filters (future enhancement)

        Returns:
            List of chunks with scores and metadata
        """
        # Build query with filters
        query = self.db.query(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.chunk_index,
            DocumentChunk.metadata,
            DocumentChunk.chunk_metadata,
            DocumentChunk.document_id,
            DocumentChunk.collection_id,
            Document.title.label('document_title'),
            Document.filename.label('document_filename'),
            DocumentChunk.embedding.cosine_distance(query_embedding).label('distance')
        ).join(
            Document,
            Document.id == DocumentChunk.document_id
        )

        # Apply filters
        filters = []
        if user_id:
            filters.append(DocumentChunk.user_id == user_id)
        if collection_id:
            filters.append(DocumentChunk.collection_id == collection_id)

        if filters:
            query = query.filter(and_(*filters))

        # Order by similarity and limit
        results = query.order_by('distance').limit(top_k).all()

        # Convert to response format
        return [
            {
                'chunk_id': str(result.id),
                'content': result.content,
                'chunk_index': result.chunk_index,
                'score': 1 - result.distance,  # Convert distance to similarity score
                'metadata': result.metadata or {},
                'chunk_metadata': result.chunk_metadata or {},
                'document': {
                    'id': str(result.document_id),
                    'title': result.document_title,
                    'filename': result.document_filename,
                },
                'collection_id': str(result.collection_id)
            }
            for result in results
        ]
```

**Deliverables:**
- VectorSearchService with cosine similarity
- Filtering by user_id, collection_id
- Returns top_k results with scores

---

### Step 2: Query Embedding Service (Day 1, Afternoon)

**Priority:** HIGH - Required for query processing
**Time:** 1-2 hours

**Implementation:**

**Update `backend/embeddings/openai_embedder.py`:**
```python
# Add query-specific method
async def embed_query(self, query: str) -> List[float]:
    """Generate embedding for search query"""
    return await self.embed(query)
```

**OR Create `backend/search/query_embedder.py`:**
```python
from typing import List
from backend.embeddings.openai_embedder import OpenAIEmbedder


class QueryEmbedder:
    """Wrapper for query embedding with caching support"""

    def __init__(self):
        self.embedder = OpenAIEmbedder()

    async def embed(self, query: str) -> List[float]:
        """
        Generate embedding for query

        Args:
            query: Search query text

        Returns:
            Embedding vector (1536 dimensions)
        """
        return await self.embedder.embed(query)
```

**Deliverables:**
- Query embedding generation
- Reuse existing OpenAIEmbedder

---

### Step 3: Retrieval API Endpoint (Day 2, Morning)

**Priority:** CRITICAL - Main API endpoint
**Time:** 3-4 hours

**Implementation:**

**Create `backend/api/retrievals.py`:**
```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import asyncio

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse
)
from backend.search.vector_search import VectorSearchService
from backend.embeddings.openai_embedder import OpenAIEmbedder

router = APIRouter(prefix="/retrievals", tags=["retrievals"])


@router.post("", response_model=RetrievalResponse, status_code=status.HTTP_200_OK)
async def retrieve(
    request: RetrievalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve relevant chunks for a query

    Args:
        request: Retrieval request (query, mode, top_k, etc.)
        db: Database session
        current_user: Authenticated user

    Returns:
        RetrievalResponse: Ranked chunks with scores
    """
    # Generate query embedding
    embedder = OpenAIEmbedder()
    query_embedding = await embedder.embed(request.query)

    # Perform search
    search_service = VectorSearchService(db)

    if request.mode == "semantic":
        results = search_service.search(
            query_embedding=query_embedding,
            collection_id=request.collection_id,
            user_id=current_user.id,
            top_k=request.top_k
        )
    elif request.mode == "hybrid":
        # Week 3: Implement hybrid search
        results = search_service.hybrid_search(
            query_text=request.query,
            query_embedding=query_embedding,
            collection_id=request.collection_id,
            user_id=current_user.id,
            top_k=request.top_k
        )
    else:
        # Default to semantic
        results = search_service.search(
            query_embedding=query_embedding,
            collection_id=request.collection_id,
            user_id=current_user.id,
            top_k=request.top_k
        )

    return RetrievalResponse(
        results=results,
        query=request.query,
        mode=request.mode,
        total_results=len(results)
    )
```

**Register router in `backend/main.py`:**
```python
from backend.api import auth, collections, documents, retrievals

app.include_router(retrievals.router, prefix="/api/v1")
```

**Deliverables:**
- POST /api/v1/retrievals endpoint
- Query embedding generation
- Vector search integration
- User ownership filtering

---

### Step 4: Pydantic Schemas (Day 2, Afternoon)

**Priority:** HIGH - Request/Response validation
**Time:** 1-2 hours

**Implementation:**

**Create `backend/schemas/retrieval.py`:**
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import UUID
from enum import Enum


class RetrievalMode(str, Enum):
    """Search mode"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class RetrievalRequest(BaseModel):
    """Request schema for retrieval endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    mode: RetrievalMode = Field(default=RetrievalMode.SEMANTIC, description="Search mode")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")
    collection_id: Optional[UUID] = Field(None, description="Filter by collection")
    rerank: bool = Field(default=False, description="Enable reranking")
    metadata_filter: Optional[Dict] = Field(None, description="Metadata filters")


class ChunkResult(BaseModel):
    """Single chunk result"""
    chunk_id: str
    content: str
    chunk_index: int
    score: float = Field(..., description="Relevance score (0-1)")
    metadata: Dict
    chunk_metadata: Dict
    document: Dict = Field(..., description="Document metadata")
    collection_id: str


class RetrievalResponse(BaseModel):
    """Response schema for retrieval endpoint"""
    results: List[ChunkResult]
    query: str
    mode: str
    total_results: int
```

**Deliverables:**
- RetrievalRequest schema
- RetrievalResponse schema
- ChunkResult schema
- RetrievalMode enum

---

### Step 5: Hybrid Search (Day 3, Morning)

**Priority:** MEDIUM - Enhanced search accuracy
**Time:** 3-4 hours

**Implementation:**

**Add to `backend/search/vector_search.py`:**
```python
def hybrid_search(
    self,
    query_text: str,
    query_embedding: List[float],
    collection_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Hybrid search: Semantic + Full-text with RRF

    Args:
        query_text: Query text for full-text search
        query_embedding: Query embedding for semantic search
        collection_id: Filter by collection
        user_id: Filter by user ownership
        top_k: Number of results

    Returns:
        Merged and ranked results
    """
    # Semantic search
    semantic_results = self.search(
        query_embedding=query_embedding,
        collection_id=collection_id,
        user_id=user_id,
        top_k=top_k * 2  # Get more results for fusion
    )

    # Full-text search
    keyword_results = self._keyword_search(
        query_text=query_text,
        collection_id=collection_id,
        user_id=user_id,
        top_k=top_k * 2
    )

    # RRF (Reciprocal Rank Fusion)
    merged = self._reciprocal_rank_fusion(
        semantic_results,
        keyword_results,
        k=60  # RRF constant
    )

    return merged[:top_k]


def _keyword_search(
    self,
    query_text: str,
    collection_id: Optional[UUID],
    user_id: Optional[UUID],
    top_k: int
) -> List[Dict[str, Any]]:
    """Full-text search using PostgreSQL ts_vector"""
    from sqlalchemy import func

    query = self.db.query(
        DocumentChunk.id,
        DocumentChunk.content,
        DocumentChunk.chunk_index,
        DocumentChunk.metadata,
        DocumentChunk.chunk_metadata,
        DocumentChunk.document_id,
        DocumentChunk.collection_id,
        Document.title.label('document_title'),
        Document.filename.label('document_filename'),
        func.ts_rank(
            func.to_tsvector('english', DocumentChunk.content),
            func.plainto_tsquery('english', query_text)
        ).label('rank')
    ).join(
        Document,
        Document.id == DocumentChunk.document_id
    ).filter(
        func.to_tsvector('english', DocumentChunk.content).match(
            func.plainto_tsquery('english', query_text)
        )
    )

    # Apply filters
    if user_id:
        query = query.filter(DocumentChunk.user_id == user_id)
    if collection_id:
        query = query.filter(DocumentChunk.collection_id == collection_id)

    results = query.order_by(func.ts_rank(
        func.to_tsvector('english', DocumentChunk.content),
        func.plainto_tsquery('english', query_text)
    ).desc()).limit(top_k).all()

    return [
        {
            'chunk_id': str(result.id),
            'content': result.content,
            'chunk_index': result.chunk_index,
            'score': float(result.rank),
            'metadata': result.metadata or {},
            'chunk_metadata': result.chunk_metadata or {},
            'document': {
                'id': str(result.document_id),
                'title': result.document_title,
                'filename': result.document_filename,
            },
            'collection_id': str(result.collection_id)
        }
        for result in results
    ]


def _reciprocal_rank_fusion(
    self,
    results_a: List[Dict],
    results_b: List[Dict],
    k: int = 60
) -> List[Dict]:
    """
    Merge results using Reciprocal Rank Fusion

    RRF formula: score = sum(1 / (k + rank))

    Args:
        results_a: First result list
        results_b: Second result list
        k: RRF constant (default 60)

    Returns:
        Merged and ranked results
    """
    scores = {}

    # Score from results_a
    for rank, result in enumerate(results_a, 1):
        chunk_id = result['chunk_id']
        scores[chunk_id] = scores.get(chunk_id, {'result': result, 'score': 0})
        scores[chunk_id]['score'] += 1 / (k + rank)

    # Score from results_b
    for rank, result in enumerate(results_b, 1):
        chunk_id = result['chunk_id']
        scores[chunk_id] = scores.get(chunk_id, {'result': result, 'score': 0})
        scores[chunk_id]['score'] += 1 / (k + rank)

    # Sort by RRF score
    merged = sorted(
        scores.values(),
        key=lambda x: x['score'],
        reverse=True
    )

    # Update scores in results
    return [
        {**item['result'], 'score': item['score']}
        for item in merged
    ]
```

**Deliverables:**
- Hybrid search combining semantic + full-text
- RRF (Reciprocal Rank Fusion) for merging
- Full-text search using PostgreSQL ts_vector

---

### Step 6: Result Ranking and Metadata (Day 3, Afternoon)

**Priority:** LOW - Enhancement
**Time:** 1-2 hours

**Implementation:**

**Add helper methods to `VectorSearchService`:**
```python
def _apply_metadata_filters(
    self,
    query,
    metadata_filter: Optional[Dict]
) -> Any:
    """Apply metadata JSON filters"""
    if not metadata_filter:
        return query

    for key, value in metadata_filter.items():
        # JSON path query
        query = query.filter(
            DocumentChunk.metadata[key].astext == str(value)
        )

    return query


def _boost_scores(
    self,
    results: List[Dict],
    boost_recent: bool = True
) -> List[Dict]:
    """
    Apply score boosting strategies

    Args:
        results: Search results
        boost_recent: Boost recently created documents

    Returns:
        Results with boosted scores
    """
    if not boost_recent:
        return results

    # Simple recency boost (can be enhanced)
    from datetime import datetime, timedelta

    for result in results:
        # Boost by 10% if created in last 7 days
        # (would need to add created_at to query)
        pass

    return results
```

**Deliverables:**
- Metadata filtering
- Score boosting (basic)

---

## Week 3 Success Criteria

Week 3 is complete when:
1. POST /api/v1/retrievals endpoint works
2. Semantic search returns top_k relevant chunks
3. Query embedding generation works
4. Results include scores and document metadata
5. User ownership filtering enforced
6. Collection filtering works
7. Hybrid search combines semantic + keyword
8. RRF merging produces good results
9. API documented in OpenAPI/Swagger
10. End-to-end retrieval works

---

## Testing Strategy

### Manual Testing:

1. **Upload and process documents** (Week 2):
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -F "collection_id=$COLLECTION_ID" \
  -F "file=@document.pdf"

# Wait for processing to complete
```

2. **Semantic search**:
```bash
curl -X POST "http://localhost:8000/api/v1/retrievals" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "mode": "semantic",
    "top_k": 5
  }'
```

3. **Hybrid search**:
```bash
curl -X POST "http://localhost:8000/api/v1/retrievals" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "neural networks",
    "mode": "hybrid",
    "top_k": 10,
    "collection_id": "$COLLECTION_ID"
  }'
```

4. **Verify results**:
- Check scores are between 0 and 1
- Verify results are relevant to query
- Confirm document metadata is included
- Test collection filtering

---

## What's NOT in Week 3

- Chat API (/chat endpoint) - Week 4
- LightRAG integration - Week 4
- Reranking with cross-encoder models - Week 4
- Query expansion - Week 4
- Caching layer - Week 4+
- External connectors - Week 4+

---

## Estimated Timeline

| Day | Tasks | Hours |
|-----|-------|-------|
| Day 1 | Vector search service + Query embedding | 4-6 |
| Day 2 | Retrieval API endpoint + Pydantic schemas | 4-5 |
| Day 3 | Hybrid search + RRF | 4-5 |
| Day 4 | Testing + Polish + Documentation | 3-4 |

**Total:** ~20-25 hours over 4 days

---

## Next Week Preview

**Week 4: Chat API + LightRAG**
- Conversational retrieval with context
- LightRAG graph-based retrieval
- Query expansion and reformulation
- Streaming responses (SSE)
- Session management
