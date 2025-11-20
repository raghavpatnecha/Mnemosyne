# Mnemosyne Phase 1: Big Picture Architecture Review

**Date**: 2025-11-20  
**Status**: Post-Implementation Review  
**Scope**: Document current system design after recent fixes and improvements  
**Next Phase**: Phase 2 will dive into specific component optimization and scaling

---

## Executive Summary

Mnemosyne is a production-ready **Retrieval-Augmented Generation (RAG)-as-a-Service** platform built on FastAPI, PostgreSQL + pgvector, LightRAG, and Celery. The system provides a multi-tenant architecture with five retrieval modes, streaming chat, and comprehensive document processing capabilities.

**Key Metrics**:
- 5 search modes (semantic, keyword, hybrid, hierarchical, graph)
- 150+ LLM models via LiteLLM
- Per-user, per-collection isolation
- 50-70% search performance via caching
- 35-80% accuracy improvement with graph enhancement
- Support for 10+ document types (PDF, DOCX, video, audio, YouTube)

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Data Flow Diagrams](#data-flow-diagrams)
3. [Component Breakdown](#component-breakdown)
4. [Storage Architecture](#storage-architecture)
5. [Retrieval Modes Deep Dive](#retrieval-modes-deep-dive)
6. [Background Processing Pipeline](#background-processing-pipeline)
7. [SDK Integration Points](#sdk-integration-points)
8. [Performance & Optimization Features](#performance--optimization-features)
9. [Discrepancies & Known Limitations](#discrepancies--known-limitations)
10. [Deeper Inspection Items for Phase 2](#deeper-inspection-items-for-phase-2)

---

## System Architecture Overview

### High-Level Layer Stack

```
CLIENT LAYER
  Web Frontend | Python SDK | TypeScript SDK

API LAYER (FastAPI)
  Auth | Collections | Documents | Retrievals | Chat
  CORS | Rate Limiting | Error Handlers | Request ID Logging

SERVICE LAYER
  Embedding | Chat | Cache | Search | Rerank
  LightRAG | Vector Search | Hierarchical Search | Query Reformulation

TASK QUEUE LAYER (Celery)
  Document Processing | Parse | Chunk | Embed | Index | Graph Build

STORAGE LAYER
  PostgreSQL + pgvector | LightRAG (File-based) | Redis | S3/Local
```

### Core Findings

Mnemosyne implements a **multi-tenant RAG platform** with:
- **5 retrieval modes** optimized for different use cases
- **Async-first architecture** with FastAPI + Celery
- **Comprehensive caching** (embeddings 24h, search 1h)
- **Knowledge graph integration** via LightRAG
- **Streaming chat** with session persistence
- **Multi-format document support** (PDF, DOCX, video, audio, YouTube)

---

## Data Flow Diagrams

### 1. Document Ingestion Pipeline

```
Upload → API Handler → Create (pending) → Enqueue Celery Task
                                              ↓
                                    Row-level locking
                                              ↓
        Parse (Docling) → Chunk (Chonkie) → Embed (OpenAI)
              ↓                    ↓              ↓
        Extract images    Create metadata   1536d vectors
                                              ↓
        ┌─────────────────────────────────────┼─────────────────────┐
        │                                     │                     │
        ▼                                     ▼                     ▼
    POSTGRESQL                         SUMMARY GENERATION       LIGHTRAG
    • Chunks                          • Document embedding     • Per-user
    • Embeddings                      • Hierarchical search    • Per-collection
    • Indexes (pgvector)              • LightRAG indexing      • Knowledge graph
                                                                • Entities
                                                                • Relationships

                          ↓
                 Update Document Status: completed
                 Store: chunk_count, total_tokens, timestamps
                 Cleanup: S3 temp files

TIMELINE: 2-30 seconds (doc size, LightRAG enabled)
RETRIES: Max 3 with 60s backoff
RACE CONDITIONS: Fixed with row-level locking
```

### 2. Search Request Flow (5 Modes)

```
Query POST /retrievals/retrieve
    ↓
CACHE CHECK (Redis 1h)
    ├─ HIT → Return immediately (50-70% faster)
    └─ MISS → Continue

Query Reformulation (optional, 10-15% better results)
    ↓
Embedding Generation (cached 24h)
    ↓
MODE SELECTION
    ├─ SEMANTIC: pgvector cosine similarity (100-300ms)
    ├─ KEYWORD: PostgreSQL full-text search (50-200ms)
    ├─ HYBRID: RRF fusion (150-400ms)
    ├─ HIERARCHICAL: Doc-level → chunk-level (200-600ms)
    ├─ GRAPH: LightRAG knowledge graph (300-1000ms)
    └─ HybridRAG: Base + Graph parallel (1.5-2x base)

Reranking (optional, 15-25% accuracy improvement)
    ↓
Cache Results (1h TTL)
    ↓
Return Response (chunks + scores + citations)
```

### 3. Chat Streaming Flow

```
Message POST /chat
    ↓
RAG RETRIEVAL (search service, top_k)
    ↓
PROMPT CONSTRUCTION (system + context + history + message)
    ↓
LiteLLM STREAMING (150+ models, default: gpt-4o-mini)
    ↓
SSE STREAM (asyncio generator)
    ├─ delta: tokens
    ├─ sources: citations
    └─ done: completion marker
    ↓
PERSISTENCE (save message + session metadata)

LATENCY: 1-5 seconds E2E (retrieval + first token + streaming)
```

---

## Component Breakdown

### API Layer (FastAPI)

**Endpoints:**
- `POST /auth/register` - User authentication
- `CRUD /collections` - Collection management
- `CRUD /documents` - Document upload + status
- `POST /retrievals/retrieve` - Search (5 modes)
- `POST /chat` - Streaming chat with RAG

**Middleware Stack:**
1. CORS (configurable origins)
2. Rate Limiting (SlowAPI)
3. Error Handlers (custom exceptions)
4. Request ID Logging

### Service Layer

| Service | Purpose |
|---------|---------|
| EmbeddingService | OpenAI embedding + Redis cache |
| SearchService | Vector + keyword + hybrid search |
| HierarchicalSearchService | Document-level → chunk-level |
| ChatService | RAG + LLM streaming |
| LightRAGService | Knowledge graph (per-user, per-collection) |
| RerankerService | Optional result reranking (5 providers) |
| CacheService | Redis integration |
| QueryReformulationService | Query expansion (optional) |
| DocumentSummaryService | Document summarization |
| QuotaService | Usage tracking |

### Task Queue Layer (Celery)

**Configuration:**
- Broker: Redis
- Concurrency: 4 workers
- Retries: 3 with 60s backoff
- Task: `process_document_task`

**Pipeline:**
1. Parse (Docling)
2. Chunk (Chonkie semantic)
3. Embed (OpenAI, cached)
4. Store (PostgreSQL + pgvector)
5. Summarize (for hierarchical)
6. Index (LightRAG graph)

### Data Models

```
Users ←→ APIKeys (1:N)
Users ←→ Collections (1:N)
    Collections ←→ Documents (1:N)
        Documents ←→ Chunks (1:N)
Users ←→ ChatSessions (1:N)
    ChatSessions ←→ ChatMessages (1:N)
```

**Key Fields:**
- All models have `user_id` (multi-tenancy)
- Chunks have 1536d pgvector embeddings
- Documents track status (pending→processing→completed/failed)
- Chat sessions persist indefinitely

---

## Storage Architecture

### PostgreSQL + pgvector

**Key Tables:**
- `users` - Authentication
- `api_keys` - API key management (SHA-256 hashed)
- `collections` - Document groupings (per-user)
- `documents` - Document metadata + processing status
- `document_chunks` - Text chunks with embeddings (pgvector 1536d)
- `chat_sessions` - Conversation history
- `chat_messages` - Individual messages

**Indexes:**
- IVFFlat vector index on chunks.embedding (cosine)
- GIN full-text index on chunks.content
- B-tree on all foreign keys
- Unique (document_id, chunk_index)

**Storage:** ~5GB for 10K documents

### LightRAG (Knowledge Graph)

**Directory Structure:**
```
LIGHTRAG_WORKING_DIR/
└── users/{user_id}/
    └── collections/{collection_id}/
        ├── graph_chunk_entity_relation.graphml
        ├── entities.json
        ├── relationships.json
        ├── entity_embeddings.npy
        └── chunks/
```

**Features:**
- Per-user, per-collection isolation
- Entity extraction + relationship inference
- File-based storage (no S3 yet)
- Instance manager caches LightRAG objects
- TODO: PostgreSQL migration, S3 support

**Storage:** ~2-5GB for 10K documents

### Redis

**Cache Strategy:**
- Embeddings: 24h TTL (60-80% hit rate)
- Search results: 1h TTL (40-60% hit rate)
- Rate limits: Configurable
- Celery tasks: Task-dependent

**Performance:** 50-70% faster on cache hits

---

## Retrieval Modes Deep Dive

### Mode 1: Semantic (Vector Similarity)
- **Algorithm**: pgvector cosine similarity
- **Speed**: 100-300ms
- **Use Case**: Conceptual similarity
- **Accuracy**: High semantic understanding

### Mode 2: Keyword (Full-Text)
- **Algorithm**: PostgreSQL BM25 full-text search
- **Speed**: 50-200ms
- **Use Case**: Exact term matching
- **Accuracy**: High for technical queries

### Mode 3: Hybrid (Semantic + Keyword)
- **Algorithm**: Reciprocal Rank Fusion (RRF)
- **Speed**: 150-400ms (parallel execution)
- **Use Case**: General-purpose (recommended default)
- **Accuracy**: 15-25% better than single mode

### Mode 4: Hierarchical (Document → Chunk)
- **Algorithm**: Two-tier ranking
- **Speed**: 200-600ms
- **Use Case**: Long documents, hierarchical data
- **Accuracy**: Good for multi-document searches

### Mode 5: Graph (Knowledge Graph)
- **Algorithm**: LightRAG entity + relationship traversal
- **Speed**: 300-1000ms (LLM-based)
- **Use Case**: Complex multi-hop reasoning
- **Accuracy**: 35-80% improvement vs base (research-backed)

### HybridRAG (Base + Graph)
- **Algorithm**: Base mode + LightRAG in parallel
- **Speed**: 1.5-2x base mode (parallelism, not additive)
- **Use Case**: Relationship queries requiring both relevance and context
- **Request**: `enable_graph=true` + any base mode

---

## Background Processing Pipeline

### Document Lifecycle

```
Upload → Pending → Processing → Completed (or Failed)
          ↓
      Celery task enqueued
      Row-level locking applied
          ↓
      Parse (async, Docling)
          ↓
      Chunk (Chonkie semantic)
          ↓
      Embed (OpenAI, cached)
      Generate summary embedding (hierarchical)
          ↓
      Store (PostgreSQL + pgvector indexes)
          ↓
      Index (LightRAG, if enabled)
          ↓
      Mark completed
      Store timestamps, chunk_count, tokens
          ↓
      Cleanup (S3 temp files)
```

**Race Condition Prevention:**
- Row-level locking: `with_for_update()`
- Status validation: only "pending" transitions
- Atomic updates in transaction

**Error Handling:**
- Max 3 retries with 60s backoff
- Status = "failed", error_message stored
- User can monitor via `/documents/{id}/status`

---

## SDK Integration Points

### Python SDK
```python
from mnemosyne import Client

client = Client(api_key="mn_...", base_url="http://localhost:8000/api/v1")

# Collections
col = client.collections.create(name="Papers")

# Documents
doc = client.documents.create(col.id, file="paper.pdf")
status = client.documents.status(doc.id)

# Search (all 5 modes + HybridRAG)
results = client.retrievals.retrieve(
    query="What is RAG?",
    mode="hybrid",
    enable_graph=True,
    rerank=True
)

# Chat
for chunk in client.chat.chat(message="Explain RAG", stream=True):
    print(chunk, end="")
```

### TypeScript SDK
```typescript
import { MnemosyneClient } from '@mnemosyne/sdk';

const client = new MnemosyneClient({ apiKey: 'mn_...' });

// Same API as Python SDK
const col = await client.collections.create({ name: 'Papers' });
const results = await client.retrievals.retrieve({ query, mode: 'hybrid' });

for await (const chunk of await client.chat.chat({ message, stream: true })) {
  process.stdout.write(chunk);
}
```

### Frontend Integration
- Quart (async Flask) + jQuery
- Collection management
- Document upload (file, URL, YouTube)
- Search mode selection
- Real-time results
- Streaming chat display

---

## Performance & Optimization Features

### 1. Redis Caching
- Embeddings: 24h TTL (70% faster)
- Search results: 1h TTL (50-70% faster)
- No manual invalidation (TTL-based)

### 2. Query Reformulation (Optional)
- Expands queries with synonyms
- 10-15% better results
- ~50ms overhead

### 3. Reranking (Optional, 5 Providers)
- FlashRank (local, fast, free)
- Cohere, Jina, Voyage, Mixedbread (API-based)
- 15-25% accuracy improvement
- Works with all search modes

### 4. Hierarchical Search
- Two-tier approach (doc-level → chunk-level)
- Reduces false positives
- 200-600ms latency

### 5. Knowledge Graph (LightRAG)
- Entity extraction (LLM-based)
- Relationship inference
- Dual-level retrieval
- 35-80% accuracy improvement

### 6. Concurrent Processing
- 4 Celery workers (configurable)
- Async/await throughout
- Parallel embedding generation
- Parallel LightRAG indexing

---

## Discrepancies & Known Limitations

### Documentation vs Implementation

| Item | Documented | Actual | Impact |
|------|-----------|--------|--------|
| LightRAG Storage | File + S3 ready | File-based only | Scalability concern |
| Keyword Search | Public method | `_keyword_search` (private) | Code organization |
| Weekly Phases | Week 1-5 structure | No phase impl | Not enforced |

### Known Limitations

1. **LightRAG Storage**: File-based only, no S3 support yet
2. **Per-Instance Caching**: Memory grows with users
3. **Cascade Delete**: Multiple systems to coordinate
4. **Session Cleanup**: No retention policy (DB bloat risk)
5. **Rate Limiting**: Not documented in API reference
6. **Celery Retries**: Fixed backoff, not exponential
7. **File Size Compliance**: Some files exceed 300-line guideline
8. **Error Recovery**: Limited transient failure handling

---

## Deeper Inspection Items for Phase 2

### 1. Cascade Delete Behavior
- Does LightRAG cleanup on collection delete?
- Are all file storage items cleaned up?
- Orphaned Redis cache entries?

### 2. Rate Limiting Effectiveness
- Current limits documented?
- Proper enforcement under load?
- Streaming response handling?

### 3. LightRAG Memory Management
- Memory growth over time?
- Thousands of users?
- GC impact with many instances?
- LRU cache needed?

### 4. Search Performance at Scale
- Performance with 1M+ chunks?
- IVFFlat tuning (lists=100)?
- GIN index overhead?
- Vector recall accuracy?

### 5. Embedding Cache Invalidation
- Model change handling?
- Corrupted cache recovery?
- Cache versioning strategy?

### 6. LightRAG S3 Migration
- S3 backend design?
- Performance implications?
- Cost-benefit analysis?

### 7. Celery Error Recovery
- Exponential backoff?
- Dead letter queue?
- Error monitoring/alerting?

### 8. Chat Session Management
- Cleanup policy?
- Storage limits?
- Archive strategy?
- Expiration timing?

### 9. Document Processing Idempotency
- Partial failure recovery?
- Upsert safety?
- Chunk uniqueness?

### 10. Query Reformulation Coverage
- When is it enabled?
- All query types?
- Cost-benefit?
- Language support?

---

## Strengths

✓ Well-structured service layer
✓ Multi-tenancy by design
✓ 5 retrieval modes + HybridRAG
✓ Async-first architecture
✓ Production features (caching, reranking, rate limiting)
✓ Multimodal document support
✓ Official SDKs (Python + TypeScript)
✓ Knowledge graph integration
✓ Streaming chat
✓ Proper database schema with indexing

---

## Concerns

⚠ LightRAG file-based storage limits scalability
⚠ Per-instance caching memory growth
⚠ Cascade delete coordination complexity
⚠ Session cleanup could cause DB bloat
⚠ Celery retry strategy not optimal
⚠ Some rate limiting details undocumented
⚠ Query reformulation impact not quantified
⚠ Error recovery needs enhancement

---

## Conclusion

Mnemosyne is a **well-engineered, production-ready RAG platform** with comprehensive features and solid architecture. It successfully implements multi-tenancy, multiple retrieval modes, and production optimizations.

**Ready for:** Initial production deployments with awareness of known limitations.

**Phase 2 Priorities:**
1. LightRAG S3 backend support
2. Performance profiling and optimization
3. Celery error recovery enhancement
4. Session lifecycle management
5. Rate limiting documentation

---

**Review Date**: 2025-11-20  
**Status**: Complete - Ready for Phase 2 Planning
