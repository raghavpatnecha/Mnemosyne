# TypeScript SDK Examples

This directory contains working examples demonstrating all features of the Mnemosyne TypeScript SDK.

## Prerequisites

1. **Install dependencies**:
   ```bash
   cd sdk-ts
   npm install
   npm run build
   ```

2. **Set up environment variables**:
   ```bash
   export MNEMOSYNE_API_KEY="mn_your_api_key"
   export MNEMOSYNE_BASE_URL="http://localhost:8000/api/v1"
   ```

3. **Start Mnemosyne backend**:
   ```bash
   docker-compose up -d
   ```

## Examples

### 1. Basic Retrieval (`basic-retrieval.ts`)
Demonstrates all 5 search modes:
- Semantic search (embeddings)
- Keyword search (BM25)
- Hybrid search (recommended)
- Hierarchical search
- Graph search (LightRAG)
- HybridRAG (search + knowledge graph)

```bash
npm run build && node examples/basic-retrieval.js
```

### 2. Ingestion Workflow (`ingestion-workflow.ts`)
Complete document ingestion pipeline:
- Create collection
- Batch upload documents
- Monitor processing status
- Verify ingestion
- Update metadata

```bash
npm run build && node examples/ingestion-workflow.js
```

### 3. Video Ingestion (`video-ingestion.ts`)
Video processing examples:
- Ingest YouTube videos
- Ingest local MP4 files
- Monitor video processing
- Search transcribed content

```bash
npm run build && node examples/video-ingestion.js
```

### 4. Streaming Chat (`streaming-chat.ts`)
Real-time chat with SSE:
- Basic streaming chat
- Multi-turn conversations
- Session management
- Streaming vs non-streaming comparison

```bash
npm run build && node examples/streaming-chat.js
```

### 5. Async Operations (`async-operations.ts`)
Concurrent processing patterns:
- Concurrent document uploads
- Parallel search operations
- Batch status checking
- Efficient processing pipelines

```bash
npm run build && node examples/async-operations.js
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MNEMOSYNE_API_KEY` | Your API key | Required |
| `MNEMOSYNE_BASE_URL` | API base URL | `http://localhost:8000/api/v1` |
| `COLLECTION_ID` | Collection ID for retrieval examples | Required for retrieval |
| `DOCS_DIR` | Directory with documents to upload | `./demo_docs` |

## Quick Start

Run all examples in sequence:

```bash
# Build the SDK
npm run build

# Run examples
node examples/ingestion-workflow.js
node examples/basic-retrieval.js
node examples/streaming-chat.js
node examples/async-operations.js
```

## Tips

- **Use TypeScript**: All examples work with TypeScript via `ts-node`
- **Error Handling**: Examples include comprehensive error handling
- **Production Ready**: Patterns shown are production-ready
- **Parallel Execution**: Use `Promise.all()` for concurrent operations

## Need Help?

- [SDK Documentation](../README.md)
- [API Reference](../../docs/user/api-reference.md)
- [GitHub Issues](https://github.com/raghavpatnecha/Mnemosyne/issues)
