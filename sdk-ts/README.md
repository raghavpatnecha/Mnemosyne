# Mnemosyne TypeScript SDK

Official TypeScript/JavaScript SDK for [Mnemosyne](https://github.com/raghavpatnecha/Mnemosyne) - the open-source RAG-as-a-Service platform.

## Features

- **Zero Dependencies**: Uses native `fetch` API (Node.js 18+)
- **Full TypeScript Support**: Strict typing with comprehensive type definitions
- **Streaming Chat**: Real-time SSE (Server-Sent Events) streaming
- **Multipart Uploads**: File and document uploads with metadata
- **Automatic Retries**: Exponential backoff for failed requests
- **5 Search Modes**: Semantic, keyword, hybrid, hierarchical, and graph search
- **HybridRAG**: Knowledge graph-enhanced retrieval
- **Dual Format**: CommonJS and ES Module support

## Installation

```bash
npm install @mnemosyne/sdk
# or
yarn add @mnemosyne/sdk
# or
pnpm add @mnemosyne/sdk
```

## Quick Start

```typescript
import { MnemosyneClient } from '@mnemosyne/sdk';

// Initialize client
const client = new MnemosyneClient({
  apiKey: process.env.MNEMOSYNE_API_KEY,
  baseUrl: 'http://localhost:8000/api/v1', // Optional
});

// Create a collection
const collection = await client.collections.create({
  name: 'Research Papers',
  description: 'AI/ML research collection',
});

// Upload a document
const document = await client.documents.create(
  collection.id,
  './paper.pdf',
  { author: 'John Doe', year: 2024 }
);

// Search with hybrid mode
const results = await client.retrievals.retrieve({
  query: 'What are transformers?',
  mode: 'hybrid',
  collection_id: collection.id,
  top_k: 5,
});

// Chat with streaming
for await (const chunk of client.chat.chat({
  message: 'Explain the key concepts',
  collection_id: collection.id,
  stream: true,
})) {
  process.stdout.write(chunk);
}
```

## Configuration

### Environment Variables

```bash
export MNEMOSYNE_API_KEY="mn_your_api_key_here"
export MNEMOSYNE_BASE_URL="http://localhost:8000/api/v1"  # Optional
```

### Client Options

```typescript
const client = new MnemosyneClient({
  apiKey: 'mn_your_api_key',          // Required (or set env var)
  baseUrl: 'http://localhost:8000/api/v1', // Optional, default: http://localhost:8000/api/v1
  timeout: 60000,                      // Optional, default: 60 seconds
  maxRetries: 3,                       // Optional, default: 3
});
```

## API Reference

### Collections

```typescript
// Create collection
const collection = await client.collections.create({
  name: 'My Collection',
  description: 'Optional description',
  metadata: { key: 'value' },
});

// List collections with pagination
const { data, pagination } = await client.collections.list({
  limit: 20,
  offset: 0,
});

// Get collection by ID
const collection = await client.collections.get('coll_123');

// Update collection
const updated = await client.collections.update('coll_123', {
  name: 'Updated Name',
  metadata: { updated: true },
});

// Delete collection
await client.collections.delete('coll_123');
```

### Documents

**Note:** File path uploads (`string`) only work in Node.js. In browsers, use `File` or `Blob` objects from `<input type="file">`.

```typescript
// Upload file (File object, Blob, or file path)
// Node.js: supports file paths
const doc = await client.documents.create(
  'coll_123',
  './document.pdf',  // string path (Node.js only)
  { custom: 'metadata' }
);

// Browser: use File from input
const doc = await client.documents.create(
  'coll_123',
  fileInput.files[0],  // File object (works everywhere)
  { custom: 'metadata' }
);

// List documents
const { data, pagination } = await client.documents.list({
  collection_id: 'coll_123',
  status_filter: 'completed',
  limit: 20,
  offset: 0,
});

// Get document
const doc = await client.documents.get('doc_123');

// Check processing status
const status = await client.documents.getStatus('doc_123');
console.log(status.status); // 'pending' | 'processing' | 'completed' | 'failed'
console.log(status.chunk_count, status.total_tokens);

// Delete document
await client.documents.delete('doc_123');
```

### Retrievals

```typescript
// Semantic search (embeddings)
const results = await client.retrievals.retrieve({
  query: 'machine learning',
  mode: 'semantic',
  top_k: 5,
});

// Keyword search (BM25)
const results = await client.retrievals.retrieve({
  query: 'neural networks',
  mode: 'keyword',
  top_k: 10,
});

// Hybrid search (recommended)
const results = await client.retrievals.retrieve({
  query: 'deep learning',
  mode: 'hybrid',
  top_k: 5,
  rerank: true,  // Optional reranking
});

// Graph search (LightRAG)
const results = await client.retrievals.retrieve({
  query: 'AI architectures',
  mode: 'graph',
  collection_id: 'coll_123',
});

// HybridRAG (search + knowledge graph)
const results = await client.retrievals.retrieve({
  query: 'transformers',
  mode: 'hybrid',
  enable_graph: true,  // Enhance with graph
  collection_id: 'coll_123',
});

// Access results
results.results.forEach((result) => {
  console.log(`Score: ${result.score}`);
  console.log(`Content: ${result.content}`);
  console.log(`Document: ${result.document.title}`);
});
console.log(`Processing time: ${results.processing_time_ms}ms`);
```

### Chat

```typescript
// Streaming chat (SSE)
for await (const chunk of client.chat.chat({
  message: 'What are the main topics?',
  collection_id: 'coll_123',
  stream: true,
  top_k: 5,
})) {
  process.stdout.write(chunk);
}

// Non-streaming chat
for await (const response of client.chat.chat({
  message: 'Summarize the key points',
  stream: false,
})) {
  console.log(response);
}

// Multi-turn conversation
let sessionId: string | undefined;

for (const question of questions) {
  for await (const chunk of client.chat.chat({
    message: question,
    session_id: sessionId,
    stream: true,
  })) {
    process.stdout.write(chunk);
  }
  // Extract session_id from response metadata for next turn
}

// Session management
const sessions = await client.chat.listSessions({ limit: 10 });
const messages = await client.chat.getSessionMessages('session_123');
await client.chat.deleteSession('session_123');
```

### Authentication

```typescript
// Register new user (returns API key)
const response = await client.auth.register(
  'user@example.com',
  'secure_password_123'
);
console.log('API Key:', response.api_key);
// IMPORTANT: Save this API key securely - it's only shown once!
```

## Search Modes

### 1. Semantic Search
Vector similarity search using embeddings (pgvector + cosine distance).

```typescript
const results = await client.retrievals.retrieve({
  query: 'machine learning algorithms',
  mode: 'semantic',
  top_k: 5,
});
```

**Best for**: Conceptual searches, finding similar meaning

### 2. Keyword Search
Full-text search using PostgreSQL BM25 ranking.

```typescript
const results = await client.retrievals.retrieve({
  query: 'neural network',
  mode: 'keyword',
});
```

**Best for**: Exact term matching, specific keywords

### 3. Hybrid Search (Recommended)
Combines semantic + keyword with RRF (Reciprocal Rank Fusion).

```typescript
const results = await client.retrievals.retrieve({
  query: 'transformers architecture',
  mode: 'hybrid',
  rerank: true,  // Optional: apply reranking
});
```

**Best for**: Most use cases, balanced results

### 4. Hierarchical Search
Two-tier search: document-level → chunk-level retrieval.

```typescript
const results = await client.retrievals.retrieve({
  query: 'quantum computing',
  mode: 'hierarchical',
});
```

**Best for**: Large documents, document-aware search

### 5. Graph Search
Knowledge graph traversal using LightRAG.

```typescript
const results = await client.retrievals.retrieve({
  query: 'relationships between concepts',
  mode: 'graph',
});
```

**Best for**: Discovering entity relationships, complex reasoning

### HybridRAG
Combines hybrid search with knowledge graph enhancement.

```typescript
const results = await client.retrievals.retrieve({
  query: 'advanced topic',
  mode: 'hybrid',
  enable_graph: true,  // Add graph enhancement
});
```

**Best for**: Maximum accuracy, context-aware results

## Error Handling

```typescript
import {
  MnemosyneError,
  AuthenticationError,
  NotFoundError,
  ValidationError,
  RateLimitError,
  APIError,
} from '@mnemosyne/sdk';

try {
  const collection = await client.collections.get('invalid_id');
} catch (error) {
  if (error instanceof NotFoundError) {
    console.error('Collection not found');
  } else if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.error('Rate limit exceeded, retry after backoff');
  } else if (error instanceof APIError) {
    console.error(`API error: ${error.message}`);
  }
}
```

## Examples

See the [`examples/`](./examples) directory for complete working examples:

- **[basic-retrieval.ts](./examples/basic-retrieval.ts)** - All 5 search modes + HybridRAG
- **[ingestion-workflow.ts](./examples/ingestion-workflow.ts)** - Complete document ingestion pipeline
- **[video-ingestion.ts](./examples/video-ingestion.ts)** - YouTube and MP4 video processing
- **[streaming-chat.ts](./examples/streaming-chat.ts)** - Real-time SSE streaming chat
- **[async-operations.ts](./examples/async-operations.ts)** - Concurrent operations with Promise.all

### Running Examples

```bash
# Build the SDK
cd sdk-ts
npm install
npm run build

# Set environment variables
export MNEMOSYNE_API_KEY="mn_your_api_key"
export MNEMOSYNE_BASE_URL="http://localhost:8000/api/v1"

# Run an example
node examples/basic-retrieval.js
```

## TypeScript Usage

The SDK is written in TypeScript and includes full type definitions:

```typescript
import type {
  Collection,
  Document,
  RetrievalResult,
  RetrievalMode,
  ProcessingStatus,
} from '@mnemosyne/sdk';

const mode: RetrievalMode = 'hybrid';

const handleResult = (result: RetrievalResult) => {
  result.results.forEach((item) => {
    console.log(item.score, item.content);
  });
};
```

## Async/Await and Concurrency

All methods return Promises and support async/await:

```typescript
// Sequential operations
const collection = await client.collections.create({ name: 'Test' });
const doc1 = await client.documents.create(collection.id, file1);
const doc2 = await client.documents.create(collection.id, file2);

// Concurrent operations (faster)
const [collection] = await Promise.all([
  client.collections.create({ name: 'Test' }),
]);

const [doc1, doc2, doc3] = await Promise.all([
  client.documents.create(collection.id, file1),
  client.documents.create(collection.id, file2),
  client.documents.create(collection.id, file3),
]);
```

## Development

```bash
# Install dependencies
npm install

# Build (TypeScript → JavaScript + types)
npm run build

# Run tests
npm test

# Lint
npm run lint

# Type check
npm run type-check
```

## Requirements

- **Node.js**: 18.0.0 or higher (for native fetch support)
- **Browser**: Modern browsers with fetch API support
- **TypeScript**: 5.0+ (for development)

### Platform Support

| Feature | Node.js | Browser |
|---------|---------|---------|
| All API operations | ✅ | ✅ |
| File upload (File/Blob) | ✅ | ✅ |
| File upload (path string) | ✅ | ❌ |
| SSE streaming | ✅ | ✅ |

**Note:** File path uploads use Node.js `fs/promises` and are not available in browsers. Use `File` objects from `<input type="file">` in browser environments.

## License

MIT

## Links

- [Mnemosyne GitHub](https://github.com/raghavpatnecha/Mnemosyne)
- [Documentation](../../docs/user/README.md)
- [API Reference](../../docs/user/api-reference.md)
- [Python SDK](../sdk/README.md)

## Support

- [GitHub Issues](https://github.com/raghavpatnecha/Mnemosyne/issues)
- [Discussions](https://github.com/raghavpatnecha/Mnemosyne/discussions)
