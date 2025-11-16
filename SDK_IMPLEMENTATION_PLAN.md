# Mnemosyne Python SDK - Implementation Plan

**Date:** November 17, 2025
**Status:** Planning Phase
**Goal:** Create a production-ready Python SDK for Mnemosyne API

---

## 1. Overview

### Purpose
Provide developers with an easy-to-use Python SDK for interacting with the Mnemosyne RAG API, following modern SDK patterns used by OpenAI, Anthropic, and Stripe.

### Key Features
- **Dual client architecture**: Sync (`Client`) and async (`AsyncClient`)
- **Resource-based organization**: `client.collections.create()`, `client.documents.list()`, etc.
- **Full type hints**: Complete type safety with Pydantic models
- **Streaming support**: SSE streaming for chat endpoint
- **Error handling**: Custom exceptions with helpful error messages
- **Automatic retries**: Configurable retry logic for network failures
- **LangChain integration**: First-class support via custom retriever

---

## 2. Current API Analysis

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
│   ├── basic_usage.py        # Normal example
│   ├── langchain_integration.py  # LangChain example
│   ├── async_example.py      # Async client example
│   └── streaming_chat.py     # SSE streaming example
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

### Example 1: Basic Usage (Normal SDK)

```python
# examples/basic_usage.py
"""
Basic Mnemosyne SDK usage example
Demonstrates core functionality: collections, documents, retrieval, chat
"""

from mnemosyne import Client
from uuid import UUID

# Initialize client
client = Client(api_key="mn_your_api_key_here")

# 1. Create a collection
print("Creating collection...")
collection = client.collections.create(
    name="Research Papers",
    description="AI and ML research papers",
    metadata={"topic": "machine_learning"}
)
print(f"Created collection: {collection.id}")

# 2. Upload documents
print("\nUploading documents...")
doc1 = client.documents.create(
    collection_id=collection.id,
    file="papers/attention_is_all_you_need.pdf",
    metadata={"year": 2017, "authors": ["Vaswani et al."]}
)
print(f"Uploaded document: {doc1.id} (status: {doc1.status})")

# Wait for processing
import time
while True:
    status = client.documents.get_status(doc1.id)
    print(f"Processing status: {status.status} ({status.chunk_count} chunks)")
    if status.status == "completed":
        break
    time.sleep(2)

# 3. Search with different modes
print("\n--- Semantic Search ---")
results = client.retrievals.search(
    query="What is the transformer architecture?",
    mode="semantic",
    top_k=5,
    collection_id=collection.id
)
for i, chunk in enumerate(results.results, 1):
    print(f"{i}. [Score: {chunk.score:.3f}] {chunk.content[:100]}...")

print("\n--- Hybrid Search (Vector + Keyword) ---")
results = client.retrievals.search(
    query="attention mechanism",
    mode="hybrid",
    top_k=5
)
print(f"Found {results.total_results} results")

print("\n--- Graph Search (LightRAG) ---")
results = client.retrievals.search(
    query="Who proposed the transformer model?",
    mode="graph",
    top_k=10
)
print(results.results[0].content)

# 4. Conversational chat (async required for streaming)
# See async_example.py for streaming chat

# 5. List and manage resources
print("\n--- Collections ---")
collections = client.collections.list(limit=10)
print(f"Total collections: {collections.pagination['total']}")
for col in collections.data:
    print(f"  - {col.name}: {col.document_count} documents")

# 6. Update metadata
client.collections.update(
    collection_id=collection.id,
    metadata={"topic": "machine_learning", "updated": True}
)

# 7. Cleanup
client.documents.delete(doc1.id)
client.collections.delete(collection.id)
client.close()
```

### Example 2: Async Client with Streaming

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
- [ ] Basic usage example
- [ ] Async streaming example
- [ ] LangChain integration example
- [ ] Comprehensive README
- [ ] API documentation (docstrings)
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
- 4 complete examples (basic, async, streaming, langchain)
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
- [ ] Type hints and validation
- [ ] SSE streaming for chat
- [ ] Basic error handling
- [ ] 2 examples (basic + langchain)

### Production-Ready SDK (v1.0)
- [ ] Comprehensive error handling
- [ ] Automatic retries
- [ ] Full test coverage (90%+)
- [ ] Complete documentation
- [ ] Published to PyPI
- [ ] 4 complete examples
- [ ] LangChain integration tested

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
