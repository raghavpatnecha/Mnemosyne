# Mnemosyne API Design Specification

**Version**: 1.0
**Status**: Draft
**Last Updated**: 2025-11-14

## Overview

Mnemosyne is an open-source RAG-as-a-Service platform inspired by Ragie.ai, designed with API-first principles. This document defines the complete API specification, database schema, and SDK contracts.

### Design Philosophy

1. **Developer-First**: Simple, intuitive API that requires minimal code
2. **API-First**: Everything accessible via REST API
3. **Self-Hostable**: Full deployment control
4. **Multimodal**: Support for documents, images, videos, audio
5. **Cost-Efficient**: LightRAG integration (99% token reduction)
6. **Production-Ready**: Based on proven SurfSense patterns

---

## Core Concepts

### Multi-Tenancy Hierarchy

```
Organization (optional for self-hosted)
  └── User (API key owner)
      └── Collection (logical grouping of documents)
          └── Document (ingested content)
              └── Chunk (retrieved units)
                  └── Entity/Relationship (knowledge graph)
```

### Content Lifecycle

```
Ingest → Hash → Parse → Chunk → Embed → Index → Retrieve → Rerank → Generate
```

---

## Authentication

### API Key Authentication

All requests require an API key in the header:

```http
Authorization: Bearer mn_key_1234567890abcdef
```

### Key Types

1. **Live Keys**: `mn_live_...` - Production use
2. **Test Keys**: `mn_test_...` - Development/testing
3. **Admin Keys**: `mn_admin_...` - Platform management (self-hosted)

### Key Scopes

- `documents:read` - Read document metadata
- `documents:write` - Create/update/delete documents
- `retrievals:read` - Perform retrievals
- `chat:read` - Use chat endpoints
- `collections:manage` - Manage collections

---

## API Endpoints

### Base URL

```
Production: https://api.mnemosyne.ai/v1
Self-Hosted: https://your-domain.com/api/v1
```

---

## 1. Collections API

### Create Collection

Create a new document collection.

**Endpoint**: `POST /collections`

**Request Body**:
```json
{
  "name": "company-docs",
  "description": "Internal company documentation",
  "metadata": {
    "department": "engineering",
    "visibility": "private"
  },
  "config": {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "embedding_model": "text-embedding-3-small",
    "enable_hybrid_search": true,
    "enable_knowledge_graph": true
  }
}
```

**Response**: `201 Created`
```json
{
  "id": "col_abc123",
  "name": "company-docs",
  "description": "Internal company documentation",
  "metadata": {
    "department": "engineering",
    "visibility": "private"
  },
  "config": {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "embedding_model": "text-embedding-3-small",
    "enable_hybrid_search": true,
    "enable_knowledge_graph": true
  },
  "document_count": 0,
  "created_at": "2025-11-14T10:30:00Z",
  "updated_at": "2025-11-14T10:30:00Z"
}
```

### List Collections

**Endpoint**: `GET /collections`

**Query Parameters**:
- `limit` (int, default: 20, max: 100)
- `offset` (int, default: 0)
- `sort_by` (string: "created_at", "name", "document_count")
- `order` (string: "asc", "desc")

**Response**: `200 OK`
```json
{
  "data": [
    {
      "id": "col_abc123",
      "name": "company-docs",
      "description": "Internal company documentation",
      "document_count": 42,
      "created_at": "2025-11-14T10:30:00Z",
      "updated_at": "2025-11-14T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

### Get Collection

**Endpoint**: `GET /collections/{collection_id}`

**Response**: `200 OK` (same schema as create response)

### Update Collection

**Endpoint**: `PATCH /collections/{collection_id}`

**Request Body**: (all fields optional)
```json
{
  "name": "updated-name",
  "description": "Updated description",
  "metadata": {
    "department": "product"
  }
}
```

**Response**: `200 OK` (updated collection object)

### Delete Collection

**Endpoint**: `DELETE /collections/{collection_id}`

**Query Parameters**:
- `cascade` (boolean, default: false) - Delete all documents in collection

**Response**: `204 No Content`

---

## 2. Documents API

### Create Document (File Upload)

Upload a file for processing.

**Endpoint**: `POST /documents`

**Request**: `multipart/form-data`
```
collection_id: col_abc123
file: document.pdf
metadata: {"author": "John Doe", "category": "technical"}
```

**Response**: `202 Accepted`
```json
{
  "id": "doc_xyz789",
  "collection_id": "col_abc123",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size_bytes": 1048576,
  "status": "processing",
  "metadata": {
    "author": "John Doe",
    "category": "technical"
  },
  "created_at": "2025-11-14T10:35:00Z",
  "updated_at": "2025-11-14T10:35:00Z"
}
```

**Supported Formats**: PDF, DOCX, PPTX, XLSX, TXT, MD, HTML, CSV, JSON, XML, EPUB, images (PNG, JPG, etc.), audio (MP3, WAV), video (MP4, etc.)

**Document Type Hints** (Optional):

You can provide a `document_type` hint in metadata to help the system apply specialized domain processing:

```json
{
  "collection_id": "col_abc123",
  "file": "contract.pdf",
  "metadata": {
    "document_type": "legal"  // legal, academic, qa, table, or general
  }
}
```

**Available Document Types**:
- `legal` - Contracts, regulations, policies (extracts hierarchical structure: Parts, Sections, Articles, Clauses)
- `academic` - Research papers, theses (extracts title, authors, abstract, sections, references)
- `qa` - FAQ documents, exam papers, interview questions (extracts Q&A pairs)
- `table` - Spreadsheets, tabular data (enhances table structure recognition)
- `general` - Default processing (no specialized handling)

If not specified, the system auto-detects document type using metadata heuristics and optional LLM classification.

### Create Document (URL)

Ingest content from a URL.

**Endpoint**: `POST /documents/url`

**Request Body**:
```json
{
  "collection_id": "col_abc123",
  "url": "https://example.com/article",
  "metadata": {
    "source": "web",
    "category": "article"
  }
}
```

**Response**: `202 Accepted` (same schema as file upload)

### Create Document (Raw Text)

Ingest raw text content.

**Endpoint**: `POST /documents/text`

**Request Body**:
```json
{
  "collection_id": "col_abc123",
  "content": "This is the raw text content to ingest...",
  "title": "My Document",
  "metadata": {
    "source": "manual",
    "category": "note"
  }
}
```

**Response**: `202 Accepted` (same schema)

### List Documents

**Endpoint**: `GET /documents`

**Query Parameters**:
- `collection_id` (string, required)
- `limit` (int, default: 20, max: 100)
- `offset` (int, default: 0)
- `status` (string: "processing", "completed", "failed")
- `sort_by` (string: "created_at", "title", "size_bytes")
- `order` (string: "asc", "desc")

**Response**: `200 OK`
```json
{
  "data": [
    {
      "id": "doc_xyz789",
      "collection_id": "col_abc123",
      "title": "Technical Documentation",
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "size_bytes": 1048576,
      "status": "completed",
      "chunk_count": 25,
      "metadata": {
        "author": "John Doe",
        "category": "technical"
      },
      "created_at": "2025-11-14T10:35:00Z",
      "updated_at": "2025-11-14T10:36:00Z"
    }
  ],
  "pagination": {
    "total": 42,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### Get Document

**Endpoint**: `GET /documents/{document_id}`

**Response**: `200 OK`
```json
{
  "id": "doc_xyz789",
  "collection_id": "col_abc123",
  "title": "Technical Documentation",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size_bytes": 1048576,
  "status": "completed",
  "chunk_count": 25,
  "content_hash": "sha256:abcd1234...",
  "unique_identifier_hash": "sha256:efgh5678...",
  "metadata": {
    "author": "John Doe",
    "category": "technical"
  },
  "processing_info": {
    "service_used": "docling",
    "processing_time_ms": 1234,
    "chunk_strategy": "recursive",
    "embedding_model": "text-embedding-3-small"
  },
  "created_at": "2025-11-14T10:35:00Z",
  "updated_at": "2025-11-14T10:36:00Z"
}
```

### Update Document

**Endpoint**: `PATCH /documents/{document_id}`

**Request Body**:
```json
{
  "metadata": {
    "author": "Jane Doe",
    "category": "updated"
  }
}
```

**Response**: `200 OK` (updated document object)

### Delete Document

**Endpoint**: `DELETE /documents/{document_id}`

**Response**: `204 No Content`

**Note**: Automatically deletes all associated chunks (cascade delete pattern from SurfSense)

---

## 3. Retrievals API

### Retrieve Documents

Perform semantic search and retrieve relevant document chunks.

**Endpoint**: `POST /retrievals`

**Request Body**:
```json
{
  "collection_id": "col_abc123",
  "query": "How do I deploy the application?",
  "top_k": 10,
  "mode": "hybrid",
  "document_type": "technical",
  "rerank": true,
  "metadata_filter": {
    "category": "technical",
    "author": "John Doe"
  }
}
```

**Parameters**:
- `query` (string, required): Search query (1-1000 chars)
- `mode` (string, default: "semantic"): Search mode
  - `"semantic"`: Vector similarity search
  - `"keyword"`: PostgreSQL full-text search (BM25)
  - `"hybrid"`: RRF fusion of semantic + keyword (recommended) ⭐
  - `"hierarchical"`: Two-tier document → chunk retrieval
  - `"graph"`: LightRAG knowledge graph search with source extraction
- `top_k` (int, default: 10, max: 100): Number of results to return
- `collection_id` (UUID, optional): Filter by specific collection
- `document_type` (string, optional): Filter by document type (legal, academic, qa, table, general)
- `rerank` (boolean, default: false): Apply reranking to improve accuracy by 15-25%
- `enable_graph` (boolean, default: false): Enhance results with knowledge graph context ⚡
- `metadata_filter` (object, optional): Filter by metadata fields

**Response**: `200 OK`
```json
{
  "query": "How do I deploy the application?",
  "mode": "hybrid",
  "total_results": 10,
  "graph_enhanced": false,
  "graph_context": null,
  "results": [
    {
      "chunk_id": "chunk_aaa111",
      "document_id": "doc_xyz789",
      "content": "To deploy the application, follow these steps: 1. Build the Docker image...",
      "score": 0.92,
      "rank": 1,
      "document_metadata": {
        "title": "Deployment Guide",
        "author": "John Doe",
        "category": "technical"
      },
      "chunk_metadata": {
        "page_number": 5,
        "section": "Deployment"
      }
    }
  ]
}
```

### Reranking for Better Accuracy ⭐

Apply optional reranking to improve retrieval accuracy by 15-25% by re-scoring results with specialized models.

**How to Enable**:
```json
{
  "query": "How to deploy?",
  "mode": "hybrid",
  "rerank": true,  // ← Enable reranking
  "top_k": 10
}
```

**Supported Rerankers** (configured via environment variables):
- **Flashrank**: Local cross-encoder (fast, free, no API calls) - Default
- **Cohere**: High-quality API-based (`rerank-english-v3.0`)
- **Jina**: API-based with free tier (`jina-reranker-v1-base-en`)
- **Voyage**: API-based reranking
- **Mixedbread**: API-based reranking

**Configuration**:
```bash
RERANK_ENABLED=true
RERANK_PROVIDER=flashrank  # or cohere, jina, voyage, mixedbread
RERANK_MODEL=ms-marco-MiniLM-L-12-v2  # For flashrank
RERANK_API_KEY=your-key  # For API-based providers
```

**Benefits**:
- Works with all 5 search modes
- Improves relevance scoring
- Re-orders results by query-document relevance
- Optional (disabled by default, no cost unless enabled)

---

### Graph Enhancement (HybridRAG) 🚀 NEW

Enhance any search mode with knowledge graph context by setting `enable_graph: true`.

**What is HybridRAG?**

HybridRAG combines traditional retrieval (vector/keyword/hybrid) with LightRAG's knowledge graph to provide both relevant documents AND relationship context. This is based on production systems from AWS, Neo4j, Databricks, and Cedars-Sinai.

**Request Example**:
```json
{
  "query": "How does protein X interact with disease Y?",
  "mode": "hybrid",
  "enable_graph": true,  // ← Enable graph enhancement
  "top_k": 10
}
```

**How It Works**:
1. Base search (hybrid/semantic/keyword/hierarchical) runs in parallel with LightRAG graph query
2. Results are enriched with graph-sourced chunks
3. Response includes `graph_context` with relationship insights
4. Latency: ~1.5-2x vs base search (parallel execution, not additive)

**Response with Graph Enhancement**:
```json
{
  "query": "How does protein X interact with disease Y?",
  "mode": "hybrid",
  "total_results": 12,
  "graph_enhanced": true,
  "graph_context": "Protein X interacts with Disease Y through pathway Z, involving entities A and B. Research shows...",
  "results": [
    {
      "chunk_id": "chunk_abc123",
      "content": "Protein X binds to receptor Y...",
      "score": 0.94,
      "metadata": {
        "graph_sourced": false  // From base search
      }
    },
    {
      "chunk_id": "chunk_def456",
      "content": "Disease Y pathway involves...",
      "score": 0.68,
      "metadata": {
        "graph_sourced": true   // From graph traversal
      }
    }
  ]
}
```

**When to Use Graph Enhancement**:
- ✅ Queries about relationships ("how does X relate to Y?")
- ✅ Multi-hop reasoning ("connection between A, B, and C?")
- ✅ Research queries requiring context
- ✅ Complex domain-specific questions
- ❌ Simple factual lookups (use base search for speed)
- ❌ High-volume production endpoints (higher latency)

**Performance & Accuracy**:
- **Accuracy Improvement**: 35-80% for relationship-based queries (research-backed)
- **Latency**: 200-500ms (vs 100-300ms for base search)
- **Works With**: semantic, keyword, hybrid, hierarchical modes
- **Note**: NOT compatible with mode="graph" (redundant)

**Configuration**:
```bash
LIGHTRAG_ENABLED=true  # Required for graph enhancement
```

**Compatibility**:
- ✅ All search modes except "graph"
- ✅ Works with reranking (`rerank: true`)
- ✅ Works with caching (faster on repeated queries)
- ✅ Works with query reformulation

---

### Pure Graph Mode Search (LightRAG) ⭐

Use mode `"graph"` for knowledge graph-based retrieval with automatic source extraction.

**Request Example**:
```json
{
  "collection_id": "col_abc123",
  "query": "What are the relationships between Docker and Kubernetes?",
  "mode": "graph",
  "top_k": 10
}
```

**How Graph Mode Works**:
1. LightRAG queries knowledge graph for entity-relationship context
2. System performs semantic search to find actual source chunks in PostgreSQL
3. Returns real chunk IDs and document references for citations
4. Response format consistent with other search modes

**Response**: `200 OK` (Same schema as other modes)
```json
{
  "query": "What are the relationships between Docker and Kubernetes?",
  "results": [
    {
      "chunk_id": "chunk_aaa111",
      "document_id": "doc_xyz789",
      "content": "Kubernetes orchestrates Docker containers by...",
      "score": 0.95,
      "rank": 1,
      "document_metadata": {
        "title": "Container Orchestration Guide",
        "filename": "k8s-guide.pdf"
      },
      "chunk_metadata": {
        "page_number": 12,
        "section": "Docker Integration"
      }
    }
  ],
  "retrieval_metadata": {
    "mode": "graph",
    "total_results": 10,
    "retrieval_time_ms": 78
  }
}
```

**Note**: Graph mode returns actual chunk IDs from your PostgreSQL database, not synthesized results. This ensures you can cite sources and maintain response format consistency across all search modes.

---

## 4. Chat API

RAG-powered conversational AI that uses the retrieval endpoint internally for all search operations.

### Chat Completion

**Endpoint**: `POST /chat`

Supports both OpenAI-compatible messages array and simple message string.

**Request Body (OpenAI-compatible)**:
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "How do I deploy the application?"}
  ],
  "collection_id": "col_abc123",
  "stream": true,
  "model": "gpt-4o",
  "preset": "research",
  "reasoning_mode": "deep",
  "temperature": 0.5,
  "max_tokens": 2000,
  "retrieval": {
    "mode": "hybrid",
    "top_k": 5,
    "rerank": true,
    "enable_graph": true,
    "hierarchical": true,
    "expand_context": true
  },
  "generation": {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**Request Body (Legacy - deprecated)**:
```json
{
  "message": "How do I deploy the application?",
  "collection_id": "col_abc123",
  "stream": true
}
```

### Top-Level Request Parameters

These parameters provide convenient shortcuts that override the nested `generation` config:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | null | LLM model override (e.g., "gpt-4o", "claude-3-opus", "gpt-4o-mini"). Supports any LiteLLM-compatible model. |
| `preset` | string | "detailed" | Answer style preset (see presets table below) |
| `reasoning_mode` | string | "standard" | Reasoning depth: "standard" (single-pass) or "deep" (multi-step iterative) |
| `temperature` | float | null | Temperature override (0.0-2.0). Overrides preset and generation.temperature |
| `max_tokens` | int | null | Max tokens override (1-8192). Overrides preset and generation.max_tokens |
| `custom_instruction` | string | null | Custom instruction appended to the system prompt for additional guidance (e.g., "focus on security aspects", "generate 10 MCQs") |
| `is_follow_up` | boolean | false | Whether this is a follow-up to a previous question. When true, previous context from the session is preserved and used to inform the response. |

### Answer Style Presets

Presets provide predefined configurations for different use cases:

| Preset | Temperature | Max Tokens | Description |
|--------|-------------|------------|-------------|
| `concise` | 0.3 | 500 | Brief, to-the-point answers |
| `detailed` | 0.5 | 2000 | Comprehensive explanations (default) |
| `research` | 0.2 | 4000 | Academic style with thorough analysis |
| `technical` | 0.1 | 3000 | Precise, detail-oriented answers with exact terminology |
| `creative` | 0.8 | 2000 | More exploratory, creative responses |
| `qna` | 0.4 | 4000 | Question generation mode (MCQs, quizzes, study materials) |

**Preset Examples**:
```json
// Concise answer for quick lookups
{"message": "What is RAG?", "preset": "concise"}

// Research-grade response with citations
{"message": "Compare RAG architectures", "preset": "research"}

// Technical precise answer with exact details
{"message": "What are the specifications in this document?", "preset": "technical"}

// Question generation mode
{"message": "Create questions about this topic", "preset": "qna", "custom_instruction": "Generate 10 MCQs with 4 options each"}
```

### Deep Reasoning Mode

The `reasoning_mode: "deep"` enables multi-step iterative reasoning inspired by agentic RAG systems. Instead of a single retrieval-then-generate pass, deep reasoning:

1. **Decomposes** the query into sub-questions
2. **Iteratively retrieves** relevant context for each sub-question
3. **Synthesizes** findings into a comprehensive answer

**When to Use Deep Reasoning**:
- Complex multi-part questions
- Questions requiring analysis across multiple topics
- Research-grade queries needing thorough exploration

**Example Request**:
```json
{
  "message": "Compare the pros and cons of different RAG architectures and recommend which is best for a legal document search system",
  "preset": "research",
  "reasoning_mode": "deep",
  "model": "gpt-4o"
}
```

**Retrieval Configuration Options**:
- `mode`: Search mode - "semantic", "keyword", "hybrid" (default), "graph"
- `top_k`: Number of chunks to retrieve (1-50, default: 5)
- `rerank`: Enable cross-encoder reranking (default: true)
- `enable_graph`: Enable LightRAG knowledge graph enhancement (default: true)
- `hierarchical`: Enable two-tier hierarchical search (default: true)
- `expand_context`: Expand results with surrounding chunks (default: true)
- `metadata_filter`: Metadata filters for retrieval

**Generation Configuration Options** (nested, can be overridden by top-level params):
- `model`: LLM model name (default: "gpt-4o-mini")
- `temperature`: Sampling temperature 0-2 (default: 0.7)
- `max_tokens`: Maximum tokens to generate (default: 1000)
- `top_p`: Nucleus sampling parameter (default: 1.0)
- `frequency_penalty`: Frequency penalty -2 to 2 (default: 0)
- `presence_penalty`: Presence penalty -2 to 2 (default: 0)

**Response (Non-Streaming)**: `200 OK`
```json
{
  "query": "How do I deploy the application?",
  "response": "To deploy the application, follow these steps:\n\n1. Build the Docker image...",
  "sources": [
    {
      "document_id": "doc_xyz789",
      "title": "Deployment Guide",
      "filename": "deploy.pdf",
      "chunk_index": 5,
      "score": 0.92
    }
  ],
  "usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 350,
    "total_tokens": 1600,
    "retrieval_tokens": 800
  },
  "metadata": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "collection_id": "col_abc123",
    "retrieval_mode": "hybrid",
    "model": "gpt-4o-mini",
    "latency_ms": 1250,
    "retrieval_latency_ms": 450,
    "generation_latency_ms": 800,
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

**Note**: Sources are lightweight references containing only document identification and relevance score. The knowledge graph context (when `enable_graph: true`) is used internally to enrich the LLM prompt but is not exposed in the response.

**Response (Streaming)**: `200 OK` with `Content-Type: text/event-stream`

```
data: {"type":"sources","sources":[{"document_id":"doc_xyz789","title":"Deployment Guide","filename":"deploy.pdf","chunk_index":5,"score":0.92}]}

data: {"type":"delta","content":"To"}

data: {"type":"delta","content":" deploy"}

data: {"type":"delta","content":" the"}

...

data: {"type":"usage","usage":{"prompt_tokens":1250,"completion_tokens":350,"total_tokens":1600}}

data: {"type":"done","metadata":{"session_id":"...", "latency_ms":1250, ...}}
```

**Stream Chunk Types**:
- `sources`: Lightweight source references (sent once at start)
- `delta`: Incremental text content
- `usage`: Token usage statistics (sent at end)
- `done`: Stream completion signal with metadata
- `error`: Error message if something fails
- `reasoning_step`: Deep reasoning progress (step number + description)
- `sub_query`: Sub-query being processed during deep reasoning

**Deep Reasoning Streaming Example**:

When using `reasoning_mode: "deep"`, additional chunk types are emitted to show reasoning progress:

```
data: {"type":"reasoning_step","step":1,"description":"Analyzing RAG architecture types"}

data: {"type":"sub_query","query":"What are the main RAG architecture patterns?"}

data: {"type":"sources","sources":[...]}

data: {"type":"reasoning_step","step":2,"description":"Evaluating legal document requirements"}

data: {"type":"sub_query","query":"What are specific requirements for legal document search?"}

data: {"type":"sources","sources":[...]}

data: {"type":"reasoning_step","step":3,"description":"Synthesizing recommendations"}

data: {"type":"delta","content":"Based on my analysis..."}
...
data: {"type":"done","metadata":{...}}
```

### Multi-Turn Chat with Sessions

Use `session_id` for multi-turn conversations. If not provided, a new session is created.

**Request**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {"role": "user", "content": "What about database migrations?"}
  ],
  "collection_id": "col_abc123"
}
```

Mnemosyne maintains conversation history per session and retrieves context for each user message.

### List Chat Sessions

**Endpoint**: `GET /chat/sessions`

**Query Parameters**:
- `limit`: Max sessions to return (default: 20)
- `offset`: Offset for pagination

**Response**: `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "collection_id": "col_abc123",
    "title": "How do I deploy...",
    "created_at": "2025-01-15T10:30:00Z",
    "last_message_at": "2025-01-15T10:35:00Z",
    "message_count": 4
  }
]
```

### Get Session Messages

**Endpoint**: `GET /chat/sessions/{session_id}/messages`

**Response**: `200 OK`
```json
[
  {
    "id": "msg_abc123",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "user",
    "content": "How do I deploy the application?",
    "created_at": "2025-01-15T10:30:00Z"
  },
  {
    "id": "msg_def456",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "assistant",
    "content": "To deploy the application...",
    "created_at": "2025-01-15T10:30:05Z"
  }
]
```

### Delete Session

**Endpoint**: `DELETE /chat/sessions/{session_id}`

**Response**: `204 No Content`

---

## 5. Admin API (Self-Hosted)

### Health Check

**Endpoint**: `GET /health`

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "celery": "healthy",
    "redis": "healthy",
    "embedding_service": "healthy"
  },
  "timestamp": "2025-11-14T10:40:00Z"
}
```

### Stats

**Endpoint**: `GET /stats`

**Response**: `200 OK`
```json
{
  "total_users": 150,
  "total_collections": 450,
  "total_documents": 12500,
  "total_chunks": 250000,
  "total_entities": 15000,
  "total_relationships": 8000,
  "storage_used_bytes": 5368709120,
  "api_calls_today": 5420
}
```

---

## Error Responses

All errors follow this schema:

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "collection_not_found",
    "message": "Collection with ID 'col_abc123' not found",
    "details": {
      "collection_id": "col_abc123"
    }
  }
}
```

### Error Types

1. `invalid_request_error` - Malformed request (400)
2. `authentication_error` - Invalid API key (401)
3. `permission_error` - Insufficient permissions (403)
4. `not_found_error` - Resource not found (404)
5. `rate_limit_error` - Rate limit exceeded (429)
6. `server_error` - Internal server error (500)

### Common Error Codes

- `invalid_api_key` - API key is invalid or expired
- `missing_required_field` - Required field not provided
- `invalid_field_value` - Field value doesn't meet validation rules
- `collection_not_found` - Collection doesn't exist
- `document_not_found` - Document doesn't exist
- `duplicate_document` - Document with same content hash exists
- `file_too_large` - File exceeds size limit
- `unsupported_file_type` - File type not supported
- `processing_failed` - Document processing failed
- `rate_limit_exceeded` - Too many requests

---

## Database Schema

### Tables

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### api_keys
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    scopes TEXT[],
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
```

#### collections
```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, name)
);

CREATE INDEX idx_collections_user ON collections(user_id);
CREATE INDEX idx_collections_metadata ON collections USING GIN(metadata);
```

#### documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    title VARCHAR(512),
    filename VARCHAR(512),
    content_type VARCHAR(255),
    size_bytes BIGINT,

    content_hash VARCHAR(64) UNIQUE NOT NULL,
    unique_identifier_hash VARCHAR(64) UNIQUE,

    status VARCHAR(50) DEFAULT 'processing',
    metadata JSONB DEFAULT '{}',
    processing_info JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_documents_collection ON documents(collection_id);
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);
```

#### chunks
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,

    embedding VECTOR(1536),

    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_user ON chunks(user_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_fts ON chunks USING GIN(to_tsvector('english', content));
CREATE INDEX idx_chunks_metadata ON chunks USING GIN(metadata);
```

#### entities (LightRAG)
```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,

    name VARCHAR(512) NOT NULL,
    type VARCHAR(255),
    description TEXT,

    embedding VECTOR(1536),

    chunk_references UUID[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(collection_id, name)
);

CREATE INDEX idx_entities_collection ON entities(collection_id);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_embedding ON entities USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
```

#### relationships (LightRAG)
```sql
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,

    source_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,

    type VARCHAR(255) NOT NULL,
    description TEXT,

    chunk_reference UUID REFERENCES chunks(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(source_entity_id, target_entity_id, type)
);

CREATE INDEX idx_relationships_collection ON relationships(collection_id);
CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(type);
```

#### task_logs (from SurfSense pattern)
```sql
CREATE TABLE task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,

    task_name VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,

    message TEXT,
    error_details TEXT,
    metadata JSONB DEFAULT '{}',

    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_task_logs_collection ON task_logs(collection_id);
CREATE INDEX idx_task_logs_status ON task_logs(status);
CREATE INDEX idx_task_logs_started ON task_logs(started_at DESC);
```

---

## SDK Design

### Python SDK

**Installation**:
```bash
pip install mnemosyne-ai
```

**Usage**:
```python
from mnemosyne import Mnemosyne

# Initialize client
client = Mnemosyne(api_key="mn_live_...")

# Create collection
collection = client.collections.create(
    name="company-docs",
    description="Internal documentation"
)

# Upload document
document = client.documents.create(
    collection_id=collection.id,
    file=open("guide.pdf", "rb")
)

# Wait for processing
client.documents.wait_until_ready(document.id, timeout=300)

# Retrieve relevant chunks
results = client.retrievals.retrieve(
    collection_id=collection.id,
    query="How do I deploy?",
    mode="hybrid",
    top_k=10,
    rerank=True
)

for result in results:
    print(f"Score: {result.score}")
    print(f"Content: {result.content}\n")

# Chat completion
response = client.chat.completions.create(
    collection_id=collection.id,
    messages=[
        {"role": "user", "content": "How do I deploy the application?"}
    ],
    model="gpt-4o-mini",
    stream=False
)

print(response.choices[0].message.content)

# Streaming chat
stream = client.chat.completions.create(
    collection_id=collection.id,
    messages=[
        {"role": "user", "content": "Explain the architecture"}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

**SDK Structure**:
```
mnemosyne/
├── __init__.py
├── client.py               # Main Mnemosyne class
├── resources/
│   ├── __init__.py
│   ├── collections.py      # CollectionsResource
│   ├── documents.py        # DocumentsResource
│   ├── retrievals.py       # RetrievalsResource
│   └── chat.py             # ChatResource
├── models/
│   ├── __init__.py
│   ├── collection.py       # Collection model
│   ├── document.py         # Document model
│   ├── chunk.py            # Chunk model
│   └── chat.py             # Chat models
├── errors.py               # Error classes
└── utils.py                # Utilities
```

**Key Classes**:
```python
class Mnemosyne:
    def __init__(self, api_key: str, base_url: str = None):
        self.collections = CollectionsResource(self)
        self.documents = DocumentsResource(self)
        self.retrievals = RetrievalsResource(self)
        self.chat = ChatResource(self)

class CollectionsResource:
    def create(self, **kwargs) -> Collection
    def list(self, **kwargs) -> List[Collection]
    def get(self, collection_id: str) -> Collection
    def update(self, collection_id: str, **kwargs) -> Collection
    def delete(self, collection_id: str) -> None

class DocumentsResource:
    def create(self, collection_id: str, **kwargs) -> Document
    def create_from_url(self, collection_id: str, url: str, **kwargs) -> Document
    def create_from_text(self, collection_id: str, content: str, **kwargs) -> Document
    def list(self, collection_id: str, **kwargs) -> List[Document]
    def get(self, document_id: str) -> Document
    def wait_until_ready(self, document_id: str, timeout: int = 300) -> Document
    def delete(self, document_id: str) -> None

class RetrievalsResource:
    def retrieve(self, collection_id: str, query: str, **kwargs) -> List[Chunk]
    def graph_query(self, collection_id: str, query: str, **kwargs) -> GraphQueryResult

class ChatResource:
    def completions(self) -> ChatCompletionsResource

class ChatCompletionsResource:
    def create(self, collection_id: str, messages: List[dict], **kwargs) -> ChatCompletion | Stream[ChatCompletionChunk]
```

### TypeScript SDK

**Installation**:
```bash
npm install @mnemosyne-ai/sdk
```

**Usage**:
```typescript
import { Mnemosyne } from '@mnemosyne-ai/sdk';

// Initialize client
const client = new Mnemosyne({ apiKey: 'mn_live_...' });

// Create collection
const collection = await client.collections.create({
  name: 'company-docs',
  description: 'Internal documentation',
});

// Upload document
const document = await client.documents.create({
  collectionId: collection.id,
  file: fs.createReadStream('guide.pdf'),
});

// Wait for processing
await client.documents.waitUntilReady(document.id, { timeout: 300000 });

// Retrieve relevant chunks
const results = await client.retrievals.retrieve({
  collectionId: collection.id,
  query: 'How do I deploy?',
  mode: 'hybrid',
  topK: 10,
  rerank: true,
});

for (const result of results) {
  console.log(`Score: ${result.score}`);
  console.log(`Content: ${result.content}\n`);
}

// Chat completion
const response = await client.chat.completions.create({
  collectionId: collection.id,
  messages: [
    { role: 'user', content: 'How do I deploy the application?' }
  ],
  model: 'gpt-4o-mini',
  stream: false,
});

console.log(response.choices[0].message.content);

// Streaming chat
const stream = await client.chat.completions.create({
  collectionId: collection.id,
  messages: [
    { role: 'user', content: 'Explain the architecture' }
  ],
  stream: true,
});

for await (const chunk of stream) {
  if (chunk.choices[0]?.delta?.content) {
    process.stdout.write(chunk.choices[0].delta.content);
  }
}
```

**SDK Structure**:
```
src/
├── index.ts
├── client.ts               # Main Mnemosyne class
├── resources/
│   ├── index.ts
│   ├── collections.ts      # CollectionsResource
│   ├── documents.ts        # DocumentsResource
│   ├── retrievals.ts       # RetrievalsResource
│   └── chat.ts             # ChatResource
├── models/
│   ├── index.ts
│   ├── collection.ts       # Collection interfaces
│   ├── document.ts         # Document interfaces
│   ├── chunk.ts            # Chunk interfaces
│   └── chat.ts             # Chat interfaces
├── errors.ts               # Error classes
└── utils.ts                # Utilities
```

---

## Rate Limiting

### Tiers

**Free Tier**:
- 100 requests/day
- 10 documents/collection
- 5 collections max
- 10 MB file size limit

**Developer Tier** ($29/month):
- 10,000 requests/day
- 1,000 documents/collection
- 50 collections max
- 100 MB file size limit

**Professional Tier** ($99/month):
- 100,000 requests/day
- Unlimited documents
- Unlimited collections
- 500 MB file size limit

**Enterprise** (custom):
- Custom limits
- Self-hosted option
- SLA guarantees

### Headers

```http
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9543
X-RateLimit-Reset: 1700000000
```

---

## Webhooks (Future)

### Events

- `collection.created`
- `collection.updated`
- `collection.deleted`
- `document.processing_started`
- `document.processing_completed`
- `document.processing_failed`
- `document.deleted`

### Webhook Payload

```json
{
  "id": "evt_abc123",
  "type": "document.processing_completed",
  "created": 1700000000,
  "data": {
    "object": {
      "id": "doc_xyz789",
      "collection_id": "col_abc123",
      "status": "completed",
      "chunk_count": 25
    }
  }
}
```

---

## Key Design Decisions

### 1. Content Hashing (from SurfSense)

**Deduplication**: SHA-256 hash of content to prevent duplicate storage
```python
content_hash = hashlib.sha256(content.encode()).hexdigest()
```

**Update Detection**: Separate `unique_identifier_hash` for source tracking
```python
unique_identifier_hash = hashlib.sha256(url.encode()).hexdigest()
```

### 2. Cascade Deletes (from SurfSense)

Automatic cleanup when parent resources are deleted:
- Delete collection → delete all documents + chunks + entities + relationships
- Delete document → delete all chunks
- Delete user → delete all collections + documents + chunks

### 3. Hybrid Search (from SurfSense)

**Reciprocal Rank Fusion** for combining vector + full-text search:
```python
k = 60
for rank, chunk in enumerate(vector_results, start=1):
    rrf_scores[chunk.id] = 1 / (k + rank)
for rank, chunk in enumerate(fts_results, start=1):
    rrf_scores[chunk.id] += 1 / (k + rank)
```

### 4. Async Processing (from SurfSense)

**Celery** for background document processing:
- New event loop per task
- NullPool for database connections
- Task logging for visibility
- Retry logic with exponential backoff

### 5. LightRAG Integration

**Knowledge Graph** for efficient retrieval:
- Extract entities and relationships during ingestion
- Local retrieval (entity-focused)
- Global retrieval (community-based)
- 99% token reduction vs GraphRAG

### 6. API-First Philosophy (from Ragie.ai)

- Everything accessible via REST API
- Clean, intuitive endpoint design
- Comprehensive SDKs (Python + TypeScript)
- Developer-first experience

### 7. Multi-Tenancy

**User → Collection → Document** hierarchy:
- Ownership checks on all operations
- Scoped API keys
- Metadata filtering per user

---

## Next Steps

1. **Week 1**: Database setup + basic CRUD
   - PostgreSQL + pgvector setup
   - User + API key models
   - Collection + Document models
   - Basic endpoints (no processing)

2. **Week 2**: Document processing pipeline
   - Celery integration
   - Docling service integration
   - Chunking (Chonkie)
   - Embedding generation
   - Content hashing + deduplication

3. **Week 3**: Retrieval system
   - Vector search
   - Full-text search
   - Hybrid search with RRF
   - Reranking integration

4. **Week 4**: LightRAG integration
   - Entity extraction
   - Relationship extraction
   - Knowledge graph storage
   - Graph-based retrieval

5. **Week 5-6**: Chat API
   - LLM integration (LiteLLM)
   - Context injection
   - Streaming responses
   - Multi-turn conversation

6. **Week 7**: Python SDK
   - Resource classes
   - Models
   - Error handling
   - Testing

7. **Week 8**: TypeScript SDK
   - Resource classes
   - Type definitions
   - Error handling
   - Testing

---

## Appendix: Comparison with Ragie.ai

| Feature | Ragie.ai | Mnemosyne |
|---------|----------|-----------|
| **Open Source** | No | Yes |
| **Self-Hostable** | No | Yes |
| **File Formats** | 50+ | 50+ (via Docling) |
| **Integrations** | 15+ | Planned |
| **Knowledge Graph** | No | Yes (LightRAG) |
| **Hybrid Search** | Yes | Yes (RRF) |
| **Reranking** | Yes | Yes |
| **Chat API** | Yes | Yes |
| **Python SDK** | Yes | Yes |
| **TypeScript SDK** | Yes | Yes |
| **Webhooks** | Yes | Planned |
| **Pricing** | $0.40/1k chunks | Free (self-hosted) |

---

**End of API Design Specification**
