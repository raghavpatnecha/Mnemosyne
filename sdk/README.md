# Mnemosyne Python SDK

[![PyPI version](https://badge.fury.io/py/mnemosyne-sdk.svg)](https://badge.fury.io/py/mnemosyne-sdk)
[![Python versions](https://img.shields.io/pypi/pyversions/mnemosyne-sdk.svg)](https://pypi.org/project/mnemosyne-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Official Python SDK for the Mnemosyne RAG (Retrieval-Augmented Generation) API. Build powerful search and chat applications with semantic retrieval, graph-based search, and streaming responses.

## Features

- 🚀 **Modern & Type-Safe**: Built with Pydantic v2 for full type safety
- ⚡ **Async Ready**: Native async/await support with `AsyncClient`
- 🔍 **5 Search Modes**: Semantic, keyword, hybrid, hierarchical, and graph-based (LightRAG)
- 💬 **Streaming Chat**: Real-time SSE streaming for chat responses
- 📹 **Video Support**: Ingest and search YouTube videos and MP4 files
- 🔗 **LangChain Integration**: Drop-in retriever for LangChain workflows
- 🛡️ **Robust**: Automatic retry with exponential backoff
- 📦 **Zero Config**: Works out of the box with sensible defaults

## Installation

```bash
pip install mnemosyne-sdk
```

Or with Poetry:

```bash
poetry add mnemosyne-sdk
```

## Quick Start

### Basic Usage

```python
from mnemosyne import Client

# Initialize client
client = Client(api_key="mn_...")

# Create a collection
collection = client.collections.create(
    name="Research Papers",
    description="AI/ML research papers"
)

# Upload documents
doc = client.documents.create(
    collection_id=collection.id,
    file="paper.pdf",
    metadata={"topic": "transformers"}
)

# Search (5 modes available)
results = client.retrievals.retrieve(
    query="What are transformers?",
    mode="hybrid",  # semantic, keyword, hybrid, hierarchical, graph
    top_k=10
)

# Print results
for result in results.results:
    print(f"Score: {result.score:.4f}")
    print(f"Content: {result.content[:200]}...")
```

### Async Usage

```python
import asyncio
from mnemosyne import AsyncClient

async def main():
    async with AsyncClient(api_key="mn_...") as client:
        # Create collection
        collection = await client.collections.create(name="Papers")

        # Upload multiple documents concurrently
        tasks = [
            client.documents.create(collection.id, f"paper{i}.pdf")
            for i in range(10)
        ]
        docs = await asyncio.gather(*tasks)

        # Search
        results = await client.retrievals.retrieve(
            query="transformers",
            mode="hybrid"
        )

asyncio.run(main())
```

### Streaming Chat

```python
# Real-time streaming chat
for chunk in client.chat.chat(
    message="Explain transformers",
    stream=True
):
    print(chunk, end="", flush=True)
```

## Core Concepts

### Collections

Collections organize your documents. Think of them as databases or namespaces.

```python
# Create
collection = client.collections.create(
    name="My Collection",
    metadata={"domain": "AI"}
)

# List
collections = client.collections.list(limit=20, offset=0)

# Get
collection = client.collections.get(collection_id)

# Update
client.collections.update(
    collection_id=collection.id,
    name="Updated Name"
)

# Delete
client.collections.delete(collection_id)
```

### Documents

Documents are files (PDF, DOCX, TXT, MP4, YouTube URLs) ingested into collections.

```python
# Upload a file
doc = client.documents.create(
    collection_id=collection.id,
    file="path/to/file.pdf",
    metadata={"author": "John Doe"}
)

# Upload YouTube video
doc = client.documents.create(
    collection_id=collection.id,
    file="https://youtube.com/watch?v=...",
    metadata={"title": "AI Lecture"}
)

# Check processing status
status = client.documents.get_status(doc.id)
print(f"Status: {status.status}")  # pending, processing, completed, failed
print(f"Chunks: {status.chunk_count}")
print(f"Tokens: {status.total_tokens}")

# List documents
docs = client.documents.list(
    collection_id=collection.id,
    status_filter="completed"
)

# Update metadata
client.documents.update(
    document_id=doc.id,
    title="Updated Title"
)

# Delete
client.documents.delete(doc.id)
```

### Retrievals

Search across your documents using 5 different modes:

#### 1. Semantic Search
Best for conceptual similarity, meaning-based retrieval.
```python
results = client.retrievals.retrieve(
    query="What are transformers?",
    mode="semantic",
    top_k=10
)
```

#### 2. Keyword Search (BM25)
Best for exact term matching, technical jargon.
```python
results = client.retrievals.retrieve(
    query="attention mechanism",
    mode="keyword",
    top_k=10
)
```

#### 3. Hybrid Search (Recommended)
Combines semantic and keyword search for balanced results.
```python
results = client.retrievals.retrieve(
    query="transformer architecture",
    mode="hybrid",
    top_k=10
)
```

#### 4. Hierarchical Search
Best for long documents, structured content with multiple levels.
```python
results = client.retrievals.retrieve(
    query="introduction to RAG",
    mode="hierarchical",
    top_k=10
)
```

#### 5. Graph Search (LightRAG)
Best for complex reasoning, entity relationships, knowledge graphs.
```python
results = client.retrievals.retrieve(
    query="how do transformers relate to BERT?",
    mode="graph",
    top_k=10
)
```

#### Metadata Filtering
```python
results = client.retrievals.retrieve(
    query="transformers",
    mode="hybrid",
    collection_id=collection.id,
    metadata_filter={"year": 2024, "topic": "AI"}
)
```

### Chat

Conversational AI with RAG-powered responses.

```python
# Streaming chat
for chunk in client.chat.chat(
    message="What are transformers?",
    stream=True,
    top_k=5  # Number of chunks to retrieve
):
    print(chunk, end="")

# Multi-turn conversation
session_id = None
for message in ["What is RAG?", "How does it work?", "Give me an example"]:
    for chunk in client.chat.chat(message, session_id=session_id):
        print(chunk, end="")
    # Extract session_id from first response for continuity

# List sessions
sessions = client.chat.list_sessions()

# Get session messages
messages = client.chat.get_session_messages(session_id)

# Delete session
client.chat.delete_session(session_id)
```

## Advanced Examples

### Complete Ingestion Workflow

See `examples/ingestion_workflow.py` for a full 5-step workflow:
1. Create collection
2. Batch upload documents
3. Monitor processing status
4. Verify ingestion
5. Update metadata

```bash
python examples/ingestion_workflow.py
```

### Video Ingestion

See `examples/video_ingestion.py`:
```python
# YouTube
doc = client.documents.create(
    collection_id=collection.id,
    file="https://youtube.com/watch?v=xyz",
    metadata={"title": "AI Lecture"}
)

# Local MP4
doc = client.documents.create(
    collection_id=collection.id,
    file="meeting_recording.mp4",
    metadata={"meeting_type": "standup"}
)
```

### LangChain Integration

See `examples/langchain_integration.py`:
```python
from mnemosyne import Client
from langchain.schema.retriever import BaseRetriever
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI

class MnemosyneRetriever(BaseRetriever):
    client: Client
    collection_id: UUID

    def _get_relevant_documents(self, query: str):
        results = self.client.retrievals.retrieve(
            query=query,
            mode="hybrid",
            collection_id=self.collection_id
        )
        # Convert to LangChain Document format...

# Build QA chain
retriever = MnemosyneRetriever(client=client, collection_id=coll_id)
qa_chain = RetrievalQA.from_chain_type(
    llm=OpenAI(),
    retriever=retriever
)
```

## Error Handling

```python
from mnemosyne import (
    Client,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    APIError
)

try:
    client = Client(api_key="invalid")
    collection = client.collections.create(name="Test")
except AuthenticationError:
    print("Invalid API key")
except ValidationError as e:
    print(f"Invalid request: {e.message}")
except RateLimitError:
    print("Rate limit exceeded")
except NotFoundError:
    print("Resource not found")
except APIError as e:
    print(f"API error: {e.message}")
```

## Configuration

### Environment Variables

```bash
export MNEMOSYNE_API_KEY="mn_..."
export MNEMOSYNE_BASE_URL="https://api.mnemosyne.ai/api/v1"
```

### Custom Configuration

```python
client = Client(
    api_key="mn_...",
    base_url="https://api.mnemosyne.ai/api/v1",
    timeout=120.0,  # seconds
    max_retries=5
)
```

### Context Manager (Recommended)

```python
with Client(api_key="mn_...") as client:
    # Use client
    results = client.retrievals.retrieve(...)
# Client automatically closes
```

## Examples

All examples are in the `examples/` directory:

1. **`ingestion_workflow.py`** - Complete document ingestion lifecycle
2. **`basic_retrieval.py`** - All 5 search modes demonstrated
3. **`video_ingestion.py`** - YouTube and MP4 video processing
4. **`async_streaming.py`** - Async/await with concurrent operations
5. **`streaming_chat.py`** - Real-time chat with SSE streaming
6. **`langchain_integration.py`** - LangChain retriever and QA chains

Run any example:
```bash
python examples/ingestion_workflow.py
```

## Development

### Setup

```bash
git clone https://github.com/yourusername/mnemosyne-sdk
cd mnemosyne-sdk/sdk
poetry install
```

### Run Tests

```bash
poetry run pytest
poetry run pytest --cov=mnemosyne --cov-report=html
```

### Linting

```bash
poetry run black mnemosyne tests
poetry run ruff check mnemosyne tests
poetry run mypy mnemosyne
```

## API Reference

Full API documentation: https://docs.mnemosyne.dev

### Client Classes
- `Client` - Synchronous client
- `AsyncClient` - Asynchronous client

### Resources
- `client.collections` - Collection management
- `client.documents` - Document upload and management
- `client.retrievals` - Search and retrieval
- `client.chat` - Conversational AI

### Type Models
- `CollectionResponse`, `CollectionCreate`, `CollectionUpdate`
- `DocumentResponse`, `DocumentStatusResponse`
- `RetrievalResponse`, `ChunkResult`
- `ChatResponse`, `ChatSessionResponse`

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

MIT License - see [LICENSE](LICENSE) file.

## Support

- Documentation: https://docs.mnemosyne.dev
- Issues: https://github.com/yourusername/mnemosyne/issues
- Email: support@mnemosyne.dev

## Acknowledgments

Built with:
- [httpx](https://www.python-httpx.org/) - Modern HTTP client
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [LightRAG](https://github.com/HKUDS/LightRAG) - Graph-based retrieval
