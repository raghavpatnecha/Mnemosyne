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
  "filters": {
    "metadata.category": "technical",
    "metadata.author": "John Doe"
  },
  "rerank": true,
  "rerank_model": "jina-reranker-v1",
  "include_metadata": true
}
```

**Parameters**:
- `mode` (string): "vector" (semantic only), "keyword" (full-text only), "hybrid" (RRF fusion)
- `top_k` (int, default: 10, max: 100): Number of results to return
- `rerank` (boolean, default: false): Apply reranking to results
- `filters` (object): Metadata filters using dot notation
- `include_metadata` (boolean, default: true): Include document metadata

**Response**: `200 OK`
```json
{
  "query": "How do I deploy the application?",
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
  ],
  "retrieval_metadata": {
    "mode": "hybrid",
    "rerank_applied": true,
    "total_candidates": 50,
    "final_count": 10,
    "retrieval_time_ms": 45
  }
}
```

### Knowledge Graph Query

Query the knowledge graph for entity-relationship based retrieval.

**Endpoint**: `POST /retrievals/graph`

**Request Body**:
```json
{
  "collection_id": "col_abc123",
  "query": "What are the relationships between Docker and Kubernetes?",
  "mode": "local",
  "top_k": 10
}
```

**Parameters**:
- `mode` (string): "local" (entity-focused), "global" (community-based), "hybrid" (both)

**Response**: `200 OK`
```json
{
  "query": "What are the relationships between Docker and Kubernetes?",
  "entities": [
    {
      "name": "Docker",
      "type": "technology",
      "description": "Container platform",
      "chunk_references": ["chunk_aaa111", "chunk_bbb222"]
    },
    {
      "name": "Kubernetes",
      "type": "technology",
      "description": "Container orchestration platform",
      "chunk_references": ["chunk_ccc333", "chunk_ddd444"]
    }
  ],
  "relationships": [
    {
      "source": "Docker",
      "target": "Kubernetes",
      "type": "ORCHESTRATED_BY",
      "description": "Docker containers are orchestrated by Kubernetes",
      "chunk_reference": "chunk_aaa111"
    }
  ],
  "chunks": [
    {
      "chunk_id": "chunk_aaa111",
      "content": "Kubernetes orchestrates Docker containers...",
      "score": 0.95
    }
  ],
  "retrieval_metadata": {
    "mode": "local",
    "entities_found": 2,
    "relationships_found": 1,
    "retrieval_time_ms": 78
  }
}
```

---

## 4. Chat API

### Chat Completion

Generate a chat completion using retrieved context.

**Endpoint**: `POST /chat/completions`

**Request Body**:
```json
{
  "collection_id": "col_abc123",
  "messages": [
    {
      "role": "user",
      "content": "How do I deploy the application?"
    }
  ],
  "model": "gpt-4o-mini",
  "retrieval_config": {
    "mode": "hybrid",
    "top_k": 10,
    "rerank": true
  },
  "generation_config": {
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": false
  }
}
```

**Response (Non-Streaming)**: `200 OK`
```json
{
  "id": "chat_comp_xxx",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "To deploy the application, follow these steps:\n\n1. Build the Docker image using `docker build -t app:latest .`\n2. Push to registry...",
        "context_used": [
          {
            "chunk_id": "chunk_aaa111",
            "document_id": "doc_xyz789",
            "score": 0.92
          }
        ]
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 180,
    "total_tokens": 1430
  },
  "retrieval_metadata": {
    "mode": "hybrid",
    "chunks_retrieved": 10,
    "chunks_used": 3,
    "retrieval_time_ms": 45
  }
}
```

**Response (Streaming)**: `200 OK` with `Content-Type: text/event-stream`

```
data: {"id":"chat_comp_xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":"To"}}]}

data: {"id":"chat_comp_xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" deploy"}}]}

data: {"id":"chat_comp_xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" the"}}]}

...

data: [DONE]
```

### Multi-Turn Chat

**Endpoint**: `POST /chat/completions` (same endpoint, multiple messages)

**Request Body**:
```json
{
  "collection_id": "col_abc123",
  "messages": [
    {
      "role": "user",
      "content": "How do I deploy the application?"
    },
    {
      "role": "assistant",
      "content": "To deploy the application, follow these steps..."
    },
    {
      "role": "user",
      "content": "What about database migrations?"
    }
  ],
  "model": "gpt-4o-mini",
  "retrieval_config": {
    "mode": "hybrid",
    "top_k": 10
  }
}
```

**Note**: Mnemosyne performs retrieval on each user message, combining context from all turns.

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
