# Getting Started with Mnemosyne

This guide will help you get up and running with Mnemosyne in under 10 minutes.

## What is Mnemosyne?

Mnemosyne is an open-source RAG-as-a-Service platform that lets you:
- Upload documents (PDF, DOCX, MP4, YouTube videos)
- Search semantically across your content
- Build conversational AI applications with RAG

## Installation

### Option 1: Use the Python SDK (Recommended)

```bash
pip install mnemosyne-sdk
```

### Option 2: Self-Host with Docker

```bash
git clone https://github.com/raghavpatnecha/Mnemosyne.git
cd Mnemosyne
docker-compose up -d
```

## Quick Start with Python SDK

### 1. Initialize the Client

```python
from mnemosyne import Client

client = Client(
    api_key="mn_..."  # Get from registration or self-hosted instance
)
```

### 2. Create a Collection

Collections organize your documents:

```python
collection = client.collections.create(
    name="My Research Papers",
    description="AI and ML research papers"
)
print(f"Collection ID: {collection.id}")
```

### 3. Upload Documents

```python
# Upload a PDF
doc = client.documents.create(
    collection_id=collection.id,
    file="path/to/paper.pdf",
    metadata={"topic": "transformers", "year": 2024}
)

# Upload a YouTube video
video_doc = client.documents.create(
    collection_id=collection.id,
    file="https://youtube.com/watch?v=xyz",
    metadata={"title": "AI Lecture"}
)

print(f"Document ID: {doc.id}")
print(f"Status: {doc.status}")  # pending, processing, completed, failed
```

### 4. Wait for Processing

Documents are processed asynchronously. Check status:

```python
import time

while True:
    status = client.documents.get_status(doc.id)
    if status.status == "completed":
        print(f"✓ Processing complete! {status.chunk_count} chunks created")
        break
    elif status.status == "failed":
        print(f"✗ Processing failed: {status.error_message}")
        break
    else:
        print(f"⏳ Processing... ({status.status})")
        time.sleep(5)
```

### 5. Search Your Documents

Five search modes available:

#### Hybrid Search (Recommended)

```python
results = client.retrievals.retrieve(
    query="What are transformers in AI?",
    mode="hybrid",  # Combines semantic + keyword
    top_k=10,
    collection_id=collection.id
)

for result in results.results:
    print(f"\nScore: {result.score:.4f}")
    print(f"Content: {result.content[:200]}...")
    print(f"Document: {result.document.title}")
```

#### Other Search Modes

```python
# Semantic search (vector similarity)
results = client.retrievals.retrieve(
    query="transformer architecture",
    mode="semantic"
)

# Keyword search (BM25)
results = client.retrievals.retrieve(
    query="attention mechanism",
    mode="keyword"
)

# Hierarchical search (for long documents)
results = client.retrievals.retrieve(
    query="introduction to RAG",
    mode="hierarchical"
)

# Graph search (knowledge graph with LightRAG)
results = client.retrievals.retrieve(
    query="how do transformers relate to BERT?",
    mode="graph"
)
```

### 6. Conversational AI

Build chat applications with streaming:

```python
# Streaming chat
for chunk in client.chat.chat(
    message="Explain transformers in simple terms",
    stream=True,
    collection_id=collection.id,  # Search within this collection
    top_k=5  # Use top 5 chunks as context
):
    print(chunk, end="", flush=True)

print("\n")

# Multi-turn conversation
session_id = None
for message in ["What is RAG?", "How does it work?", "Give me an example"]:
    print(f"\nUser: {message}")
    print("Assistant: ", end="")
    for chunk in client.chat.chat(
        message=message,
        session_id=session_id,
        stream=True
    ):
        print(chunk, end="", flush=True)
        # Extract session_id from first response
```

## Complete Example

```python
from mnemosyne import Client
import time

# Initialize
client = Client(api_key="mn_...")

# Create collection
collection = client.collections.create(
    name="AI Research",
    description="Papers on transformers and RAG"
)

# Upload document
doc = client.documents.create(
    collection_id=collection.id,
    file="attention_is_all_you_need.pdf",
    metadata={"authors": "Vaswani et al.", "year": 2017}
)

# Wait for processing
while True:
    status = client.documents.get_status(doc.id)
    if status.status == "completed":
        break
    time.sleep(5)

# Search
results = client.retrievals.retrieve(
    query="What is the attention mechanism?",
    mode="hybrid",
    collection_id=collection.id,
    top_k=5
)

# Print results
for i, result in enumerate(results.results, 1):
    print(f"\n{i}. Score: {result.score:.4f}")
    print(f"   {result.content[:150]}...")

# Chat
print("\nChat:")
for chunk in client.chat.chat(
    message="Explain the attention mechanism",
    collection_id=collection.id,
    stream=True
):
    print(chunk, end="", flush=True)
```

## Async Usage

For high-performance applications:

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
            mode="hybrid",
            collection_id=collection.id
        )

        print(f"Found {len(results.results)} results")

asyncio.run(main())
```

## Self-Hosting

### Docker Compose (Quick Start)

```bash
# Clone repository
git clone https://github.com/raghavpatnecha/Mnemosyne.git
cd Mnemosyne

# Configure environment
cp .env.example .env
nano .env  # Add your OpenAI API key

# Start services
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

Services will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3000

### Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
```

Save the `api_key` from the response and use it with the SDK:

```python
client = Client(
    api_key="mn_...",
    base_url="http://localhost:8000"
)
```

## Next Steps

- **[API Reference](api-reference.md)** - Complete API documentation
- **[Architecture](architecture.md)** - Understand how Mnemosyne works
- **[Deployment Guide](deployment.md)** - Production deployment
- **[SDK Examples](../../sdk/examples/)** - More code examples

## Troubleshooting

### Document stuck in "processing"

Check the Celery worker logs:
```bash
docker-compose logs -f celery-worker
```

### Search returns no results

Ensure document processing completed:
```python
status = client.documents.get_status(doc.id)
print(f"Status: {status.status}, Chunks: {status.chunk_count}")
```

### API authentication errors

Verify your API key:
```python
client = Client(api_key="mn_...")  # Must start with "mn_"
```

## Getting Help

- **Documentation**: https://docs.mnemosyne.dev
- **API Docs**: https://api.mnemosyne.dev/docs
- **Issues**: https://github.com/raghavpatnecha/Mnemosyne/issues
- **Discussions**: https://github.com/raghavpatnecha/Mnemosyne/discussions
