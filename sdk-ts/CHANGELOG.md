# Changelog

All notable changes to the Mnemosyne TypeScript SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial TypeScript SDK implementation (Phases 1-10)
- Core infrastructure:
  - BaseClient with retry logic and exponential backoff
  - Custom exception types (6 error classes)
  - SSE streaming parser for real-time chat
  - Version tracking
- Resource classes:
  - AuthResource (user registration)
  - CollectionsResource (full CRUD)
  - DocumentsResource (upload, list, status, delete)
  - RetrievalsResource (5 search modes + HybridRAG)
  - ChatResource (streaming/non-streaming chat, session management)
- Complete type definitions:
  - Auth types
  - Collection types
  - Document types (with processing status)
  - Retrieval types (all 5 modes)
  - Chat types (messages, sessions)
  - Shared types (pagination, metadata)
- 5 working examples:
  - basic-retrieval.ts (all search modes)
  - ingestion-workflow.ts (complete pipeline)
  - video-ingestion.ts (YouTube + MP4)
  - streaming-chat.ts (SSE chat + sessions)
  - async-operations.ts (Promise.all patterns)
- Comprehensive test suite:
  - 66 total tests (46 passing)
  - Unit tests for all resources
  - Unit tests for BaseClient
  - Unit tests for SSE streaming
  - Integration tests
- Documentation:
  - Complete README.md (460+ lines)
  - API reference for all resources
  - All 5 search modes documented
  - Error handling guide
  - TypeScript usage examples
  - Async/await patterns
- CI/CD pipeline:
  - GitHub Actions workflow
  - Multi-version Node.js testing (18, 20, 22)
  - Cross-platform builds (Ubuntu, macOS, Windows)
  - Type checking, linting, testing
  - Coverage reporting
  - Package validation

### Features
- **Zero Dependencies**: Uses native fetch API (Node 18+)
- **Full TypeScript Support**: Strict mode with comprehensive types
- **Streaming Chat**: Real-time SSE streaming with async generators
- **Multipart Uploads**: File uploads with JSON-stringified metadata
- **Automatic Retries**: Exponential backoff (2^n seconds, max 16s)
- **5 Search Modes**: Semantic, keyword, hybrid, hierarchical, graph
- **HybridRAG**: Knowledge graph-enhanced hybrid search
- **Dual Format**: CommonJS and ES Module support
- **Timeout Support**: Configurable request timeouts with AbortController
- **Error Mapping**: Status codes mapped to typed exceptions

### Technical Details
- **Build System**: tsup for dual-format output
- **Testing**: Vitest with coverage reporting
- **Linting**: ESLint with strict TypeScript rules
- **Type Checking**: TypeScript 5+ with strict mode
- **Node Requirement**: 18.0.0 or higher
- **Base URL Handling**: Automatic trailing slash for correct URL resolution
- **Path Construction**: Relative paths without leading slashes

## [0.1.0] - 2025-01-XX (Upcoming)

### Added
- Initial public release
- Complete TypeScript SDK for Mnemosyne RAG platform
- Production-ready with full type safety
- Comprehensive documentation and examples
- Automated CI/CD with GitHub Actions

### Breaking Changes
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Security
- SHA-256 hashed API keys
- Bearer token authentication
- No sensitive data logging

---

## Development Notes

### Version History
- **Phase 1-5**: Core implementation (client, types, resources)
- **Phase 6**: Example files (5 working examples)
- **Phase 7**: Test suite (66 tests, 46 passing)
- **Phase 8**: Documentation (README, API reference)
- **Phase 9**: CI/CD (GitHub Actions workflow)
- **Phase 10**: Publishing preparation (CHANGELOG, LICENSE, README updates)

### Upgrade Guide
N/A (initial release)

### Migration from Python SDK
See [Python SDK](../sdk/README.md) for comparison. Key differences:
- Timeout in milliseconds (TypeScript) vs seconds (Python)
- Async generators for streaming (TypeScript) vs iterators (Python)
- `apiKey` camelCase (TypeScript) vs `api_key` snake_case (Python)
- Base URL must include `/api/v1` suffix

---

[Unreleased]: https://github.com/raghavpatnecha/Mnemosyne/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/raghavpatnecha/Mnemosyne/releases/tag/v0.1.0
