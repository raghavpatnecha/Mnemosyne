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
- 🎯 **Multimodal Support**: Documents, images, audio, video, and Excel files
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
    if chunk.type == "delta" and chunk.content:
        print(chunk.content, end="", flush=True)
    elif chunk.type == "sources":
        print(f"\n\nSources: {[s.title for s in chunk.sources]}")
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

# Upload with document type hint for specialized processing
doc = client.documents.create(
    collection_id=collection.id,
    file="contract.pdf",
    metadata={
        "document_type": "legal"  # legal, academic, qa, table, or general
    }
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

#### Document Type Filtering
Filter results by document type (legal, academic, qa, table, general):
```python
# Search only legal documents
results = client.retrievals.retrieve(
    query="contract termination clause",
    mode="hybrid",
    document_type="legal"  # Only search legal documents
)

# Search only academic papers
results = client.retrievals.retrieve(
    query="methodology section",
    mode="hybrid",
    document_type="academic"  # Only search academic papers
)
```

### Chat

Conversational AI with RAG-powered responses.

```python
# Streaming chat
for chunk in client.chat.chat(
    message="What are transformers?",
    stream=True,
    retrieval={"top_k": 5}  # Retrieval configuration
):
    if chunk.type == "delta" and chunk.content:
        print(chunk.content, end="")
    elif chunk.type == "sources":
        print(f"\nSources: {[s.title for s in chunk.sources]}")

# Non-streaming chat
response = client.chat.chat(
    message="What are transformers?",
    stream=False
)
print(response.response)
print(f"Sources: {response.sources}")

# Multi-turn conversation
session_id = None
for message in ["What is RAG?", "How does it work?", "Give me an example"]:
    for chunk in client.chat.chat(message, session_id=session_id):
        if chunk.type == "delta" and chunk.content:
            print(chunk.content, end="")
        elif chunk.type == "done" and chunk.metadata:
            session_id = chunk.metadata.session_id  # Extract for continuity
    print()  # Newline between messages

# List sessions
sessions = client.chat.list_sessions()

# Get session messages
messages = client.chat.get_session_messages(session_id)

# Delete session
client.chat.delete_session(session_id)
```

### Answer Style Presets

Control response style with presets:

```python
# Concise answers for quick lookups
for chunk in client.chat.chat("What is RAG?", preset="concise"):
    if chunk.type == "delta":
        print(chunk.content, end="")

# Research-grade responses with thorough analysis
for chunk in client.chat.chat(
    message="Compare vector databases",
    preset="research",
    model="gpt-4o"
):
    if chunk.type == "delta":
        print(chunk.content, end="")

# Technical precise answers with exact details
for chunk in client.chat.chat(
    message="How to implement cosine similarity?",
    preset="technical"
):
    if chunk.type == "delta":
        print(chunk.content, end="")
```

**Available Presets**:
| Preset | Temperature | Max Tokens | Best For |
|--------|-------------|------------|----------|
| `concise` | 0.3 | 500 | Quick lookups, simple questions |
| `detailed` | 0.5 | 2000 | General explanations (default) |
| `research` | 0.2 | 4000 | Academic analysis, thorough coverage |
| `technical` | 0.1 | 3000 | Precise, detail-oriented answers |
| `creative` | 0.8 | 2000 | Brainstorming, exploratory answers |
| `qna` | 0.4 | 4000 | Question generation (MCQs, quizzes, study materials) |

### Custom Instructions

Add custom guidance to your prompts for specialized tasks:

```python
# Generate MCQs from document content
for chunk in client.chat.chat(
    message="Create questions about machine learning",
    preset="qna",
    custom_instruction="Generate 10 multiple choice questions with 4 options each. Mark the correct answer."
):
    if chunk.type == "delta":
        print(chunk.content, end="")

# Focus on specific aspects
for chunk in client.chat.chat(
    message="Analyze this codebase",
    preset="technical",
    custom_instruction="Focus on security vulnerabilities and potential exploits"
):
    if chunk.type == "delta":
        print(chunk.content, end="")
```

### Follow-up Questions

Use `is_follow_up=True` to preserve context from previous exchanges:

```python
# Initial question
session_id = None
for chunk in client.chat.chat("What is RAG?", session_id=session_id):
    if chunk.type == "delta":
        print(chunk.content, end="")
    elif chunk.type == "done" and chunk.metadata:
        session_id = chunk.metadata.session_id
print()

# Follow-up question with context preservation
for chunk in client.chat.chat(
    "How does it compare to fine-tuning?",
    session_id=session_id,
    is_follow_up=True  # Preserves context from previous exchange
):
    if chunk.type == "delta":
        print(chunk.content, end="")
```

### Deep Reasoning Mode

Multi-step iterative reasoning for complex questions:

```python
# Deep reasoning decomposes queries and iteratively retrieves context
for chunk in client.chat.chat(
    message="Compare RAG architectures and recommend the best for legal documents",
    preset="research",
    reasoning_mode="deep",
    model="gpt-4o"
):
    if chunk.type == "reasoning_step":
        print(f"\n[Step {chunk.step}] {chunk.description}")
    elif chunk.type == "sub_query":
        print(f"  Searching: {chunk.query}")
    elif chunk.type == "delta":
        print(chunk.content, end="")
    elif chunk.type == "sources":
        print(f"\nSources: {len(chunk.sources)} documents")
```

**Stream Chunk Types**:
- `delta`: Incremental text content
- `sources`: Retrieved source documents
- `reasoning_step`: Deep reasoning progress (step number + description)
- `sub_query`: Sub-query being processed during deep reasoning
- `usage`: Token usage statistics
- `done`: Stream completion with metadata
- `error`: Error message if something fails

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

### Timeout and Retry Behavior

The SDK includes built-in timeout and retry handling:

```python
# Configure for long-running operations
client = Client(
    api_key="mn_...",
    timeout=300.0,  # 5 minutes for large document processing
    max_retries=5   # More retries for unreliable networks
)
```

**Timeout Behavior:**
- Default: 60 seconds
- Applies to all HTTP requests
- Raises `APIError` on timeout

**Retry Behavior:**
- Default: 3 retries
- Uses exponential backoff (1s, 2s, 4s, ...)
- Retries on: network errors, 5xx errors, rate limits (429)
- Does NOT retry: 4xx errors (except 429), validation errors

**Rate Limiting:**
The SDK automatically handles rate limits with exponential backoff:

```python
from mnemosyne import Client, RateLimitError

try:
    results = client.retrievals.retrieve(query="test")
except RateLimitError:
    # SDK already retried with backoff - retries exhausted
    print("Rate limit exceeded after all retries")
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

### Core Examples
1. **`ingestion_workflow.py`** - Complete document ingestion lifecycle
2. **`basic_retrieval.py`** - All 5 search modes demonstrated
3. **`streaming_chat.py`** - Real-time chat with SSE streaming
4. **`async_streaming.py`** - Async/await with concurrent operations
5. **`langchain_integration.py`** - LangChain retriever and QA chains

### Multimodal Examples
6. **`video_ingestion.py`** - YouTube and MP4 video processing
7. **`image_ingestion.py`** - Image analysis with GPT-4 Vision (PNG, JPG, WEBP)
8. **`audio_ingestion.py`** - Audio transcription with Whisper (MP3, WAV, M4A, FLAC)
9. **`excel_ingestion.py`** - Excel spreadsheet processing (XLSX, XLS)
10. **`multimodal_ingestion.py`** - Combined multimodal knowledge base

Run any example:
```bash
python examples/ingestion_workflow.py
python examples/multimodal_ingestion.py
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
- Issues: https://github.com/raghavpatnecha/Mnemosyne/issues
- Email: support@mnemosyne.dev

## Acknowledgments

Built with:
- [httpx](https://www.python-httpx.org/) - Modern HTTP client
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [LightRAG](https://github.com/HKUDS/LightRAG) - Graph-based retrieval
