# TypeScript SDK Implementation Plan

**Status**: Ready for Implementation
**Created**: 2025-11-17
**Purpose**: Comprehensive guide for implementing TypeScript SDK for Mnemosyne RAG API

---

## Overview

This document defines the complete implementation plan for the Mnemosyne TypeScript SDK, mirroring the Python SDK structure while following TypeScript/JavaScript best practices.

## Project Context

### Python SDK Analysis
- **Location**: `/sdk/`
- **Structure**: Resource-based architecture with sync/async clients
- **Key Features**: Type safety (Pydantic), streaming (SSE), retry logic, 5 search modes
- **Dependencies**: httpx, pydantic v2

### TypeScript SDK Goals
- **Zero runtime dependencies** (use native fetch, Node 18+)
- **Full type safety** (TypeScript strict mode)
- **Resource pattern** (mirror Python SDK)
- **Streaming support** (SSE with async generators)
- **Modern tooling** (tsup, vitest, eslint)

---

## Critical Implementation Details

### 1. API Path Prefix
**Backend uses**: `/api/v1` prefix for all routes

**SDK Approach**:
```typescript
// User provides full base URL
const client = new MnemosyneClient({
  baseUrl: 'http://localhost:8000/api/v1',
  apiKey: 'mn_...'
});
```

### 2. Environment Variables
Support same variables as Python SDK:
- `MNEMOSYNE_API_KEY`
- `MNEMOSYNE_BASE_URL`

```typescript
const apiKey = config.apiKey || process.env.MNEMOSYNE_API_KEY;
const baseUrl = config.baseUrl || process.env.MNEMOSYNE_BASE_URL || 'http://localhost:8000/api/v1';
```

### 3. Multipart File Upload (CRITICAL)
Documents endpoint uses `multipart/form-data`:

```typescript
const formData = new FormData();
formData.append('file', fileBlob, filename);
formData.append('collection_id', collectionId);
formData.append('metadata', JSON.stringify(metadata || {})); // ⚠️ JSON-stringified!

// Don't set Content-Type header - let fetch handle it
const response = await fetch(url, {
  method: 'POST',
  body: formData,
  headers: {
    'Authorization': `Bearer ${apiKey}`
    // NO Content-Type header!
  }
});
```

### 4. SSE Streaming Format
Protocol:
```
data: chunk1
data: chunk2
data: [DONE]
```

Parser requirements:
- Strip `data: ` prefix (6 characters)
- Stop on `[DONE]` sentinel
- Handle line buffering correctly

### 5. Auth Endpoint Special Handling
`auth.register()` does NOT require authentication:

```typescript
// Skip auth headers for registration
async register(email: string, password: string) {
  const response = await fetch(`${baseUrl}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // NO Authorization header!
    body: JSON.stringify({ email, password })
  });
}
```

### 6. Complete Type Definitions

**DocumentResponse** (complete fields):
```typescript
interface DocumentResponse {
  id: string;
  collection_id: string;
  user_id: string;
  title?: string;
  filename?: string;
  content_type?: string;        // MIME type
  size_bytes?: number;           // File size
  content_hash: string;          // SHA-256 hash
  unique_identifier_hash?: string; // Source identifier hash
  status: ProcessingStatus;
  metadata: Record<string, any>;
  processing_info?: Record<string, any>;
  created_at: string;            // ISO datetime
  updated_at?: string;
}
```

**RetrievalResponse** (includes processing_time_ms):
```typescript
interface RetrievalResponse {
  query: string;
  mode: string;
  results: ChunkResult[];
  total_results: number;
  processing_time_ms: number;    // ⚠️ Must include!
  graph_enhanced: boolean;
  graph_context?: string;
}
```

### 7. Processing Status Enum
```typescript
type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';
```

### 8. Recent Features (from git log)
- **HybridRAG** (enable_graph parameter)
- **Reranking** (rerank parameter)
- **Query reformulation** (performance optimization)

---

## Directory Structure

```
sdk-ts/
├── src/
│   ├── index.ts                    # Main exports
│   ├── client.ts                   # Main client class
│   ├── base-client.ts              # Base HTTP client logic
│   ├── version.ts                  # Version constant
│   ├── exceptions.ts               # Custom error classes (6 types)
│   ├── streaming.ts                # SSE streaming utilities
│   ├── resources/                  # API resource classes
│   │   ├── index.ts
│   │   ├── auth.ts                 # Auth resource (no auth for register)
│   │   ├── collections.ts          # Collections resource
│   │   ├── documents.ts            # Documents resource (multipart upload!)
│   │   ├── retrievals.ts           # Retrievals resource (5 modes)
│   │   └── chat.ts                 # Chat resource (SSE streaming)
│   └── types/                      # TypeScript types & interfaces
│       ├── index.ts
│       ├── common.ts               # Shared types (Pagination, etc.)
│       ├── auth.ts                 # Auth types
│       ├── collections.ts          # Collection types
│       ├── documents.ts            # Document types (complete!)
│       ├── retrievals.ts           # Retrieval types (with processing_time_ms!)
│       └── chat.ts                 # Chat types
├── examples/                       # Usage examples (mirror Python SDK)
│   ├── basic-retrieval.ts          # All 5 search modes
│   ├── ingestion-workflow.ts       # Complete workflow
│   ├── video-ingestion.ts          # YouTube + MP4
│   ├── streaming-chat.ts           # SSE streaming
│   └── async-operations.ts         # Concurrent operations
├── tests/                          # Test suite
│   ├── unit/
│   │   ├── base-client.test.ts
│   │   ├── collections.test.ts
│   │   ├── documents.test.ts
│   │   ├── retrievals.test.ts
│   │   ├── chat.test.ts
│   │   └── streaming.test.ts
│   └── integration/
│       └── api.test.ts
├── package.json                    # npm config (complete version below)
├── tsconfig.json                   # TypeScript config (strict mode)
├── tsup.config.ts                  # Build config (CJS + ESM)
├── vitest.config.ts                # Testing config
├── .eslintrc.js                    # Linting config
├── .prettierrc                     # Formatting config
├── .gitignore                      # Git ignore
├── .npmignore                      # npm ignore
├── README.md                       # SDK documentation (mirror Python)
└── LICENSE                         # MIT license
```

---

## Implementation Phases

### Phase 1: Project Setup
**Files to create**: package.json, tsconfig.json, tsup.config.ts, vitest.config.ts, .eslintrc.js, .prettierrc, .gitignore, .npmignore

**Tasks**:
- [ ] Initialize npm project with complete package.json
- [ ] Configure TypeScript with strict mode
- [ ] Set up tsup build system (CJS + ESM)
- [ ] Configure ESLint + Prettier
- [ ] Set up Vitest for testing
- [ ] Initialize changesets for version management
- [ ] Add TypeDoc for documentation generation
- [ ] Create .gitignore and .npmignore

**Key Configs**:
```json
// package.json (key fields)
{
  "name": "@mnemosyne/sdk",
  "version": "0.1.0",
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "require": "./dist/index.cjs",
      "import": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  },
  "engines": { "node": ">=18.0.0" }
}
```

### Phase 2: Core Infrastructure
**Files to create**: src/base-client.ts, src/exceptions.ts, src/streaming.ts, src/version.ts

**Tasks**:
- [ ] BaseClient with fetch-based HTTP client
- [ ] Retry logic with exponential backoff (max 3 retries)
- [ ] Error handling and exception mapping (6 exception types)
- [ ] Environment variable support
- [ ] Special handling: Skip auth for /auth/register
- [ ] SSE streaming utility with async generators
- [ ] Version constant export

**BaseClient Features**:
- Automatic retry for 429, 5xx errors
- Exponential backoff: 2^attempt seconds (max 16s)
- Status code → Exception mapping
- Environment variable fallback
- Connection timeout handling

### Phase 3: Type Definitions
**Files to create**: All files in src/types/

**Tasks**:
- [ ] common.ts: Pagination, shared interfaces
- [ ] auth.ts: RegisterRequest, RegisterResponse
- [ ] collections.ts: Create, Update, Response, ListResponse
- [ ] documents.ts: Create, Update, Response, ListResponse, StatusResponse
  - ⚠️ Include: content_hash, unique_identifier_hash, content_type, size_bytes, processing_info
- [ ] retrievals.ts: Request, Response, ChunkResult, DocumentInfo
  - ⚠️ Include: processing_time_ms, graph_enhanced, graph_context
  - RetrievalMode: "semantic" | "keyword" | "hybrid" | "hierarchical" | "graph"
- [ ] chat.ts: Request, Response, SessionResponse, MessageResponse, Source
- [ ] index.ts: Export all types

**Type Safety Requirements**:
- No `any` types (use `unknown` or specific types)
- Strict null checks
- Readonly properties where applicable
- Discriminated unions for status types

### Phase 4: Resources
**Files to create**: All files in src/resources/

**Tasks**:
- [ ] auth.ts: register() with NO authentication
- [ ] collections.ts: create(), list(), get(), update(), delete()
- [ ] documents.ts: create() with multipart/form-data, list(), get(), getStatus(), update(), delete()
  - ⚠️ Multipart upload: FormData + JSON.stringify(metadata)
- [ ] retrievals.ts: retrieve() with all 5 modes, rerank, enable_graph
- [ ] chat.ts: chat() with streaming (async generator), listSessions(), getSessionMessages(), deleteSession()
- [ ] index.ts: Export all resources

**Resource Pattern**:
```typescript
export class CollectionsResource {
  constructor(private client: BaseClient) {}

  async create(params: CollectionCreate): Promise<CollectionResponse> {
    return this.client.request('POST', '/collections', { json: params });
  }

  // ... other methods
}
```

### Phase 5: Main Client
**Files to create**: src/client.ts, src/index.ts

**Tasks**:
- [ ] MnemosyneClient class
- [ ] Initialize all resources
- [ ] Environment variable support
- [ ] Export all types and classes from index.ts

**Client Structure**:
```typescript
export class MnemosyneClient extends BaseClient {
  public readonly auth: AuthResource;
  public readonly collections: CollectionsResource;
  public readonly documents: DocumentsResource;
  public readonly retrievals: RetrievalsResource;
  public readonly chat: ChatResource;

  constructor(config: ClientConfig) {
    super(config);
    this.auth = new AuthResource(this);
    // ... initialize other resources
  }
}
```

### Phase 6: Examples
**Files to create**: All files in examples/

**Tasks**:
- [ ] basic-retrieval.ts - Demonstrate all 5 search modes
- [ ] ingestion-workflow.ts - Complete document ingestion workflow
- [ ] video-ingestion.ts - YouTube and MP4 video processing
- [ ] streaming-chat.ts - Real-time SSE streaming chat
- [ ] async-operations.ts - Concurrent operations with Promise.all

**Example Requirements**:
- Clear comments explaining each step
- Error handling demonstrations
- Environment variable usage
- Complete working examples

### Phase 7: Testing
**Files to create**: All files in tests/

**Tasks**:
- [ ] Unit tests for BaseClient (retry, errors, backoff)
- [ ] Unit tests for all resources
- [ ] Integration tests (mock API responses)
- [ ] SSE streaming tests
- [ ] File upload tests (multipart/form-data)
- [ ] Error handling tests (all 6 exception types)
- [ ] Environment variable tests

**Testing Requirements**:
- 80%+ code coverage
- Mock fetch calls
- Test retry logic
- Test error mapping
- Test streaming parser

### Phase 8: Documentation
**Files to create**: README.md, JSDoc comments

**Tasks**:
- [ ] Complete README.md (mirror Python SDK structure)
- [ ] JSDoc comments for all public APIs
- [ ] Generate TypeDoc documentation
- [ ] Add usage examples to README
- [ ] Document all 5 search modes
- [ ] Document streaming usage
- [ ] Update main project README

**README Sections**:
1. Features
2. Installation
3. Quick Start
4. Core Concepts (Collections, Documents, Retrievals, Chat)
5. Search Modes (all 5)
6. Streaming Chat
7. Error Handling
8. Configuration
9. Examples Reference
10. API Reference

### Phase 9: CI/CD
**Files to create**: .github/workflows/sdk-ts.yml

**Tasks**:
- [ ] GitHub Actions workflow for tests
- [ ] GitHub Actions workflow for publishing
- [ ] Automated type checking
- [ ] Automated linting
- [ ] Coverage reporting
- [ ] Automated releases with tags

**Workflow Triggers**:
- Push to sdk-ts/** paths
- Pull requests
- Tag creation (sdk-ts-v*)

### Phase 10: Publishing
**Tasks**:
- [ ] Publish to npm as @mnemosyne/sdk
- [ ] Create git tag sdk-ts-v0.1.0
- [ ] Update CHANGELOG.md
- [ ] Update main project README
- [ ] Announce release

---

## Configuration Files (Complete)

### package.json (Complete)
```json
{
  "name": "@mnemosyne/sdk",
  "version": "0.1.0",
  "description": "TypeScript SDK for Mnemosyne RAG API - modern, type-safe, fully async",
  "keywords": ["rag", "retrieval", "embeddings", "search", "ai", "ml", "llm", "typescript"],
  "homepage": "https://github.com/raghavpatnecha/Mnemosyne/tree/main/sdk-ts",
  "repository": {
    "type": "git",
    "url": "https://github.com/raghavpatnecha/Mnemosyne.git",
    "directory": "sdk-ts"
  },
  "license": "MIT",
  "author": "Mnemosyne Team <team@mnemosyne.dev>",
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "require": "./dist/index.cjs",
      "import": "./dist/index.js",
      "types": "./dist/index.d.ts"
    },
    "./package.json": "./package.json"
  },
  "files": ["dist", "README.md", "LICENSE"],
  "scripts": {
    "build": "tsup",
    "build:watch": "tsup --watch",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "lint": "eslint src --ext .ts",
    "lint:fix": "eslint src --ext .ts --fix",
    "format": "prettier --write \"src/**/*.ts\" \"examples/**/*.ts\"",
    "format:check": "prettier --check \"src/**/*.ts\" \"examples/**/*.ts\"",
    "typecheck": "tsc --noEmit",
    "docs": "typedoc src/index.ts --out docs",
    "prepublishOnly": "npm run build && npm run test && npm run lint",
    "changeset": "changeset",
    "version": "changeset version",
    "release": "npm run build && changeset publish"
  },
  "dependencies": {},
  "devDependencies": {
    "@changesets/cli": "^2.27.0",
    "@types/node": "^20.10.0",
    "@typescript-eslint/eslint-plugin": "^6.15.0",
    "@typescript-eslint/parser": "^6.15.0",
    "@vitest/coverage-v8": "^1.0.0",
    "eslint": "^8.56.0",
    "eslint-config-prettier": "^9.1.0",
    "prettier": "^3.1.1",
    "tsup": "^8.0.1",
    "typedoc": "^0.25.0",
    "typescript": "^5.3.3",
    "vitest": "^1.0.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```

### tsconfig.json (Production-Ready)
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020"],
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "isolatedModules": true,
    "types": ["node"]
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

### tsup.config.ts
```typescript
import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
  minify: false,
  target: 'es2020',
  outDir: 'dist',
});
```

### vitest.config.ts
```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.test.ts',
        '**/*.config.ts',
      ],
    },
  },
});
```

---

## Key Differences from Python SDK

| Aspect | Python SDK | TypeScript SDK |
|--------|-----------|----------------|
| **HTTP Client** | httpx | Native fetch (Node 18+) |
| **Type System** | Pydantic v2 | TypeScript interfaces |
| **Async Pattern** | Separate AsyncClient | Single client (all async) |
| **Streaming** | Sync/Async generators | Async generators only |
| **Dependencies** | httpx, pydantic | ZERO runtime deps |
| **Build Tool** | Poetry | tsup (bundler) |
| **Testing** | pytest | Vitest |
| **File Upload** | httpx multipart | FormData API |

---

## Validation Checklist

Before starting implementation:

- ✅ All Python SDK features mapped to TypeScript
- ✅ File upload multipart/form-data handling specified
- ✅ SSE streaming protocol documented
- ✅ All type fields included (no missing properties)
- ✅ Environment variable support planned
- ✅ Auth endpoint special case documented
- ✅ Recent features included (HybridRAG, reranking)
- ✅ CI/CD pipeline designed
- ✅ Documentation strategy complete
- ✅ Version management approach decided
- ✅ Zero runtime dependencies confirmed
- ✅ Node.js version specified (18+)

---

## Success Criteria

### Functionality
- [ ] All 5 search modes working (semantic, keyword, hybrid, hierarchical, graph)
- [ ] File upload with multipart/form-data working
- [ ] SSE streaming chat working
- [ ] All CRUD operations working (collections, documents)
- [ ] Error handling with proper exceptions
- [ ] Retry logic with exponential backoff

### Quality
- [ ] 80%+ test coverage
- [ ] Zero TypeScript errors (strict mode)
- [ ] Zero ESLint errors
- [ ] All examples working
- [ ] Documentation complete
- [ ] CI/CD passing

### Publishing
- [ ] Published to npm
- [ ] TypeDoc documentation generated
- [ ] Main README updated
- [ ] Git tag created
- [ ] Changelog updated

---

## Implementation Notes

### Must Remember
1. **Auth endpoint** does NOT require authentication
2. **File upload** uses JSON.stringify(metadata)
3. **SSE streaming** stops on `[DONE]` sentinel
4. **Base URL** includes `/api/v1` prefix
5. **Environment variables** must match Python SDK
6. **Processing time** must be included in retrieval response

### Common Pitfalls to Avoid
- ❌ Don't set Content-Type for multipart uploads
- ❌ Don't forget to strip `data: ` prefix in SSE parser
- ❌ Don't use axios (keep zero dependencies)
- ❌ Don't skip auth headers except for register()
- ❌ Don't forget processing_time_ms in types

---

## Next Steps

1. Use this plan as reference for swarm orchestration
2. Implement phases sequentially
3. Test after each phase
4. Update this document with findings
5. Commit regularly with clear messages

---

**Plan Status**: ✅ APPROVED - Ready for Implementation
**Last Updated**: 2025-11-17
**Maintainer**: Mnemosyne Team
