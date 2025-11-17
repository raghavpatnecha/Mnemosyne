# TypeScript SDK Guide

The Mnemosyne TypeScript SDK provides a clean, type-safe interface to interact with the Mnemosyne RAG API from Node.js and browser environments.

## 📦 Installation

```bash
npm install @mnemosyne/sdk
# or
yarn add @mnemosyne/sdk
# or
pnpm add @mnemosyne/sdk
```

## 📚 Complete Documentation

For the complete SDK documentation, see:

**👉 [TypeScript SDK README](../../sdk-ts/README.md)**

The SDK README includes:
- ✅ Installation instructions
- ✅ Quick start guide
- ✅ All 5 search modes (semantic, keyword, hybrid, hierarchical, graph)
- ✅ Streaming chat examples
- ✅ Platform support (Node.js & Browser)
- ✅ Error handling
- ✅ Configuration options
- ✅ API reference

## 🎯 Quick Examples

### Basic Usage

```typescript
import { MnemosyneClient } from '@mnemosyne/sdk';

// Initialize
const client = new MnemosyneClient({
  apiKey: process.env.MNEMOSYNE_API_KEY,
});

// Create collection
const collection = await client.collections.create({
  name: 'My Documents',
  description: 'Research papers',
});

// Upload document
const doc = await client.documents.create(
  collection.id,
  './document.pdf',
  { topic: 'AI' }
);

// Search
const results = await client.retrievals.retrieve({
  query: 'What is this about?',
  mode: 'hybrid',
  top_k: 10,
});
```

### Streaming Chat

```typescript
// Stream chat responses
for await (const chunk of client.chat.chat({
  message: 'Explain the key concepts',
  collection_id: collection.id,
  stream: true,
})) {
  process.stdout.write(chunk);
}
```

## 🌐 Platform Support

| Feature | Node.js | Browser |
|---------|---------|---------|
| All API operations | ✅ | ✅ |
| File upload (File/Blob) | ✅ | ✅ |
| File upload (path string) | ✅ | ❌ |
| SSE streaming | ✅ | ✅ |

## 📖 Key Features

- **Zero Dependencies**: Uses native `fetch` API (Node.js 18+)
- **Full TypeScript Support**: Strict typing with comprehensive definitions
- **Dual Format**: CommonJS and ES Module support
- **Automatic Retries**: Exponential backoff for failed requests
- **5 Search Modes**: Semantic, keyword, hybrid, hierarchical, and graph
- **HybridRAG**: Knowledge graph-enhanced retrieval
- **Streaming**: Real-time SSE (Server-Sent Events) streaming

## 🔗 Related Documentation

- [Python SDK Guide](./sdk-guide.md) - Python SDK documentation
- [API Reference](./api-reference.md) - Complete API documentation
- [Getting Started](./getting-started.md) - Platform setup guide
- [Architecture](./architecture.md) - System architecture overview

## 💡 Need Help?

- **GitHub Issues**: [Report bugs or request features](https://github.com/raghavpatnecha/Mnemosyne/issues)
- **SDK README**: [Complete TypeScript SDK documentation](../../sdk-ts/README.md)
- **Python SDK**: [Python SDK guide](./sdk-guide.md) for Python users
