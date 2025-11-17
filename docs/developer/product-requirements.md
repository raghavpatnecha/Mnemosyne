# Mnemosyne: Open-Source RAG-as-a-Service Platform
## Deep Analysis & Implementation Plan

**Date:** 2025-11-14 (Final)
**Project Type:** Open-Source RAG-as-a-Service (like Ragie.ai)
**Approach:** Original implementation with SurfSense as architectural reference

---

## Executive Summary

**What We're Building:**
An **open-source RAG-as-a-Service platform** that provides:
- Simple, powerful API (ingest anything → retrieve anything)
- SDKs for Python, TypeScript, and REST
- Self-hostable OR managed service option
- Developer-first experience (API-first architecture)

**NOT a fork** - We're building original implementation, using:
- **Ragie.ai** as API/DX inspiration (simple, powerful developer experience)
- **SurfSense** as architectural reference (proven patterns, best practices)
- **LightRAG** as retrieval engine (graph-based, cost-efficient)
- **Mnemosyne frontend** as reference implementation/demo

---

## Part 1: Competitive Analysis

### Ragie.ai (Managed RAG-as-a-Service)

**API Design:**
```python
# Ingestion - Single endpoint for everything
ragie.documents.create(
    file=open("document.pdf", "rb"),
    metadata={"category": "research"}
)

# Retrieval - Simple query
results = ragie.retrievals.retrieve(
    query="What is RAG?",
    rerank=True,
    top_k=10
)
```

**Key Features:**
- ✅ **99.4% recall accuracy** (verified against LegalBench)
- ✅ **Simple API** (2 main endpoints: `/documents`, `/retrievals`)
- ✅ **Multi-source connectors** (Google Drive, Notion, Slack, etc.)
- ✅ **Multimodal** (text, PDFs, images, audio, video)
- ✅ **Advanced retrieval** (hybrid search, reranking, entity extraction)
- ✅ **Security** (SOC 2, GDPR, HIPAA, AES-256 encryption)
- ✅ **Managed** (no infrastructure to manage)

**Pricing:**
- Free tier (developer)
- Starter ($99/month)
- Pro ($499/month)
- Enterprise (custom)

**Limitations:**
- ❌ **Closed-source** (vendor lock-in)
- ❌ **Managed only** (can't self-host)
- ❌ **Pricing** (can get expensive at scale)

---

### SurfSense (Open-Source NotebookLM Alternative)

**Architecture Patterns:**
```
Frontend (Next.js) → Backend (FastAPI) → Database (PostgreSQL + pgvector)
                  ↓
            Celery + Redis (async tasks)
                  ↓
      LangGraph agents + LiteLLM (150+ LLMs)
```

**Key Features:**
- ✅ **Open-source** (Apache 2.0)
- ✅ **Self-hostable** (Docker Compose)
- ✅ **50+ file formats** (via LlamaCloud/Unstructured/Docling)
- ✅ **Hybrid search** (semantic + full-text with RRF)
- ✅ **Two-tier RAG** (document-level → chunk-level)
- ✅ **Advanced** (reranking, Chonkie chunking, 150+ LLMs)
- ✅ **Podcast generation** (NotebookLM-style)

**Architecture Learnings:**
- ✅ **FastAPI** (1,800+ QPS async, great DX)
- ✅ **PostgreSQL + pgvector** (mature, production-ready)
- ✅ **Celery + Redis** (async processing, background jobs)
- ✅ **LangGraph** (agent orchestration)
- ✅ **LiteLLM** (unified LLM interface - 150+ models)
- ✅ **Two-tier retrieval** (coarse → fine)
- ✅ **Hybrid search + RRF** (better accuracy)

**Limitations for Our Use Case:**
- ❌ **Not API-first** (built as web app, not service)
- ❌ **No SDK** (no Python/TypeScript client libraries)
- ❌ **Monolithic** (frontend + backend coupled)
- ❌ **Not multi-tenant** (designed for single user)

---

## Part 2: Mnemosyne Platform Design

### Vision & Goals

**Mission:**
Provide developers with **the simplest, most powerful open-source RAG API** to build AI applications.

**Core Principles:**
1. **Developer-First:** API/SDK so simple, you can integrate in 5 minutes
2. **Production-Ready:** Built for scale, security, and reliability
3. **Open-Source:** No vendor lock-in, self-hostable, community-driven
4. **Multimodal:** Ingest and retrieve across all content types
5. **Flexible:** Works with any LLM, any embedding model, any vector DB

**Unique Value Proposition:**
> "Ragie.ai's developer experience + SurfSense's open-source power + LightRAG's efficiency = Mnemosyne"

---

### API Design (Ragie-Inspired)

#### Core Endpoints

**1. Ingestion API - `/documents`**

```http
POST /api/v1/documents
Content-Type: multipart/form-data

{
  "file": <binary>,
  "metadata": {
    "category": "research",
    "tags": ["AI", "RAG"],
    "user_id": "user_123"
  }
}

Response:
{
  "document_id": "doc_abc123",
  "status": "processing",
  "chunks_created": 0,
  "entities_extracted": 0
}
```

**Supported Ingestion Methods:**
- File upload (50+ formats)
- URL ingestion (web pages, PDFs)
- Raw text ingestion
- Connector sync (Google Drive, Notion, Slack, etc.)

**2. Retrieval API - `/retrievals`**

```http
POST /api/v1/retrievals
Content-Type: application/json

{
  "query": "What is RAG?",
  "top_k": 10,
  "rerank": true,
  "filter": {
    "metadata.category": "research"
  },
  "mode": "hybrid"  // semantic, keyword, or hybrid
}

Response:
{
  "results": [
    {
      "chunk_id": "chunk_xyz789",
      "content": "RAG stands for...",
      "score": 0.95,
      "document": {
        "id": "doc_abc123",
        "title": "RAG Overview",
        "metadata": {...}
      },
      "entities": ["RAG", "retrieval", "generation"]
    }
  ],
  "query_id": "query_def456",
  "latency_ms": 234
}
```

**3. Chat API - `/chat`** (conversational retrieval)

```http
POST /api/v1/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "What is RAG?"},
    {"role": "assistant", "content": "RAG is..."},
    {"role": "user", "content": "How does it work?"}
  ],
  "session_id": "session_xyz",
  "stream": true
}

Response (SSE):
data: {"delta": "RAG", "chunk_ids": ["chunk_1"]}
data: {"delta": " works", "chunk_ids": ["chunk_1", "chunk_2"]}
...
data: {"done": true, "sources": [...]}
```

**4. Management APIs**

```http
GET    /api/v1/documents           # List documents
GET    /api/v1/documents/{id}      # Get document details
DELETE /api/v1/documents/{id}      # Delete document
POST   /api/v1/documents/{id}/reindex  # Re-process

GET    /api/v1/connectors          # List available connectors
POST   /api/v1/connectors/{type}/connect  # Connect to source
GET    /api/v1/connectors/{id}/sync       # Sync connector

GET    /api/v1/health              # Health check
GET    /api/v1/stats               # Usage statistics
```

---

### SDK Design

#### Python SDK

```python
from mnemosyne import Mnemosyne

# Initialize client
client = Mnemosyne(api_key="mn_key_...")

# Ingest document
doc = client.documents.create(
    file=open("research.pdf", "rb"),
    metadata={"category": "AI"}
)

# Query
results = client.retrievals.retrieve(
    query="What is RAG?",
    top_k=10,
    rerank=True
)

# Chat
for chunk in client.chat.stream(
    messages=[{"role": "user", "content": "Explain RAG"}],
    session_id="session_1"
):
    print(chunk.delta, end="")
```

#### TypeScript SDK

```typescript
import { Mnemosyne } from "@mnemosyne/sdk";

const client = new Mnemosyne({ apiKey: "mn_key_..." });

// Ingest
const doc = await client.documents.create({
  file: fileBuffer,
  metadata: { category: "AI" }
});

// Query
const results = await client.retrievals.retrieve({
  query: "What is RAG?",
  topK: 10,
  rerank: true
});

// Chat (streaming)
const stream = await client.chat.stream({
  messages: [{ role: "user", content: "Explain RAG" }],
  sessionId: "session_1"
});

for await (const chunk of stream) {
  process.stdout.write(chunk.delta);
}
```

---

### Architecture (SurfSense-Inspired, Original Implementation)

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                             │
│  Python SDK  |  TypeScript SDK  |  REST API  |  CLI Tool    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   API GATEWAY (FastAPI)                      │
│  - Authentication (JWT, API keys)                            │
│  - Rate limiting                                             │
│  - Request validation                                        │
│  - Response formatting                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────────┐ ┌───▼──────┐ ┌─────▼──────┐
│  INGESTION API  │ │ QUERY API│ │  CHAT API  │
│                 │ │          │ │            │
│ /documents      │ │/retrievals│ │ /chat      │
└────────┬────────┘ └───┬──────┘ └─────┬──────┘
         │              │               │
         │              │               │
┌────────▼──────────────▼───────────────▼──────────────────┐
│                   SERVICE LAYER                           │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │  Ingest      │  │  Retrieval   │  │  Chat          │ │
│  │  Service     │  │  Service     │  │  Service       │ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────┘ │
│         │                 │                     │         │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌────────▼───────┐ │
│  │  Document    │  │  LightRAG    │  │  LLM           │ │
│  │  Processor   │  │  Engine      │  │  Service       │ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────┘ │
│         │                 │                     │         │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌────────▼───────┐ │
│  │  Chunking    │  │  Reranker    │  │  Embedding     │ │
│  │  (Chonkie)   │  │  Service     │  │  Service       │ │
│  └──────────────┘  └──────────────┘  └────────────────┘ │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│                    DATA LAYER                               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PostgreSQL   │  │ Redis        │  │ File Storage │    │
│  │ + pgvector   │  │ (Cache/Queue)│  │ (S3/Local)   │    │
│  │              │  │              │  │              │    │
│  │ - Documents  │  │ - Sessions   │  │ - Uploads    │    │
│  │ - Chunks     │  │ - Tasks      │  │ - Processed  │    │
│  │ - Entities   │  │ - Cache      │  │              │    │
│  │ - Embeddings │  │              │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  ASYNC WORKER LAYER (Celery)                 │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Document     │  │ Indexing     │  │ Connector    │    │
│  │ Processing   │  │ Tasks        │  │ Sync Tasks   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     CONNECTOR LAYER                          │
│  Google Drive | Notion | Slack | GitHub | Gmail | More...  │
└─────────────────────────────────────────────────────────────┘
```

---

### Technology Stack (Final)

**API Layer:**
- **FastAPI** (async, 1,800+ QPS, OpenAPI docs auto-generated)
- **Pydantic** (request/response validation)
- **FastAPI Users** (authentication, JWT, OAuth)

**Retrieval Engine:**
- **LightRAG** (graph-based, 99% token reduction)
- **PostgreSQL + pgvector** (vector + graph storage)
- **Hybrid Search** (semantic + keyword with RRF)
- **Reranker** (Flashrank local or Cohere API)

**Processing Pipeline:**
- **Chonkie** (advanced chunking with LateChunker)
- **MinerU + Docling** (multimodal document parsing)
- **Whisper API** (audio/video transcription)

**LLM Integration:**
- **LiteLLM** (150+ LLMs: OpenAI, Anthropic, Ollama, etc.)
- **LangChain** (agent orchestration)
- **Streaming** (SSE for real-time responses)

**Async Processing:**
- **Celery** (distributed task queue)
- **Redis** (message broker + caching)
- **Flower** (task monitoring)

**Data Storage:**
- **PostgreSQL 16+** (primary database)
- **pgvector 0.8+** (vector similarity)
- **Redis 7+** (cache + queue)
- **S3 / Local** (file storage)

**Embeddings:**
- **text-embedding-3-large** (OpenAI, 3072d)
- **sentence-transformers** (local alternative)
- **Configurable** (any embedding model via LiteLLM)

---

## Part 3: Implementation Plan (8 Weeks)

### Phase 1: Core API & Infrastructure (Weeks 1-2)

**Goal:** Build API-first foundation with basic ingest/retrieve

**Week 1: Foundation**
- [ ] Project setup (monorepo: api/, sdk/, frontend/)
- [ ] FastAPI boilerplate (routes, models, middleware)
- [ ] PostgreSQL + pgvector setup (Docker Compose)
- [ ] Authentication system (API keys, JWT)
- [ ] Database models (Document, Chunk, Entity, Embedding)
- [ ] Basic `/documents` endpoint (file upload)
- [ ] Basic `/retrievals` endpoint (vector search)

**Week 2: Processing Pipeline**
- [ ] Celery + Redis setup
- [ ] Document processing service
  - File type detection
  - Docling integration (PDFs, Office)
  - Text extraction
- [ ] Chunking service (Chonkie)
- [ ] Embedding service (text-embedding-3-large)
- [ ] Vector indexing (pgvector)
- [ ] Background task queue (async processing)

**Deliverables:**
- ✅ Working API (ingest file → process → vector search)
- ✅ Docker Compose setup (PostgreSQL, Redis, FastAPI, Celery)
- ✅ OpenAPI docs auto-generated
- ✅ Basic tests (upload, search)

---

### Phase 2: LightRAG Integration (Weeks 3-4)

**Goal:** Add graph-based retrieval for better accuracy

**Week 3: LightRAG Core**
- [ ] Install & configure LightRAG
- [ ] Knowledge graph storage (PostgreSQL)
- [ ] Entity extraction pipeline
- [ ] Relationship detection
- [ ] Graph construction from documents
- [ ] Dual-level retrieval (low + high level)
- [ ] Graph traversal queries

**Week 4: Advanced Retrieval**
- [ ] Hybrid search implementation
  - Semantic search (vectors)
  - Keyword search (full-text)
  - RRF fusion
- [ ] Reranking layer (Flashrank)
- [ ] Metadata filtering
- [ ] Citation tracking (chunk → document linking)
- [ ] Performance optimization (indexing, caching)

**Deliverables:**
- ✅ LightRAG-powered retrieval (graph + vectors)
- ✅ Hybrid search working
- ✅ Reranking improves results
- ✅ 10x better accuracy vs naive vector search

---

### Phase 3: SDK & Chat API (Weeks 5-6)

**Goal:** Developer experience (SDKs + conversational retrieval)

**Week 5: SDKs**
- [ ] Python SDK
  - Client class
  - Documents API
  - Retrievals API
  - Chat API
  - Error handling
  - Async support
  - Publish to PyPI
- [ ] TypeScript SDK
  - Client class
  - Same API surface
  - Streaming support
  - Publish to npm

**Week 6: Chat API**
- [ ] `/chat` endpoint (SSE streaming)
- [ ] Session management
- [ ] Context window handling
- [ ] LLM integration (OpenAI, Ollama)
- [ ] Source attribution (inline citations)
- [ ] Follow-up question generation
- [ ] Update Mnemosyne frontend to use SDK

**Deliverables:**
- ✅ Python SDK on PyPI (`pip install mnemosyne-sdk`)
- ✅ TypeScript SDK on npm (`npm install @mnemosyne/sdk`)
- ✅ Chat API with streaming
- ✅ Mnemosyne frontend using SDK

---

### Phase 4: Connectors & Production (Weeks 7-8)

**Goal:** Multi-source ingestion + production readiness

**Week 7: Connectors**
- [ ] Connector framework (abstract base class)
- [ ] Implement 3-5 core connectors:
  - Google Drive (OAuth, sync files)
  - Notion (API, sync pages/databases)
  - Slack (sync channels/messages)
  - GitHub (sync repos/issues/docs)
  - YouTube (video transcription)
- [ ] Connector sync scheduler (Celery periodic tasks)
- [ ] Connector management API

**Week 8: Production Polish**
- [ ] Multi-tenancy support
  - User isolation
  - Quota management
  - Usage tracking
- [ ] Observability
  - Logging (structured)
  - Metrics (Prometheus)
  - Tracing (OpenTelemetry optional)
- [ ] Security hardening
  - Rate limiting
  - Input sanitization
  - CORS configuration
- [ ] Deployment
  - Production docker-compose.yml
  - Kubernetes manifests (optional)
  - Environment configs
- [ ] Documentation
  - API reference (auto-generated)
  - SDK guides
  - Deployment guide
  - Contributing guide

**Deliverables:**
- ✅ 5+ connectors working
- ✅ Multi-tenant architecture
- ✅ Production deployment ready
- ✅ Comprehensive documentation

---

## Part 4: Detailed File Structure

```
mnemosyne/
├── api/                              # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app entry
│   │   ├── config.py                 # Configuration
│   │   ├── dependencies.py           # Dependency injection
│   │   │
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── documents.py      # /documents endpoints
│   │   │   │   ├── retrievals.py     # /retrievals endpoints
│   │   │   │   ├── chat.py           # /chat endpoints
│   │   │   │   ├── connectors.py     # /connectors endpoints
│   │   │   │   └── health.py         # /health endpoints
│   │   │
│   │   ├── models/                   # Pydantic models
│   │   │   ├── document.py
│   │   │   ├── retrieval.py
│   │   │   ├── chat.py
│   │   │   └── connector.py
│   │   │
│   │   ├── services/                 # Business logic
│   │   │   ├── ingest/
│   │   │   │   ├── document_service.py
│   │   │   │   ├── parser_service.py  # MinerU, Docling
│   │   │   │   ├── chunking_service.py # Chonkie
│   │   │   │   └── embedding_service.py
│   │   │   │
│   │   │   ├── retrieval/
│   │   │   │   ├── lightrag_service.py
│   │   │   │   ├── vector_service.py
│   │   │   │   ├── hybrid_service.py  # Semantic + keyword
│   │   │   │   └── reranker_service.py
│   │   │   │
│   │   │   ├── chat/
│   │   │   │   ├── chat_service.py
│   │   │   │   ├── llm_service.py     # LiteLLM integration
│   │   │   │   └── session_service.py
│   │   │   │
│   │   │   └── connectors/
│   │   │       ├── base.py            # Abstract connector
│   │   │       ├── google_drive.py
│   │   │       ├── notion.py
│   │   │       ├── slack.py
│   │   │       └── github.py
│   │   │
│   │   ├── db/                       # Database
│   │   │   ├── models.py             # SQLAlchemy models
│   │   │   ├── session.py            # DB session
│   │   │   └── migrations/           # Alembic migrations
│   │   │
│   │   ├── tasks/                    # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   ├── document_tasks.py
│   │   │   ├── indexing_tasks.py
│   │   │   └── connector_tasks.py
│   │   │
│   │   ├── auth/                     # Authentication
│   │   │   ├── jwt.py
│   │   │   └── api_keys.py
│   │   │
│   │   └── utils/
│   │       ├── logger.py
│   │       └── exceptions.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── sdk/                              # Client SDKs
│   ├── python/
│   │   ├── mnemosyne/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── resources/
│   │   │   │   ├── documents.py
│   │   │   │   ├── retrievals.py
│   │   │   │   └── chat.py
│   │   │   └── types/
│   │   ├── setup.py
│   │   ├── README.md
│   │   └── pyproject.toml
│   │
│   └── typescript/
│       ├── src/
│       │   ├── index.ts
│       │   ├── client.ts
│       │   ├── resources/
│       │   │   ├── documents.ts
│       │   │   ├── retrievals.ts
│       │   │   └── chat.ts
│       │   └── types/
│       ├── package.json
│       ├── tsconfig.json
│       └── README.md
│
├── frontend/                         # Mnemosyne Demo (reference implementation)
│   ├── templates/
│   │   ├── index.html               # Chat + upload UI
│   │   └── library.html             # Document library
│   ├── static/
│   │   ├── js/
│   │   │   ├── script.js            # Uses Python/TS SDK
│   │   │   └── upload.js
│   │   └── css/
│   └── app.py                       # Lightweight server
│
├── docs/
│   ├── api/                          # API documentation
│   ├── sdk/                          # SDK guides
│   ├── deployment/                   # Deployment guides
│   └── contributing/                 # Contributing guide
│
├── .claude/
│   ├── skills/
│   └── CLAUDE.md
│
├── docker-compose.yml               # Full stack
├── docker-compose.prod.yml          # Production
├── README.md
├── LICENSE (Apache 2.0)
└── CONTRIBUTING.md
```

---

## Part 5: What We Learn from SurfSense (Reference, Not Fork)

### Architecture Patterns to Borrow:

**1. Two-Tier RAG**
```python
# SurfSense pattern (we implement our own)
def retrieve(query):
    # Tier 1: Document-level retrieval
    relevant_docs = search_documents(query, top_k=20)

    # Tier 2: Chunk-level retrieval within docs
    relevant_chunks = []
    for doc in relevant_docs:
        chunks = search_chunks(query, document_id=doc.id, top_k=5)
        relevant_chunks.extend(chunks)

    # Rerank final results
    return rerank(relevant_chunks)
```

**2. Hybrid Search with RRF**
```python
# Learn from SurfSense, implement ourselves
def hybrid_search(query, top_k=10):
    # Semantic search (vectors)
    semantic_results = vector_search(query, top_k=top_k*2)

    # Keyword search (full-text)
    keyword_results = fulltext_search(query, top_k=top_k*2)

    # Reciprocal Rank Fusion
    fused_results = rrf_fusion(semantic_results, keyword_results)

    return fused_results[:top_k]
```

**3. Async Task Processing**
```python
# Celery pattern from SurfSense
@celery_app.task
def process_document(document_id):
    doc = get_document(document_id)

    # Parse
    content = parse_document(doc.file_path)

    # Chunk
    chunks = chunk_content(content)

    # Embed
    embeddings = generate_embeddings(chunks)

    # Index
    index_chunks(chunks, embeddings)

    # Update status
    doc.status = "indexed"
    doc.save()
```

**4. LiteLLM Integration**
```python
# Learn from SurfSense's model flexibility
from litellm import acompletion

async def query_llm(prompt, model="gpt-4o-mini"):
    response = await acompletion(
        model=model,  # Works with 150+ models
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )

    async for chunk in response:
        yield chunk.choices[0].delta.content
```

**5. Connector Pattern**
```python
# Abstract base class (inspired by SurfSense)
class Connector(ABC):
    @abstractmethod
    async def authenticate(self, credentials):
        pass

    @abstractmethod
    async def list_documents(self):
        pass

    @abstractmethod
    async def fetch_document(self, doc_id):
        pass

    @abstractmethod
    async def sync(self):
        pass
```

### What We DON'T Take from SurfSense:

- ❌ **Monolithic structure** (we're API-first)
- ❌ **Single-user focus** (we need multi-tenancy)
- ❌ **Coupled frontend** (we separate concerns)
- ❌ **No SDK** (we build Python + TypeScript SDKs)
- ❌ **Podcast generation** (not core for RAG-as-a-Service)

---

## Part 6: Database Schema

### Core Tables

**documents**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(500),
    content_type VARCHAR(100),
    file_size BIGINT,
    file_path TEXT,
    url TEXT,
    source VARCHAR(50),  -- 'upload', 'url', 'connector'
    connector_id UUID,
    status VARCHAR(50) DEFAULT 'processing',  -- processing, indexed, failed
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);
```

**chunks**
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(3072),  -- pgvector
    chunk_index INT,
    token_count INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_document_id (document_id)
);

-- Vector index
CREATE INDEX chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**entities** (LightRAG)
```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),  -- person, organization, location, concept, etc.
    description TEXT,
    embedding vector(3072),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_name (name),
    INDEX idx_type (type)
);

CREATE INDEX entities_embedding_idx ON entities
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**relationships** (LightRAG)
```sql
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100),
    confidence FLOAT,
    document_ids UUID[],  -- Which documents mention this relationship
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_source (source_entity_id),
    INDEX idx_target (target_entity_id),
    INDEX idx_type (relationship_type)
);
```

**entity_chunks** (linking)
```sql
CREATE TABLE entity_chunks (
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES chunks(id) ON DELETE CASCADE,
    PRIMARY KEY (entity_id, chunk_id)
);
```

**users**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    api_key VARCHAR(100) UNIQUE,
    plan VARCHAR(50) DEFAULT 'free',  -- free, pro, enterprise
    quota_documents INT DEFAULT 1000,
    quota_retrievals INT DEFAULT 10000,
    usage_documents INT DEFAULT 0,
    usage_retrievals INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_api_key (api_key)
);
```

**connectors**
```sql
CREATE TABLE connectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50),  -- 'google_drive', 'notion', 'slack', etc.
    credentials JSONB,  -- Encrypted OAuth tokens
    config JSONB DEFAULT '{}',
    last_sync TIMESTAMP,
    sync_frequency INT DEFAULT 3600,  -- Seconds
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_type (type)
);
```

**chat_sessions**
```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    messages JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id)
);
```

---

## Part 7: Key Differences from Original Plans

### Original Plan (Build from Scratch):
- Focus: Personal tool
- Timeline: 8 weeks
- Architecture: Monolithic
- No SDK

### Revised Plan #1 (Fork SurfSense):
- Focus: Quick deployment
- Timeline: 4 weeks
- Architecture: Fork + customize
- No SDK

### **FINAL Plan (API-First Platform):**
- **Focus:** Open-source RAG-as-a-Service
- **Timeline:** 8 weeks
- **Architecture:** API-first, multi-tenant, SDK-driven
- **Deliverables:** API + Python SDK + TypeScript SDK + Demo Frontend
- **Deployment:** Self-hostable AND managed service option
- **Inspiration:** Ragie.ai (API/DX) + SurfSense (architecture) + LightRAG (retrieval)

---

## Part 8: Success Metrics

### Functional Requirements
- [ ] **Simple API:** 2 core endpoints (`/documents`, `/retrievals`)
- [ ] **Multimodal:** 50+ file formats supported
- [ ] **Connectors:** 5+ external integrations
- [ ] **SDKs:** Python + TypeScript published
- [ ] **Graph retrieval:** LightRAG working
- [ ] **Hybrid search:** Semantic + keyword + RRF
- [ ] **Chat API:** Streaming with citations

### Performance Requirements
- [ ] **API latency:** < 100ms (p95) for simple queries
- [ ] **Retrieval latency:** < 3s (p95) with reranking
- [ ] **Upload processing:** < 30s for 10MB PDF
- [ ] **Throughput:** 1,000+ QPS (FastAPI async)
- [ ] **Concurrent users:** 100+

### Developer Experience
- [ ] **Time to first query:** < 5 minutes with SDK
- [ ] **API docs:** Auto-generated (OpenAPI)
- [ ] **SDK docs:** Comprehensive guides
- [ ] **Examples:** 10+ use cases documented

### Quality Requirements
- [ ] **Retrieval accuracy:** > 90% (RAGAS)
- [ ] **Uptime:** 99.9% (production)
- [ ] **Test coverage:** > 80%

---

## Part 9: Go-to-Market Strategy

### Open Source First
- **License:** Apache 2.0 (permissive, commercial-friendly)
- **GitHub:** Public repository from day 1
- **Community:** Discord, GitHub Discussions
- **Documentation:** Comprehensive guides, API reference
- **Examples:** Starter templates, use case examples

### Deployment Options

**Self-Hosted (Free)**
```bash
git clone https://github.com/raghavpatnecha/mnemosyne.git
cd mnemosyne
docker-compose up -d

# Get API key
curl http://localhost:8000/api/v1/auth/register \
  -d '{"email": "user@example.com", "password": "..."}'

# Use SDK
pip install mnemosyne-sdk
```

**Managed Service (Paid)**
- Hosted at `api.mnemosyne.ai`
- Free tier: 1,000 docs, 10K retrievals/month
- Pro tier: $99/month (10K docs, 100K retrievals)
- Enterprise: Custom pricing

### Positioning

**Tagline:**
> "The open-source RAG API developers love. Ragie.ai's simplicity, without the lock-in."

**Unique Value Props:**
1. **Open Source** - No vendor lock-in, self-hostable
2. **Simple API** - 5-minute integration with SDK
3. **Production-Ready** - Built with SurfSense-proven patterns
4. **Multimodal** - Text, PDFs, images, audio, video
5. **Graph-Powered** - LightRAG for 10x better retrieval
6. **Flexible** - Works with any LLM, any embedding model

---

## Part 10: Next Steps - Immediate Actions

### This Week: Deep Dive & Planning

**Day 1-2: SurfSense Code Review**
- [ ] Clone SurfSense locally
- [ ] Run it via Docker Compose
- [ ] Upload test documents
- [ ] Understand code structure
  - How does document processing work?
  - How is Celery organized?
  - How does the two-tier RAG work?
  - How are connectors implemented?
- [ ] Document findings

**Day 3-4: API Design Review**
- [ ] Finalize API endpoints (you + me)
- [ ] Design request/response models
- [ ] Plan authentication (API keys vs JWT)
- [ ] Decide on metadata schema
- [ ] Review Ragie.ai docs for DX inspiration

**Day 5: Architecture Decision Records**
- [ ] Document key decisions:
  - Why LightRAG over GraphRAG?
  - Why FastAPI over Flask/Django?
  - Why PostgreSQL over dedicated vector DB?
  - Why Celery over other task queues?
- [ ] Create ADR documents

### Next Week: Week 1 of Implementation

**Sprint 1 Goals:**
- [ ] FastAPI project setup
- [ ] PostgreSQL + pgvector + Docker Compose
- [ ] Basic `/documents` POST endpoint
- [ ] File upload handling
- [ ] Database models (Document, Chunk)
- [ ] Basic tests

---

## Conclusion

**What We're Building:**
An **open-source RAG-as-a-Service platform** that combines:
- ✅ **Ragie.ai's simplicity** (API/SDK design)
- ✅ **SurfSense's power** (architecture patterns)
- ✅ **LightRAG's efficiency** (graph retrieval)
- ✅ **Original implementation** (API-first, multi-tenant)

**Approach:**
- **NOT a fork** - Original codebase
- **Reference SurfSense** - Learn best practices
- **Inspired by Ragie** - API/DX simplicity
- **8-week timeline** - Production-ready platform

**Deliverables:**
1. **API** (FastAPI, multimodal, graph-powered)
2. **Python SDK** (PyPI package)
3. **TypeScript SDK** (npm package)
4. **Demo Frontend** (Mnemosyne UI using SDK)
5. **Documentation** (API ref, SDK guides, deployment)

**Timeline:** 8 weeks to v1.0
**License:** Apache 2.0 (open source)
**Deployment:** Self-hosted OR managed

---

**Ready to start?**

Let's begin with the **SurfSense deep dive** to understand their code, then we'll design our API and start building Week 1 of the implementation.

What would you like to do first:
1. Clone SurfSense and review it together?
2. Design the API contracts in detail?
3. Set up the initial project structure?
4. Something else?

---

**Prepared by:** Claude (Mnemosyne Development Team)
**Status:** Ready for Deep Dive
**Next Action:** SurfSense code review → API design → Week 1 implementation
