# Mnemosyne End-to-End Architecture

**Complete technical architecture from SDK → API → Backend → Storage**

This document provides a comprehensive view of the entire Mnemosyne stack, designed for developers who want to:
- Understand the complete data flow
- Build custom frontends
- Extend or modify the system
- Deploy and scale Mnemosyne

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Layer Breakdown](#layer-breakdown)
3. [End-to-End Data Flows](#end-to-end-data-flows)
4. [API Contract](#api-contract)
5. [Frontend Integration Guide](#frontend-integration-guide)
6. [Deployment Architecture](#deployment-architecture)
7. [Performance & Scaling](#performance--scaling)

**Related Documentation:**
- [Multi-Tenancy & User Separation](multi-tenancy.md) - How user data isolation works across all layers

---

## Architecture Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │   Web Frontend │  │  Python SDK    │  │  TypeScript SDK  │   │
│  │  (React/Vue)   │  │  (Official)    │  │   (Official)     │   │
│  └────────┬───────┘  └────────┬───────┘  └────────┬─────────┘   │
└───────────┼──────────────────┼────────────────────┼──────────────┘
            │                  │                    │
            └──────────────────┴────────────────────┘
                               │
                         HTTP/REST API
                               │
┌──────────────────────────────┼────────────────────────────────────┐
│                         API LAYER                                 │
│                    ┌─────────▼──────────┐                         │
│                    │  FastAPI Backend   │                         │
│                    │  (Port 8000)       │                         │
│                    └────────┬───────────┘                         │
│                             │                                     │
│         ┌───────────────────┼───────────────────┐                │
│         │                   │                   │                │
│    ┌────▼────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│    │  Auth   │      │ Collections │     │  Documents  │        │
│    │ Routes  │      │   Routes    │     │   Routes    │        │
│    └─────────┘      └─────────────┘     └─────────────┘        │
│    ┌─────────┐      ┌─────────────┐     ┌─────────────┐        │
│    │Retrieval│      │    Chat     │     │  Middleware │        │
│    │ Routes  │      │   Routes    │     │(Rate Limit) │        │
│    └─────────┘      └─────────────┘     └─────────────┘        │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────┼────────────────────────────────────┐
│                    SERVICE LAYER                                │
│                            │                                    │
│    ┌──────────────────────┼──────────────────────┐            │
│    │                      │                      │            │
│ ┌──▼─────────┐   ┌───────▼────────┐   ┌────────▼────────┐   │
│ │ Embedding  │   │   LightRAG     │   │  Document       │   │
│ │  Service   │   │   Service      │   │  Processing     │   │
│ └────┬───────┘   └────────┬───────┘   └────────┬────────┘   │
│      │                    │                     │            │
│ ┌────▼────────┐  ┌───────▼────────┐   ┌────────▼────────┐   │
│ │   Search    │  │   Reranking    │   │    Chunking     │   │
│ │  Service    │  │   Service      │   │    Service      │   │
│ └─────────────┘  └────────────────┘   └─────────────────┘   │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────┼────────────────────────────────────┐
│                     TASK QUEUE LAYER                            │
│                    ┌───────▼────────┐                           │
│                    │  Celery Worker │                           │
│                    │  (Background)  │                           │
│                    └───────┬────────┘                           │
│                            │                                    │
│    ┌────────────┬──────────┼──────────┬──────────────┐        │
│    │            │          │          │              │        │
│ ┌──▼────┐  ┌───▼───┐  ┌───▼───┐  ┌──▼─────┐  ┌────▼─────┐  │
│ │ Parse │  │ Chunk │  │ Embed │  │ Index  │  │  Graph   │  │
│ │  Task │  │ Task  │  │ Task  │  │  Task  │  │   Build  │  │
│ └───────┘  └───────┘  └───────┘  └────────┘  └──────────┘  │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────┼────────────────────────────────────┐
│                     STORAGE LAYER                               │
│                            │                                    │
│    ┌───────────────────────┼───────────────────────┐           │
│    │                       │                       │           │
│ ┌──▼──────────┐   ┌───────▼────────┐   ┌─────────▼────────┐  │
│ │ PostgreSQL  │   │    LightRAG    │   │      Redis       │  │
│ │ + pgvector  │   │  (File-based)  │   │   (Cache+Queue)  │  │
│ └─────────────┘   └────────────────┘   └──────────────────┘  │
│                                                                │
│  Stores:            Stores:              Stores:              │
│  • Users            • Knowledge Graph    • Celery Tasks       │
│  • Collections      • Entities           • Embedding Cache    │
│  • Documents        • Relationships      • Search Cache       │
│  • Chunks           • Graph Embeddings   • Rate Limits        │
│  • Embeddings                                                 │
│  • Chat History                                               │
└────────────────────────────────────────────────────────────────┘
```

---

## Layer Breakdown

### 1. Client Layer (SDK / Frontend)

#### Python SDK (`sdk/mnemosyne/`)
```python
from mnemosyne import Client

client = Client(
    api_key="mn_...",
    base_url="http://localhost:8000/api/v1"
)

# High-level abstractions
client.collections.create(name="Papers")
client.documents.create(collection_id, file="paper.pdf")
client.retrievals.retrieve(query="...", mode="hybrid")
client.chat.chat(message="...", stream=True)
```

**Responsibilities:**
- HTTP client wrapper (httpx)
- Request/response serialization (Pydantic)
- Error handling and retries
- Streaming support (SSE)
- Type safety

**Files:**
- `sdk/mnemosyne/client.py` - Sync client
- `sdk/mnemosyne/async_client.py` - Async client
- `sdk/mnemosyne/resources/*.py` - Resource clients
- `sdk/mnemosyne/types/*.py` - Pydantic models

#### TypeScript SDK (`sdk-ts/src/`)
```typescript
import { MnemosyneClient } from '@mnemosyne/sdk';

const client = new MnemosyneClient({ apiKey: 'mn_...' });

await client.collections.create({ name: 'Papers' });
await client.documents.create(collectionId, 'paper.pdf');
const results = await client.retrievals.retrieve({
  query: '...',
  mode: 'hybrid'
});
```

**Responsibilities:**
- Same as Python SDK
- Browser and Node.js support
- TypeScript type definitions

#### Custom Frontend Integration
Any frontend can integrate by:
1. Using SDK (recommended)
2. Calling REST API directly
3. Implementing custom client

**See:** [Frontend Integration Guide](#frontend-integration-guide)

---

### 2. API Layer (FastAPI)

**Location:** `backend/api/`

#### API Structure
```
backend/api/
├── auth.py           # POST /auth/register
├── collections.py    # CRUD /collections
├── documents.py      # CRUD /documents + upload
├── retrievals.py     # POST /retrievals/retrieve
└── chat.py          # POST /chat + SSE streaming
```

#### Key Endpoints

**Authentication:**
```
POST /api/v1/auth/register
→ Creates user, returns API key (one-time)
```

**Collections:**
```
GET    /api/v1/collections
POST   /api/v1/collections
GET    /api/v1/collections/{id}
PATCH  /api/v1/collections/{id}
DELETE /api/v1/collections/{id}
```

**Documents:**
```
GET    /api/v1/documents?collection_id={id}
POST   /api/v1/documents (multipart/form-data or JSON)
GET    /api/v1/documents/{id}
GET    /api/v1/documents/{id}/status
DELETE /api/v1/documents/{id}
```

**Retrievals (Search):**
```
POST /api/v1/retrievals/retrieve
{
  "query": "What is RAG?",
  "mode": "hybrid",
  "collection_id": "uuid",
  "top_k": 10,
  "enable_graph": true,
  "rerank": true
}
→ Returns: chunks with metadata, scores, sources
```

**Chat (Streaming):**
```
POST /api/v1/chat
{
  "message": "Explain RAG",
  "collection_id": "uuid",
  "session_id": "uuid",
  "stream": true
}
→ Returns: SSE stream with tokens + metadata
```

#### Middleware Stack
```python
FastAPI App
  └─ CORS Middleware (allow origins)
  └─ Rate Limiting (SlowAPI)
  └─ Error Handlers (custom exceptions)
  └─ Request ID (logging)
  └─ Routes
      └─ Dependency Injection (auth)
      └─ Pydantic Validation
      └─ Business Logic
```

---

### 3. Service Layer

**Location:** `backend/services/`

#### Core Services

**1. Embedding Service** (`embedding_service.py`)
```python
class EmbeddingService:
    def generate_embedding(text: str) -> List[float]:
        # OpenAI text-embedding-3-large (1536 dims)
        # Cached in Redis (24h TTL)
        # Returns: embedding vector
```

**2. LightRAG Service** (`lightrag_service.py`)
```python
class LightRAGService:
    def insert(text: str, metadata: dict):
        # Build knowledge graph
        # Extract entities and relationships
        # Store in working directory

    def query(query: str, mode: str) -> str:
        # Query knowledge graph
        # Return: synthesized context
```

**3. Search Service** (`search_service.py`)
```python
class SearchService:
    def semantic_search(query_embedding, top_k):
        # PostgreSQL + pgvector
        # Cosine similarity

    def keyword_search(query, top_k):
        # PostgreSQL full-text search
        # BM25 ranking

    def hybrid_search(query, top_k):
        # RRF fusion of semantic + keyword

    def graph_search(query, top_k, enable_graph):
        # LightRAG + semantic fallback
```

**4. Document Processing Service** (`document_processing.py`)
```python
class DocumentProcessor:
    def process_document(file_path, collection_id):
        # Parse (Docling)
        # Chunk (Chonkie)
        # Embed (OpenAI)
        # Index (PostgreSQL + LightRAG)
```

**5. Chat Service** (`chat_service.py`)
```python
class ChatService:
    async def stream_chat(message, context):
        # LiteLLM for LLM calls
        # SSE streaming
        # Maintains session history
```

**6. Reranking Service** (`reranking_service.py`)
```python
class RerankingService:
    def rerank(query, chunks, top_k):
        # FlashRank (local)
        # Or API rerankers (Cohere, Jina, etc.)
```

---

### 4. Task Queue Layer (Celery)

**Location:** `backend/tasks/`

**Why Celery?**
- Async document processing (long-running)
- Background indexing
- Decoupled from API requests

**Task Flow:**
```
User uploads document
  ↓
API creates Document record (status: pending)
  ↓
API enqueues Celery task
  ↓
Celery worker picks up task
  ↓
Worker processes:
  1. Parse document (Docling)
  2. Extract images/tables
  3. Chunk text (Chonkie)
  4. Generate embeddings
  5. Store in PostgreSQL
  6. Build LightRAG graph
  ↓
Update Document status (completed/failed)
  ↓
User polls /documents/{id}/status
```

**Key Tasks:**

```python
# backend/tasks/document_tasks.py

@celery_app.task
def process_document_task(document_id: str):
    # Parse → Chunk → Embed → Index

@celery_app.task
def build_graph_task(document_id: str):
    # LightRAG knowledge graph construction
```

**Queue Configuration:**
```python
# Redis as broker and result backend
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"

# Concurrency
CELERY_WORKER_CONCURRENCY = 4  # CPU-bound tasks
```

---

### 5. Storage Layer

#### PostgreSQL + pgvector

**Schema:**
```sql
-- Users and API Keys
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR,
    created_at TIMESTAMP
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    key_hash VARCHAR,  -- SHA-256 hash
    prefix VARCHAR,    -- "mn_" for display
    created_at TIMESTAMP
);

-- Collections (namespaces)
CREATE TABLE collections (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP
);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    collection_id UUID REFERENCES collections(id),
    user_id UUID REFERENCES users(id),
    title VARCHAR,
    filename VARCHAR,
    content_hash VARCHAR,
    status VARCHAR,  -- pending, processing, completed, failed
    metadata JSONB,
    created_at TIMESTAMP
);

-- Document Chunks (with embeddings)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    collection_id UUID REFERENCES collections(id),
    chunk_index INTEGER,
    content TEXT,
    embedding VECTOR(1536),  -- pgvector extension
    metadata JSONB,
    created_at TIMESTAMP
);

-- Vector index for fast similarity search
CREATE INDEX ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Full-text search index
CREATE INDEX ON document_chunks
USING GIN (to_tsvector('english', content));

-- Chat Sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    collection_id UUID,
    created_at TIMESTAMP,
    last_message_at TIMESTAMP
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id),
    role VARCHAR,  -- user, assistant
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP
);
```

**Indexes:**
- Vector index (IVFFlat) for similarity search
- Full-text index (GIN) for keyword search
- B-tree on foreign keys and timestamps

**Storage Estimates:**
- 1k documents: ~500 MB
- 10k documents: ~5 GB
- 100k documents: ~50 GB

#### LightRAG (File-based)

**Directory Structure:**
```
/app/data/lightrag/
├── {collection_id}/
│   ├── graph_chunk_entity_relation.graphml  # Knowledge graph
│   ├── entities.json                        # Entity metadata
│   ├── relationships.json                   # Relationship metadata
│   ├── entity_embeddings.npy               # Entity vectors
│   └── chunks/
│       ├── chunk_1.json
│       ├── chunk_2.json
│       └── ...
```

**What it stores:**
- Extracted entities (people, places, concepts)
- Relationships between entities
- Graph embeddings for traversal
- Original chunk references

**Storage Estimates:**
- 1k documents: ~200 MB
- 10k documents: ~2 GB
- 100k documents: ~20 GB

**Persistence:**
- Mount as volume: `./data/lightrag:/app/data/lightrag`
- **CRITICAL:** Do not lose this data (rebuilding is expensive)

#### Redis

**Usage:**
```
# Embedding cache (24h TTL)
SET embed:hash:abc123 "[0.123, 0.456, ...]" EX 86400

# Search results cache (1h TTL)
SET search:hash:xyz789 "{...results...}" EX 3600

# Celery task queue
LPUSH celery "task_payload"

# Rate limiting
INCR ratelimit:user:{user_id}:{endpoint} EX 60
```

**Storage:** ~1 GB typical

---

## End-to-End Data Flows

### Flow 1: Document Upload & Processing

```
┌─────────────┐
│   Client    │
│ (SDK/Web)   │
└──────┬──────┘
       │ 1. Upload document
       │ POST /api/v1/documents
       │ (multipart/form-data)
       ▼
┌──────────────┐
│  FastAPI     │
│  Documents   │
│  Endpoint    │
└──────┬───────┘
       │ 2. Validate & save file
       │ 3. Create Document record (status: pending)
       │ 4. Enqueue Celery task
       ▼
┌──────────────┐
│  Celery      │
│  Worker      │
└──────┬───────┘
       │ 5. Process document:
       │
       ├─► Docling: Parse PDF/DOCX
       │   → Extract text, images, tables
       │
       ├─► Chonkie: Chunk text
       │   → 512 tokens per chunk
       │   → 128 token overlap
       │
       ├─► OpenAI: Generate embeddings
       │   → 1536-dim vectors
       │   → Cache in Redis
       │
       ├─► PostgreSQL: Store chunks
       │   → Insert into document_chunks
       │   → Store embeddings
       │
       └─► LightRAG: Build graph
           → Extract entities
           → Extract relationships
           → Store in working dir

       │ 6. Update Document (status: completed)
       ▼
┌──────────────┐
│  PostgreSQL  │  ┌────────────┐  ┌──────────┐
│  + pgvector  │  │  LightRAG  │  │  Redis   │
└──────────────┘  └────────────┘  └──────────┘
       ▲              ▲               ▲
       │              │               │
       └──────────────┴───────────────┘
                      │
       7. Client polls /documents/{id}/status
       ▼
    ┌──────────────┐
    │   Client     │
    │  (Receives)  │
    │  Completed!  │
    └──────────────┘
```

### Flow 2: Semantic/Hybrid Search

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Search query
       │ POST /api/v1/retrievals/retrieve
       │ {query: "...", mode: "hybrid"}
       ▼
┌──────────────┐
│  FastAPI     │
│  Retrievals  │
│  Endpoint    │
└──────┬───────┘
       │ 2. Extract query
       ▼
┌──────────────┐
│  Search      │
│  Service     │
└──────┬───────┘
       │ 3. Hybrid search:
       │
       ├─► Semantic Search:
       │   ├─ Generate query embedding (OpenAI)
       │   ├─ Check Redis cache
       │   └─ Query pgvector (cosine similarity)
       │
       ├─► Keyword Search:
       │   └─ PostgreSQL full-text search (BM25)
       │
       └─► RRF Fusion:
           └─ Combine results with Reciprocal Rank Fusion

       │ 4. Optional: Reranking
       │    └─ FlashRank reorder results
       ▼
┌──────────────┐
│  PostgreSQL  │
│  Returns:    │
│  • Chunks    │
│  • Scores    │
│  • Metadata  │
└──────┬───────┘
       │ 5. Format response
       ▼
┌──────────────┐
│   Client     │
│  (Receives)  │
│   Results    │
└──────────────┘
```

### Flow 3: Graph Search (LightRAG)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Search query
       │ POST /api/v1/retrievals/retrieve
       │ {query: "...", mode: "graph"}
       ▼
┌──────────────┐
│  FastAPI     │
└──────┬───────┘
       │ 2. Route to graph search
       ▼
┌──────────────┐
│  Search      │
│  Service     │
└──────┬───────┘
       │ 3. Query LightRAG:
       ▼
┌──────────────┐
│  LightRAG    │
│  Service     │
└──────┬───────┘
       │ 4. Graph traversal:
       │    ├─ Extract entities from query
       │    ├─ Find related entities in graph
       │    ├─ Traverse relationships
       │    └─ Synthesize context from graph
       │
       │ 5. Get actual source chunks:
       ▼
┌──────────────┐
│  PostgreSQL  │
│  (Semantic   │
│   Search)    │
└──────┬───────┘
       │ 6. Combine:
       │    • Graph context (from LightRAG)
       │    • Source chunks (from PostgreSQL)
       │    • Metadata + scores
       ▼
┌──────────────┐
│   Client     │
│  (Receives)  │
│   Graph      │
│   Results    │
└──────────────┘
```

### Flow 4: Streaming Chat

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Chat message
       │ POST /api/v1/chat
       │ {message: "...", stream: true}
       ▼
┌──────────────┐
│  FastAPI     │
│  Chat        │
│  Endpoint    │
└──────┬───────┘
       │ 2. Establish SSE connection
       ▼
┌──────────────┐
│  Chat        │
│  Service     │
└──────┬───────┘
       │ 3. Retrieve context:
       │    └─► Search Service
       │        └─► Get relevant chunks
       │
       │ 4. Build prompt:
       │    • System prompt
       │    • Retrieved context
       │    • User message
       │    • Chat history (if session_id)
       ▼
┌──────────────┐
│  LiteLLM     │
│  (OpenAI)    │
└──────┬───────┘
       │ 5. Stream tokens:
       ▼
   "Based on"
   " the"
   " documents,"
   " RAG"
   " stands"
   " for..."
       │
       │ 6. SSE format:
       │    data: Based on\n\n
       │    data: the\n\n
       │    data: documents,\n\n
       ▼
┌──────────────┐
│   Client     │
│  (Displays)  │
│   Streaming  │
│   Response   │
└──────────────┘
```

### Flow 5: HybridRAG (Graph Enhancement)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Search with graph enhancement
       │ POST /api/v1/retrievals/retrieve
       │ {query: "...", mode: "hybrid", enable_graph: true}
       ▼
┌──────────────┐
│  Search      │
│  Service     │
└──────┬───────┘
       │ 2. Parallel execution:
       │
       ├─────────────────┬──────────────────┐
       │                 │                  │
       ▼                 ▼                  ▼
   ┌─────────┐    ┌──────────┐      ┌──────────┐
   │ Hybrid  │    │  Graph   │      │  Both    │
   │ Search  │    │  Query   │      │  Execute │
   │(PG+FTS) │    │(LightRAG)│      │ Parallel │
   └────┬────┘    └────┬─────┘      └──────────┘
        │              │
        │              │ 3. Wait for both
        └──────┬───────┘
               │
               ▼
       ┌──────────────┐
       │  Merge &     │
       │  Dedupe      │
       └──────┬───────┘
              │ 4. Combined results:
              │    • Base chunks (hybrid)
              │    • Graph chunks (marked)
              │    • graph_context field
              ▼
       ┌──────────────┐
       │   Client     │
       │  (Receives)  │
       │   Enhanced   │
       │   Results    │
       └──────────────┘
```

---

## API Contract

### Request/Response Formats

#### Standard Response Envelope
```json
{
  "data": {...},
  "meta": {
    "timestamp": "2024-01-15T12:00:00Z",
    "request_id": "uuid"
  }
}
```

#### Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid query parameter",
    "details": {...}
  },
  "meta": {
    "timestamp": "2024-01-15T12:00:00Z",
    "request_id": "uuid"
  }
}
```

#### Retrieval Response
```json
{
  "query": "What is RAG?",
  "mode": "hybrid",
  "total_results": 10,
  "graph_enhanced": true,
  "results": [
    {
      "chunk_id": "uuid",
      "content": "RAG stands for...",
      "chunk_index": 0,
      "score": 0.92,
      "metadata": {
        "images": ["url1.png"],
        "graph_sourced": false
      },
      "document": {
        "id": "uuid",
        "title": "RAG Paper",
        "filename": "rag.pdf"
      },
      "collection_id": "uuid"
    }
  ],
  "graph_context": "RAG relates to LLMs through..."
}
```

#### Chat SSE Stream
```
event: message
data: Based on

event: message
data: the documents,

event: done
data: {"session_id": "uuid", "sources": [...]}
```

---

## Frontend Integration Guide

### Option 1: Use Official SDKs (Recommended)

#### Python
```python
from mnemosyne import Client

client = Client(api_key="mn_...")

# Collections
collection = client.collections.create(name="Papers")

# Documents
doc = client.documents.create(
    collection_id=collection.id,
    file="paper.pdf"
)

# Search
results = client.retrievals.retrieve(
    query="What is RAG?",
    mode="hybrid",
    enable_graph=True
)

# Chat
for chunk in client.chat.chat(message="Explain RAG", stream=True):
    print(chunk, end="")
```

#### TypeScript
```typescript
import { MnemosyneClient } from '@mnemosyne/sdk';

const client = new MnemosyneClient({ apiKey: 'mn_...' });

const collection = await client.collections.create({ name: 'Papers' });
const doc = await client.documents.create(collection.id, 'paper.pdf');
const results = await client.retrievals.retrieve({
  query: 'What is RAG?',
  mode: 'hybrid',
  enableGraph: true
});

for await (const chunk of client.chat.chat({ message: 'Explain RAG' })) {
  process.stdout.write(chunk);
}
```

### Option 2: Direct REST API Integration

#### Authentication
```javascript
// 1. Register user
const response = await fetch('http://localhost:8000/api/v1/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password'
  })
});
const { api_key } = await response.json();

// 2. Use API key in all requests
const headers = {
  'Authorization': `Bearer ${api_key}`,
  'Content-Type': 'application/json'
};
```

#### Create Collection
```javascript
const collection = await fetch('http://localhost:8000/api/v1/collections', {
  method: 'POST',
  headers,
  body: JSON.stringify({ name: 'Papers' })
}).then(r => r.json());
```

#### Upload Document
```javascript
const formData = new FormData();
formData.append('collection_id', collection.id);
formData.append('file', fileInput.files[0]);

const doc = await fetch('http://localhost:8000/api/v1/documents', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${api_key}` },
  body: formData
}).then(r => r.json());
```

#### Search
```javascript
const results = await fetch('http://localhost:8000/api/v1/retrievals/retrieve', {
  method: 'POST',
  headers,
  body: JSON.stringify({
    query: 'What is RAG?',
    mode: 'hybrid',
    enable_graph: true,
    top_k: 10
  })
}).then(r => r.json());
```

#### Streaming Chat (SSE)
```javascript
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/chat?` +
  `message=${encodeURIComponent('Explain RAG')}&stream=true`,
  {
    headers: { 'Authorization': `Bearer ${api_key}` }
  }
);

eventSource.onmessage = (event) => {
  if (event.data === '[DONE]') {
    eventSource.close();
  } else {
    console.log(event.data); // Token by token
  }
};
```

### Option 3: Custom Client Implementation

**Required Features:**
1. HTTP client (fetch, axios, httpx)
2. Authentication header injection
3. SSE parsing for streaming
4. Retry logic with exponential backoff
5. Error handling

**Example Structure:**
```typescript
class CustomMnemosyneClient {
  constructor(apiKey: string, baseUrl: string) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  private async request(endpoint, options) {
    return fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        ...options.headers
      }
    });
  }

  async createCollection(name: string) {
    return this.request('/collections', {
      method: 'POST',
      body: JSON.stringify({ name })
    });
  }

  async *streamChat(message: string) {
    const response = await this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, stream: true })
    });

    const reader = response.body.getReader();
    // Parse SSE stream...
  }
}
```

---

## Deployment Architecture

### Development (Local)
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: mnemosyne
      POSTGRES_USER: mnemosyne
      POSTGRES_PASSWORD: dev

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./data/lightrag:/app/data/lightrag
    environment:
      DATABASE_URL: postgresql://mnemosyne:dev@postgres/mnemosyne
      REDIS_URL: redis://redis:6379/0
      OPENAI_API_KEY: ${OPENAI_API_KEY}

  celery:
    build: ./backend
    command: celery -A backend.celery_app worker
    depends_on:
      - postgres
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./data/lightrag:/app/data/lightrag
```

### Production (Kubernetes)

**Components:**
- **API Deployment**: 3+ replicas (horizontal scaling)
- **Celery Workers**: Auto-scaling based on queue depth
- **PostgreSQL**: Managed service (RDS, Cloud SQL)
- **Redis**: Managed service (ElastiCache, MemoryStore)
- **LightRAG**: Persistent volume (shared across pods)
- **Load Balancer**: Nginx/Envoy

**Scaling Considerations:**
- API pods: Scale based on CPU/request count
- Celery workers: Scale based on queue length
- PostgreSQL: Read replicas for search queries
- Redis: Cluster mode for high availability

---

## Performance & Scaling

### Latency Benchmarks

| Operation | Latency | Notes |
|-----------|---------|-------|
| Semantic search | 100-300ms | Depends on top_k |
| Keyword search | 50-150ms | PostgreSQL FTS |
| Hybrid search | 150-400ms | Combined overhead |
| Graph search | 300-800ms | LightRAG traversal |
| HybridRAG | 200-500ms | Parallel execution |
| Chat (first token) | 500-1500ms | Includes retrieval |
| Document processing | 10-60s | Async via Celery |

### Optimization Strategies

**1. Caching**
- Embeddings (24h TTL in Redis)
- Search results (1h TTL)
- Collection metadata (indefinite)

**2. Indexing**
- IVFFlat index for vectors (tune `lists` parameter)
- GIN index for full-text search
- B-tree on foreign keys

**3. Connection Pooling**
- PostgreSQL: 20 connections per pod
- Redis: 10 connections per pod
- Async I/O throughout

**4. Batch Processing**
- Batch embeddings (up to 100 chunks)
- Bulk inserts to PostgreSQL
- Parallel Celery tasks

**5. Read Replicas**
- Route search queries to replicas
- Write to primary only
- Eventual consistency acceptable

### Scaling Limits

| Component | Limit | Bottleneck |
|-----------|-------|------------|
| Collections | Unlimited | PostgreSQL storage |
| Documents | Millions | PostgreSQL + LightRAG storage |
| Chunks | 100M+ | Vector index performance |
| Concurrent requests | 1000+ | API pods + PostgreSQL connections |
| Embedding throughput | 10k/min | OpenAI rate limits |
| Search QPS | 500+ | PostgreSQL + caching |

---

## Summary

Mnemosyne's architecture is:
- **Layered**: Clear separation of concerns (SDK → API → Services → Storage)
- **Scalable**: Horizontal scaling at API and worker layers
- **Multi-modal**: Supports text, images, videos via metadata
- **Flexible**: 5 search modes + graph enhancement
- **Production-ready**: Caching, queueing, error handling built-in
- **Frontend-agnostic**: Any client can integrate via REST API or SDKs

**Key Takeaways for Integration:**
1. Use official SDKs for fastest development
2. All data flows through REST API (OpenAPI spec available)
3. Streaming is SSE-based (Server-Sent Events)
4. Authentication is API key-based (Bearer token)
5. Document processing is async (poll for status)
6. LightRAG requires persistent storage (don't lose the volume!)

**Next Steps:**
- Read API reference: `docs/user/api-reference.md`
- Try SDK examples: `sdk/examples/` or `sdk-ts/examples/`
- Deploy with Docker: `docker-compose up -d`
- Explore frontend integration: `src/README.md`

---

**Questions?** Check the other docs in `/docs` or open an issue on GitHub!
