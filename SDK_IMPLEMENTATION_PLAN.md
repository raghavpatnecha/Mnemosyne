# Mnemosyne Python SDK - Implementation Plan

**Date:** November 17, 2025
**Status:** Planning Phase
**Goal:** Create a production-ready Python SDK for Mnemosyne API

---

## 1. Overview

### Purpose
Provide developers with an easy-to-use Python SDK for interacting with the Mnemosyne RAG API, following modern SDK patterns used by OpenAI, Anthropic, and Stripe.

### Key Features

**Full Document Lifecycle:**
- **Collection management**: Create, list, update, delete collections
- **Document ingestion**: Upload PDFs, DOCX, YouTube videos, MP4s
- **Batch upload**: Efficiently upload multiple documents
- **Processing monitoring**: Real-time status tracking with chunk/token counts
- **Metadata management**: Rich metadata for organization and filtering

**Advanced Retrieval:**
- **5 search modes**: Semantic, keyword, hybrid, hierarchical, graph (LightRAG)
- **Metadata filtering**: Search within specific document types/categories
- **Conversational chat**: RAG-powered chat with SSE streaming

**Developer Experience:**
- **Dual client architecture**: Sync (`Client`) and async (`AsyncClient`)
- **Resource-based organization**: `client.collections.create()`, `client.documents.list()`, etc.
- **Full type hints**: Complete type safety with Pydantic models
- **Error handling**: Custom exceptions with helpful error messages
- **Automatic retries**: Configurable retry logic for network failures
- **LangChain integration**: First-class support via custom retriever

---

## 2. Full Workflow: Ingestion → Retrieval

### Quick Example: End-to-End Usage

```python
from mnemosyne import Client

client = Client(api_key="mn_your_api_key")

# ============================================================================
# INGESTION: Build your knowledge base
# ============================================================================

# 1. Create collection
collection = client.collections.create(
    name="AI Research",
    metadata={"domain": "machine_learning"}
)

# 2. Upload documents (PDFs, DOCX, YouTube, MP4)
doc = client.documents.create(
    collection_id=collection.id,
    file="research_paper.pdf",
    metadata={"year": 2024, "authors": ["Smith et al."]}
)

# 3. Monitor processing
import time
while client.documents.get_status(doc.id).status != "completed":
    time.sleep(2)

print(f"✓ Document processed: {doc.title}")

# ============================================================================
# RETRIEVAL: Search your knowledge base
# ============================================================================

# 4. Semantic search
results = client.retrievals.search(
    query="What is the transformer architecture?",
    mode="hybrid",  # semantic + keyword
    top_k=5,
    collection_id=collection.id
)

for chunk in results.results:
    print(f"[{chunk.score:.3f}] {chunk.content[:200]}...")

# 5. Conversational chat (requires async)
# See async examples for streaming chat

client.close()
```

### Supported Content Types

| Type | Extension | Ingestion Method | Processing |
|------|-----------|------------------|------------|
| **PDF** | `.pdf` | File upload | Text extraction + chunking |
| **Word** | `.docx` | File upload | Text extraction + chunking |
| **YouTube** | URL | YouTube URL | Transcription + chunking |
| **Video** | `.mp4` | File upload | Transcription + chunking |
| **Text** | `.txt`, `.md` | File upload | Direct chunking |

---

## 3. Current API Analysis

### Implemented Endpoints (17 total)

#### Authentication (1 endpoint)
```
POST /auth/register
  - Request: email, password
  - Response: user_id, email, api_key
  - Purpose: Register user and get API key
```

#### Collections (5 endpoints)
```
POST /collections
  - Request: name, description?, metadata?, config?
  - Response: CollectionResponse
  - Purpose: Create collection

GET /collections
  - Query: limit?, offset?
  - Response: CollectionListResponse (paginated)
  - Purpose: List all collections

GET /collections/{id}
  - Response: CollectionResponse
  - Purpose: Get single collection

PATCH /collections/{id}
  - Request: name?, description?, metadata?, config?
  - Response: CollectionResponse
  - Purpose: Update collection metadata

DELETE /collections/{id}
  - Response: 204 No Content
  - Purpose: Delete collection (cascade deletes documents)
```

#### Documents (6 endpoints)
```
POST /documents
  - Request: file (multipart), collection_id, metadata?
  - Response: DocumentResponse (status=202)
  - Purpose: Upload document for async processing

GET /documents
  - Query: collection_id, limit?, offset?, status_filter?
  - Response: DocumentListResponse (paginated)
  - Purpose: List documents in collection

GET /documents/{id}
  - Response: DocumentResponse
  - Purpose: Get single document

PATCH /documents/{id}
  - Request: title?, metadata?
  - Response: DocumentResponse
  - Purpose: Update document metadata

GET /documents/{id}/status
  - Response: DocumentStatusResponse
  - Purpose: Get processing status and details

DELETE /documents/{id}
  - Response: 204 No Content
  - Purpose: Delete document and file
```

#### Retrievals (1 endpoint)
```
POST /retrievals
  - Request: query, mode, top_k?, collection_id?, metadata_filter?
  - Response: RetrievalResponse
  - Purpose: Search with 5 modes (semantic, keyword, hybrid, hierarchical, graph)
  - Modes:
    - semantic: Vector similarity only
    - keyword: Full-text search only
    - hybrid: Vector + FTS with RRF
    - hierarchical: Document → chunk two-tier
    - graph: LightRAG entity + relationship
```

#### Chat (4 endpoints)
```
POST /chat
  - Request: message, session_id?, collection_id?, top_k?, stream?
  - Response: StreamingResponse (SSE)
  - Purpose: Conversational RAG with streaming
  - SSE Events: delta, sources, done, error

GET /chat/sessions
  - Query: limit?, offset?
  - Response: List[ChatSessionResponse]
  - Purpose: List chat sessions

GET /chat/sessions/{id}/messages
  - Response: List[ChatMessageResponse]
  - Purpose: Get all messages in session

DELETE /chat/sessions/{id}
  - Response: 204 No Content
  - Purpose: Delete session and messages
```

### Authentication
- **Method**: Bearer token (API key)
- **Header**: `Authorization: Bearer mn_...`
- **Key format**: Generated on registration, shown once

---

## 3. SDK Architecture

### Design Pattern: Resource-Based Organization (OpenAI/Anthropic Style)

```
mnemosyne-sdk/
├── mnemosyne/
│   ├── __init__.py           # Exports Client, AsyncClient
│   ├── client.py             # Sync client
│   ├── async_client.py       # Async client
│   ├── base_client.py        # Shared HTTP logic
│   ├── resources/            # Resource endpoints
│   │   ├── __init__.py
│   │   ├── collections.py    # CollectionsResource
│   │   ├── documents.py      # DocumentsResource
│   │   ├── retrievals.py     # RetrievalsResource
│   │   └── chat.py           # ChatResource
│   ├── types/                # Pydantic models
│   │   ├── __init__.py
│   │   ├── collections.py    # Collection schemas
│   │   ├── documents.py      # Document schemas
│   │   ├── retrievals.py     # Retrieval schemas
│   │   └── chat.py           # Chat schemas
│   ├── exceptions.py         # Custom exceptions
│   ├── streaming.py          # SSE streaming utilities
│   └── version.py            # Version string
├── examples/
│   ├── ingestion_workflow.py     # Document ingestion (CORE)
│   ├── basic_usage.py            # Retrieval and search
│   ├── video_ingestion.py        # YouTube + MP4 videos
│   ├── async_example.py          # Async client example
│   ├── streaming_chat.py         # SSE streaming example
│   └── langchain_integration.py  # LangChain retriever
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml            # Poetry config
├── README.md                 # Installation and usage
└── LICENSE                   # MIT License
```

---

## 4. Core Client Design

### Base Client (shared logic)
```python
# mnemosyne/base_client.py
import httpx
from typing import Optional, Dict, Any
from .exceptions import MnemosyneError, AuthenticationError, RateLimitError

class BaseClient:
    """Shared HTTP logic for sync and async clients"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"mnemosyne-python/{VERSION}"
        }

    def _handle_error(self, response: httpx.Response):
        """Convert HTTP errors to custom exceptions"""
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code >= 400:
            raise MnemosyneError(f"API error: {response.text}")
```

### Sync Client
```python
# mnemosyne/client.py
import httpx
from .resources.collections import CollectionsResource
from .resources.documents import DocumentsResource
from .resources.retrievals import RetrievalsResource
from .resources.chat import ChatResource

class Client(BaseClient):
    """Synchronous Mnemosyne API client"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self._http_client = httpx.Client(
            base_url=self.base_url,
            headers=self._build_headers(),
            timeout=self.timeout
        )

        # Resource endpoints
        self.collections = CollectionsResource(self)
        self.documents = DocumentsResource(self)
        self.retrievals = RetrievalsResource(self)
        self.chat = ChatResource(self)

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic"""
        response = self._http_client.request(method, path, **kwargs)
        self._handle_error(response)
        return response

    def close(self):
        self._http_client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
```

### Async Client
```python
# mnemosyne/async_client.py
import httpx
from .resources.collections import AsyncCollectionsResource
from .resources.documents import AsyncDocumentsResource
from .resources.retrievals import AsyncRetrievalsResource
from .resources.chat import AsyncChatResource

class AsyncClient(BaseClient):
    """Asynchronous Mnemosyne API client"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._build_headers(),
            timeout=self.timeout
        )

        # Resource endpoints
        self.collections = AsyncCollectionsResource(self)
        self.documents = AsyncDocumentsResource(self)
        self.retrievals = AsyncRetrievalsResource(self)
        self.chat = AsyncChatResource(self)

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make async HTTP request with retry logic"""
        response = await self._http_client.request(method, path, **kwargs)
        self._handle_error(response)
        return response

    async def close(self):
        await self._http_client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
```

---

## 5. Resource Implementations

### Collections Resource (example)
```python
# mnemosyne/resources/collections.py
from typing import Optional, Dict, List
from uuid import UUID
from ..types.collections import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse
)

class CollectionsResource:
    """Sync collections operations"""

    def __init__(self, client):
        self._client = client

    def create(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        config: Optional[Dict] = None
    ) -> CollectionResponse:
        """Create a new collection"""
        data = CollectionCreate(
            name=name,
            description=description,
            metadata=metadata,
            config=config
        )
        response = self._client.request("POST", "/collections", json=data.dict())
        return CollectionResponse(**response.json())

    def list(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> CollectionListResponse:
        """List all collections"""
        params = {"limit": limit, "offset": offset}
        response = self._client.request("GET", "/collections", params=params)
        return CollectionListResponse(**response.json())

    def get(self, collection_id: UUID) -> CollectionResponse:
        """Get collection by ID"""
        response = self._client.request("GET", f"/collections/{collection_id}")
        return CollectionResponse(**response.json())

    def update(
        self,
        collection_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        config: Optional[Dict] = None
    ) -> CollectionResponse:
        """Update collection metadata"""
        data = CollectionUpdate(
            name=name,
            description=description,
            metadata=metadata,
            config=config
        ).dict(exclude_unset=True)
        response = self._client.request("PATCH", f"/collections/{collection_id}", json=data)
        return CollectionResponse(**response.json())

    def delete(self, collection_id: UUID) -> None:
        """Delete collection"""
        self._client.request("DELETE", f"/collections/{collection_id}")


class AsyncCollectionsResource:
    """Async collections operations"""

    def __init__(self, client):
        self._client = client

    async def create(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        config: Optional[Dict] = None
    ) -> CollectionResponse:
        """Create a new collection"""
        data = CollectionCreate(
            name=name,
            description=description,
            metadata=metadata,
            config=config
        )
        response = await self._client.request("POST", "/collections", json=data.dict())
        return CollectionResponse(**response.json())

    # ... (same methods but async)
```

### Documents Resource (key feature: file upload)
```python
# mnemosyne/resources/documents.py
from pathlib import Path
from typing import Optional, Dict, Union, BinaryIO
from uuid import UUID
from ..types.documents import DocumentResponse, DocumentListResponse, DocumentStatusResponse

class DocumentsResource:
    """Sync document operations"""

    def __init__(self, client):
        self._client = client

    def create(
        self,
        collection_id: UUID,
        file: Union[str, Path, BinaryIO],
        metadata: Optional[Dict] = None
    ) -> DocumentResponse:
        """Upload a document"""
        # Handle file input
        if isinstance(file, (str, Path)):
            file_obj = open(file, "rb")
            filename = Path(file).name
            close_file = True
        else:
            file_obj = file
            filename = getattr(file, "name", "file")
            close_file = False

        try:
            files = {"file": (filename, file_obj)}
            data = {
                "collection_id": str(collection_id),
                "metadata": json.dumps(metadata or {})
            }

            # Use multipart/form-data
            response = self._client._http_client.post(
                "/documents",
                files=files,
                data=data
            )
            self._client._handle_error(response)
            return DocumentResponse(**response.json())
        finally:
            if close_file:
                file_obj.close()

    def list(
        self,
        collection_id: UUID,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> DocumentListResponse:
        """List documents in collection"""
        params = {
            "collection_id": str(collection_id),
            "limit": limit,
            "offset": offset
        }
        if status_filter:
            params["status_filter"] = status_filter

        response = self._client.request("GET", "/documents", params=params)
        return DocumentListResponse(**response.json())

    def get_status(self, document_id: UUID) -> DocumentStatusResponse:
        """Get document processing status"""
        response = self._client.request("GET", f"/documents/{document_id}/status")
        return DocumentStatusResponse(**response.json())

    # ... (other CRUD methods)
```

### Retrievals Resource (supports 5 modes)
```python
# mnemosyne/resources/retrievals.py
from typing import Optional, Dict, Literal
from uuid import UUID
from ..types.retrievals import RetrievalRequest, RetrievalResponse

RetrievalMode = Literal["semantic", "keyword", "hybrid", "hierarchical", "graph"]

class RetrievalsResource:
    """Sync retrieval operations"""

    def __init__(self, client):
        self._client = client

    def search(
        self,
        query: str,
        mode: RetrievalMode = "hybrid",
        top_k: int = 10,
        collection_id: Optional[UUID] = None,
        metadata_filter: Optional[Dict] = None
    ) -> RetrievalResponse:
        """Search for relevant chunks"""
        data = RetrievalRequest(
            query=query,
            mode=mode,
            top_k=top_k,
            collection_id=collection_id,
            metadata_filter=metadata_filter
        )
        response = self._client.request("POST", "/retrievals", json=data.dict())
        return RetrievalResponse(**response.json())
```

### Chat Resource (SSE streaming support)
```python
# mnemosyne/resources/chat.py
from typing import Optional, AsyncIterator, Dict
from uuid import UUID
from ..types.chat import ChatRequest, ChatSessionResponse, ChatMessageResponse
from ..streaming import parse_sse_stream

class ChatResource:
    """Sync chat operations (limited - use AsyncChatResource for streaming)"""

    def __init__(self, client):
        self._client = client

    def list_sessions(self, limit: int = 20, offset: int = 0):
        """List chat sessions"""
        params = {"limit": limit, "offset": offset}
        response = self._client.request("GET", "/chat/sessions", params=params)
        return [ChatSessionResponse(**s) for s in response.json()]

    # ... other methods


class AsyncChatResource:
    """Async chat operations with streaming support"""

    def __init__(self, client):
        self._client = client

    async def chat(
        self,
        message: str,
        session_id: Optional[UUID] = None,
        collection_id: Optional[UUID] = None,
        top_k: int = 5
    ) -> AsyncIterator[Dict]:
        """Chat with streaming SSE response"""
        data = ChatRequest(
            message=message,
            session_id=session_id,
            collection_id=collection_id,
            top_k=top_k,
            stream=True
        )

        async with self._client._http_client.stream(
            "POST",
            "/chat",
            json=data.dict()
        ) as response:
            self._client._handle_error(response)
            async for event in parse_sse_stream(response):
                yield event

    async def list_sessions(self, limit: int = 20, offset: int = 0):
        """List chat sessions"""
        params = {"limit": limit, "offset": offset}
        response = await self._client.request("GET", "/chat/sessions", params=params)
        return [ChatSessionResponse(**s) for s in response.json()]
```

---

## 6. Type System (Pydantic Models)

All request/response schemas will mirror the backend schemas:

```python
# mnemosyne/types/collections.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from uuid import UUID

class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict] = None
    config: Optional[Dict] = None

class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict] = None
    config: Optional[Dict] = None

class CollectionResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    metadata: Dict
    config: Dict
    document_count: int
    created_at: datetime
    updated_at: Optional[datetime]

class CollectionListResponse(BaseModel):
    data: List[CollectionResponse]
    pagination: Dict
```

---

## 7. Streaming Support (SSE)

```python
# mnemosyne/streaming.py
import json
from typing import AsyncIterator, Dict
import httpx

async def parse_sse_stream(response: httpx.Response) -> AsyncIterator[Dict]:
    """Parse Server-Sent Events stream"""
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            data = line[6:]  # Remove "data: " prefix
            try:
                event = json.loads(data)
                yield event
            except json.JSONDecodeError:
                continue
```

---

## 8. Error Handling

```python
# mnemosyne/exceptions.py

class MnemosyneError(Exception):
    """Base exception for all Mnemosyne errors"""
    pass

class AuthenticationError(MnemosyneError):
    """Invalid API key or authentication failure"""
    pass

class RateLimitError(MnemosyneError):
    """Rate limit exceeded"""
    pass

class NotFoundError(MnemosyneError):
    """Resource not found"""
    pass

class ValidationError(MnemosyneError):
    """Invalid request parameters"""
    pass

class APIError(MnemosyneError):
    """Generic API error"""
    def __init__(self, message: str, status_code: int, response_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
```

---

## 9. Examples

### Example 1: Document Ingestion Workflow (Full Lifecycle)

```python
# examples/ingestion_workflow.py
"""
Complete document ingestion workflow
Demonstrates: collection creation, batch upload, processing monitoring, metadata management
"""

from mnemosyne import Client
from pathlib import Path
import time

# Initialize client
client = Client(api_key="mn_your_api_key_here")

print("=" * 60)
print("MNEMOSYNE DOCUMENT INGESTION WORKFLOW")
print("=" * 60)

# ============================================================================
# STEP 1: Create a Collection (organize your knowledge base)
# ============================================================================
print("\n[1/5] Creating collection...")
collection = client.collections.create(
    name="AI Research Papers 2024",
    description="Latest papers on LLMs, RAG, and transformers",
    metadata={
        "domain": "machine_learning",
        "year": 2024,
        "tags": ["llm", "rag", "transformers"]
    },
    config={
        "embedding_model": "text-embedding-3-small",
        "chunk_size": 512,
        "chunk_overlap": 128
    }
)
print(f"✓ Collection created: {collection.name}")
print(f"  ID: {collection.id}")
print(f"  Metadata: {collection.metadata}")

# ============================================================================
# STEP 2: Batch Upload Documents (multiple file types)
# ============================================================================
print("\n[2/5] Uploading documents...")

# Define documents to upload
documents_to_upload = [
    {
        "file": "papers/attention_is_all_you_need.pdf",
        "metadata": {
            "title": "Attention Is All You Need",
            "year": 2017,
            "authors": ["Vaswani et al."],
            "venue": "NeurIPS",
            "type": "research_paper"
        }
    },
    {
        "file": "papers/rag_paper.pdf",
        "metadata": {
            "title": "Retrieval-Augmented Generation",
            "year": 2020,
            "authors": ["Lewis et al."],
            "venue": "NeurIPS",
            "type": "research_paper"
        }
    },
    {
        "file": "reports/quarterly_analysis.docx",
        "metadata": {
            "title": "Q4 2024 AI Analysis",
            "department": "Research",
            "type": "internal_report"
        }
    }
]

# Upload all documents
uploaded_docs = []
for i, doc_info in enumerate(documents_to_upload, 1):
    print(f"\n  Uploading {i}/{len(documents_to_upload)}: {doc_info['file']}")

    doc = client.documents.create(
        collection_id=collection.id,
        file=doc_info["file"],
        metadata=doc_info["metadata"]
    )

    uploaded_docs.append(doc)
    print(f"  ✓ Uploaded: {doc.title}")
    print(f"    Document ID: {doc.id}")
    print(f"    Size: {doc.size_bytes / 1024:.1f} KB")
    print(f"    Status: {doc.status}")
    print(f"    Content Type: {doc.content_type}")

# ============================================================================
# STEP 3: Monitor Processing Status (wait for completion)
# ============================================================================
print("\n[3/5] Monitoring document processing...")

def wait_for_processing(client, doc_ids, check_interval=3):
    """Poll processing status until all documents are completed"""
    pending = set(doc_ids)

    while pending:
        time.sleep(check_interval)

        for doc_id in list(pending):
            status = client.documents.get_status(doc_id)

            if status.status == "completed":
                print(f"  ✓ {status.document_id}: COMPLETED")
                print(f"    - Chunks: {status.chunk_count}")
                print(f"    - Tokens: {status.total_tokens:,}")
                print(f"    - Processing time: {(status.processed_at - status.created_at).total_seconds():.1f}s")
                pending.remove(doc_id)

            elif status.status == "failed":
                print(f"  ✗ {status.document_id}: FAILED")
                print(f"    Error: {status.error_message}")
                pending.remove(doc_id)

            elif status.status == "processing":
                print(f"  ⏳ {status.document_id}: Processing... ({status.chunk_count} chunks so far)")

    print("\n  All documents processed!")

doc_ids = [doc.id for doc in uploaded_docs]
wait_for_processing(client, doc_ids)

# ============================================================================
# STEP 4: Verify Ingestion (check collection stats)
# ============================================================================
print("\n[4/5] Verifying ingestion...")

# Refresh collection to get updated document count
collection = client.collections.get(collection.id)
print(f"  Collection: {collection.name}")
print(f"  Total documents: {collection.document_count}")

# List all documents in collection
docs_list = client.documents.list(
    collection_id=collection.id,
    status_filter="completed"
)

print(f"\n  Documents ready for retrieval:")
total_chunks = 0
total_tokens = 0

for doc in docs_list.data:
    status = client.documents.get_status(doc.id)
    total_chunks += status.chunk_count
    total_tokens += status.total_tokens

    print(f"    - {doc.title}")
    print(f"      Chunks: {status.chunk_count}, Tokens: {status.total_tokens:,}")

print(f"\n  Totals:")
print(f"    Documents: {len(docs_list.data)}")
print(f"    Chunks: {total_chunks}")
print(f"    Tokens: {total_tokens:,}")

# ============================================================================
# STEP 5: Update Metadata (optional - add tags, update info)
# ============================================================================
print("\n[5/5] Updating metadata...")

# Update collection with processing stats
client.collections.update(
    collection_id=collection.id,
    metadata={
        **collection.metadata,
        "total_chunks": total_chunks,
        "total_tokens": total_tokens,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
    }
)
print("  ✓ Collection metadata updated")

# Update individual document metadata
doc = uploaded_docs[0]
client.documents.update(
    document_id=doc.id,
    metadata={
        **doc.metadata,
        "processed": True,
        "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
)
print("  ✓ Document metadata updated")

# ============================================================================
# SUCCESS! Collection is ready for retrieval
# ============================================================================
print("\n" + "=" * 60)
print("✓ INGESTION COMPLETE - Collection ready for search!")
print("=" * 60)
print(f"\nCollection ID: {collection.id}")
print(f"Documents indexed: {collection.document_count}")
print(f"Total chunks: {total_chunks}")
print("\nYou can now:")
print("  - Search: client.retrievals.search(query='...', collection_id=collection.id)")
print("  - Chat: client.chat.chat(message='...', collection_id=collection.id)")
print("  - Manage: client.documents.list(), update(), delete()")

client.close()
```

### Example 2: Basic Usage (Retrieval & Search)

```python
# examples/basic_usage.py
"""
Basic retrieval and search example
Assumes you've already ingested documents (see ingestion_workflow.py)
"""

from mnemosyne import Client

# Initialize client
client = Client(api_key="mn_your_api_key_here")

# Get existing collection
collections = client.collections.list()
collection = collections.data[0]  # Use first collection

print(f"Searching in collection: {collection.name}")

# ============================================================================
# Search with Different Modes
# ============================================================================

# 1. Semantic Search (vector similarity)
print("\n--- Semantic Search ---")
results = client.retrievals.search(
    query="What is the transformer architecture?",
    mode="semantic",
    top_k=5,
    collection_id=collection.id
)
for i, chunk in enumerate(results.results, 1):
    print(f"{i}. [Score: {chunk.score:.3f}] {chunk.document.title}")
    print(f"   {chunk.content[:150]}...")

# 2. Hybrid Search (vector + keyword with RRF)
print("\n--- Hybrid Search ---")
results = client.retrievals.search(
    query="attention mechanism self-attention",
    mode="hybrid",
    top_k=5,
    collection_id=collection.id
)
print(f"Found {results.total_results} results")

# 3. Hierarchical Search (document-level then chunk-level)
print("\n--- Hierarchical Search ---")
results = client.retrievals.search(
    query="How does RAG work?",
    mode="hierarchical",
    top_k=10
)
for chunk in results.results[:3]:
    print(f"  - {chunk.document.title}: {chunk.content[:100]}...")

# 4. Graph Search (LightRAG - entity + relationship aware)
print("\n--- Graph Search (LightRAG) ---")
results = client.retrievals.search(
    query="Who proposed the transformer model and when?",
    mode="graph",
    top_k=10
)
print(results.results[0].content)

# 5. Metadata Filtering
print("\n--- Filtered Search ---")
results = client.retrievals.search(
    query="machine learning advancements",
    mode="hybrid",
    top_k=5,
    metadata_filter={"year": 2024, "type": "research_paper"}
)
print(f"Found {results.total_results} results from 2024 research papers")

client.close()
```

### Example 3: YouTube & Video Ingestion

```python
# examples/video_ingestion.py
"""
YouTube and MP4 video ingestion example
Demonstrates video processing capabilities
"""

from mnemosyne import Client

client = Client(api_key="mn_your_api_key_here")

# Create collection for video content
collection = client.collections.create(
    name="Video Tutorials",
    description="Educational videos on AI and ML"
)

# ============================================================================
# YouTube Video Ingestion
# ============================================================================
print("Ingesting YouTube video...")

# Option 1: Using YouTube URL directly (if backend supports it)
youtube_doc = client.documents.create(
    collection_id=collection.id,
    file="https://www.youtube.com/watch?v=video_id",  # YouTube URL
    metadata={
        "source": "youtube",
        "title": "Introduction to Transformers",
        "channel": "AI Explained",
        "duration_seconds": 1200
    }
)

# Option 2: Upload downloaded MP4 file
mp4_doc = client.documents.create(
    collection_id=collection.id,
    file="videos/tutorial.mp4",
    metadata={
        "source": "local",
        "title": "RAG Tutorial",
        "speaker": "John Doe"
    }
)

# Wait for video processing (transcription + chunking)
import time
while True:
    status = client.documents.get_status(youtube_doc.id)
    if status.status == "completed":
        print(f"✓ Video processed!")
        print(f"  Transcript chunks: {status.chunk_count}")
        print(f"  Transcript tokens: {status.total_tokens}")
        break
    elif status.status == "failed":
        print(f"✗ Processing failed: {status.error_message}")
        break
    time.sleep(5)

# Search video transcripts
results = client.retrievals.search(
    query="How do transformers work?",
    mode="hybrid",
    collection_id=collection.id
)

for chunk in results.results:
    print(f"Video: {chunk.document.title}")
    print(f"Transcript: {chunk.content}")
    print(f"Metadata: {chunk.metadata}")  # May include timestamp info

client.close()
```

### Example 4: Async Client with Streaming

```python
# examples/async_example.py
"""
Async Mnemosyne SDK example with streaming chat
"""

import asyncio
from mnemosyne import AsyncClient

async def main():
    async with AsyncClient(api_key="mn_your_api_key_here") as client:
        # Create collection
        collection = await client.collections.create(
            name="AI Research",
            description="Collection for AI papers"
        )

        # Upload document
        doc = await client.documents.create(
            collection_id=collection.id,
            file="paper.pdf"
        )

        # Wait for processing
        while True:
            status = await client.documents.get_status(doc.id)
            if status.status == "completed":
                break
            await asyncio.sleep(1)

        # Streaming chat
        print("Chat with your documents:\n")
        async for event in client.chat.chat(
            message="Summarize the key findings in this paper",
            collection_id=collection.id,
            top_k=5
        ):
            if event["type"] == "delta":
                print(event["delta"], end="", flush=True)
            elif event["type"] == "sources":
                print(f"\n\nSources: {len(event['sources'])} chunks")
            elif event["type"] == "done":
                print(f"\n\nSession ID: {event['session_id']}")

asyncio.run(main())
```

### Example 3: LangChain Integration

```python
# examples/langchain_integration.py
"""
Mnemosyne + LangChain integration example
Custom retriever for LangChain's RetrievalQA chain
"""

from typing import List
from langchain.schema import Document
from langchain.retrievers import BaseRetriever
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from mnemosyne import Client
from uuid import UUID

class MnemosyneRetriever(BaseRetriever):
    """Custom LangChain retriever using Mnemosyne SDK"""

    def __init__(
        self,
        api_key: str,
        collection_id: UUID,
        mode: str = "hybrid",
        top_k: int = 5
    ):
        self.client = Client(api_key=api_key)
        self.collection_id = collection_id
        self.mode = mode
        self.top_k = top_k

    def get_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve documents using Mnemosyne API"""
        results = self.client.retrievals.search(
            query=query,
            mode=self.mode,
            top_k=self.top_k,
            collection_id=self.collection_id
        )

        # Convert to LangChain Documents
        documents = []
        for chunk in results.results:
            doc = Document(
                page_content=chunk.content,
                metadata={
                    "chunk_id": chunk.chunk_id,
                    "score": chunk.score,
                    "document_id": chunk.document.id,
                    "document_title": chunk.document.title,
                    **chunk.metadata
                }
            )
            documents.append(doc)

        return documents

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """Async version (not implemented - use AsyncMnemosyneRetriever)"""
        raise NotImplementedError("Use AsyncMnemosyneRetriever for async")


# Usage example
def main():
    # 1. Initialize Mnemosyne client and create collection
    client = Client(api_key="mn_your_api_key_here")

    collection = client.collections.create(
        name="LangChain Demo",
        description="Documents for LangChain integration"
    )

    # 2. Upload documents
    doc = client.documents.create(
        collection_id=collection.id,
        file="knowledge_base.pdf"
    )

    # Wait for processing...
    import time
    while client.documents.get_status(doc.id).status != "completed":
        time.sleep(2)

    # 3. Create Mnemosyne retriever
    retriever = MnemosyneRetriever(
        api_key="mn_your_api_key_here",
        collection_id=collection.id,
        mode="hybrid",
        top_k=5
    )

    # 4. Build LangChain RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=OpenAI(temperature=0),
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )

    # 5. Ask questions
    result = qa_chain({"query": "What is the main topic of this document?"})

    print("Answer:", result["result"])
    print("\nSource documents:")
    for i, doc in enumerate(result["source_documents"], 1):
        print(f"{i}. [{doc.metadata['score']:.3f}] {doc.metadata['document_title']}")
        print(f"   {doc.page_content[:200]}...\n")


if __name__ == "__main__":
    main()
```

---

## 10. Implementation Timeline

### Phase 1: Core SDK (Week 1)
- [ ] Project setup (Poetry, directory structure)
- [ ] Base client implementation (sync + async)
- [ ] Type definitions (Pydantic models)
- [ ] Collections resource (full CRUD)
- [ ] Documents resource (with file upload)
- [ ] Basic error handling
- [ ] Unit tests for core functionality

### Phase 2: Advanced Features (Week 2)
- [ ] Retrievals resource (5 modes)
- [ ] Chat resource with SSE streaming
- [ ] Retry logic and timeout handling
- [ ] Enhanced error messages
- [ ] Integration tests

### Phase 3: Examples & Documentation (Week 3)
- [ ] Ingestion workflow example (CORE - create, upload, monitor, verify)
- [ ] Basic retrieval/search example
- [ ] Video ingestion example (YouTube + MP4)
- [ ] Async streaming example
- [ ] LangChain integration example
- [ ] Comprehensive README (installation, quickstart, examples)
- [ ] API documentation (docstrings for all public methods)
- [ ] Type stubs (.pyi files)

### Phase 4: Publishing (Week 4)
- [ ] PyPI package setup
- [ ] CI/CD for testing
- [ ] Version tagging
- [ ] Release to PyPI
- [ ] Announcement and marketing

---

## 11. Dependencies

### Core Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.9"
httpx = "^0.25.0"        # HTTP client with sync/async support
pydantic = "^2.5.0"      # Type validation
typing-extensions = "^4.8.0"  # Type hints for older Python

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-httpx = "^0.26.0"  # Mock httpx requests
black = "^23.0.0"
mypy = "^1.7.0"
```

### Optional Dependencies (for examples)
```toml
[tool.poetry.group.examples.dependencies]
langchain = "^0.1.0"
openai = "^1.0.0"
```

---

## 12. Testing Strategy

### Unit Tests
- Mock all HTTP requests (pytest-httpx)
- Test each resource method
- Test error handling
- Test type validation

### Integration Tests
- Run against local Mnemosyne instance
- Test full workflows (upload → process → search)
- Test streaming chat
- Test LangChain integration

### Test Coverage Target
- **Core SDK**: 90%+ coverage
- **Resources**: 85%+ coverage
- **Examples**: Manual testing

---

## 13. Documentation Plan

### README.md
- Installation instructions
- Quick start guide
- Basic examples
- API reference link
- LangChain integration guide

### API Documentation
- Complete docstrings for all public methods
- Type hints throughout
- Usage examples in docstrings

### Examples Directory
- 6 complete examples:
  1. **ingestion_workflow.py** - Document upload and processing (CORE)
  2. **basic_usage.py** - Retrieval and search
  3. **video_ingestion.py** - YouTube and MP4 videos
  4. **async_example.py** - Async client usage
  5. **streaming_chat.py** - SSE streaming chat
  6. **langchain_integration.py** - LangChain retriever
- Comments explaining each step
- Real-world use cases

---

## 14. Key Decisions

### Why httpx over requests?
- Native async/await support
- Same API for sync and async
- Better HTTP/2 support
- Modern and actively maintained

### Why Pydantic v2?
- Type validation and serialization
- Matches backend schemas
- Better IDE support
- Performance improvements

### Why resource-based organization?
- Matches OpenAI/Anthropic SDK patterns
- More intuitive API (`client.documents.create()`)
- Easier to extend
- Better code organization

### Sync vs Async clients?
- Sync client for simple scripts
- Async client for production (better performance)
- Separate implementations (no sync wrapper over async)

---

## 15. Success Criteria

### Minimum Viable SDK (MVP)
- [ ] Sync and async clients working
- [ ] All 17 endpoints implemented
- [ ] **Full ingestion workflow** (collections + documents + status monitoring)
- [ ] **All 5 retrieval modes** (semantic, keyword, hybrid, hierarchical, graph)
- [ ] Type hints and validation
- [ ] SSE streaming for chat
- [ ] Basic error handling
- [ ] 3 core examples (ingestion, retrieval, langchain)

### Production-Ready SDK (v1.0)
- [ ] Comprehensive error handling
- [ ] Automatic retries with exponential backoff
- [ ] Full test coverage (90%+)
- [ ] **File upload support** (multipart/form-data for PDFs, DOCX, videos)
- [ ] **Video ingestion** (YouTube URL + MP4 file support)
- [ ] Complete documentation (README + API docs)
- [ ] Published to PyPI
- [ ] 6 complete examples (all use cases covered)
- [ ] LangChain integration tested and documented

---

## 16. Future Enhancements (Post v1.0)

### v1.1
- Pagination helpers (auto-fetch all pages)
- Batch operations (upload multiple files)
- Progress callbacks for uploads

### v1.2
- Caching layer (in-memory cache for retrievals)
- Request middleware system
- Custom headers support

### v1.3
- TypeScript SDK (same architecture)
- CLI tool (`mnemosyne upload file.pdf`)
- Sync wrappers for async methods

---

## 17. Open Questions

1. **Versioning**: Follow Mnemosyne API version or independent versioning?
   - **Recommendation**: Independent semantic versioning (SDK can evolve faster)

2. **Streaming chat in sync client**: Support or async-only?
   - **Recommendation**: Async-only (SSE requires async, sync would block)

3. **LangChain as core dependency or optional?**
   - **Recommendation**: Optional (extras_require for langchain integration)

4. **Retry configuration**: Exponential backoff or fixed delays?
   - **Recommendation**: Exponential backoff with jitter (industry standard)

5. **Base URL configuration**: Environment variable or constructor only?
   - **Recommendation**: Both (env var as default, constructor override)

---

## Summary

This plan provides a **complete blueprint** for implementing a production-ready Python SDK for Mnemosyne, following modern SDK design patterns from OpenAI and Anthropic.

**Key Features:**
- Dual sync/async clients
- Resource-based organization
- Full type safety with Pydantic
- SSE streaming support
- LangChain integration
- Comprehensive examples

**Timeline:** 4 weeks from start to PyPI publication

**Next Step:** Begin Phase 1 implementation with project setup and base client.
