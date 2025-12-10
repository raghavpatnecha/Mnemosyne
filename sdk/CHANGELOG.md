# Changelog

All notable changes to the Mnemosyne Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Deep reasoning mode for complex multi-step queries
- Answer style presets (concise, detailed, research, technical, creative)
- Document type filtering for specialized search (legal, academic, qa, table)
- Follow-up questions in chat responses
- Media item support in chat (images, tables, figures)
- Multimodal ingestion examples (images, audio, Excel, video)

### Changed
- Enhanced streaming types with reasoning_step and sub_query events

## [0.1.0] - 2024-12-06

### Added
- Initial release of Mnemosyne Python SDK
- `Client` - Synchronous HTTP client
- `AsyncClient` - Asynchronous HTTP client with context manager support
- Collections resource: create, list, get, update, delete
- Documents resource: create (upload), list, get, get_status, update, delete
- Retrievals resource: retrieve with 5 search modes
  - Semantic search (embedding-based)
  - Keyword search (BM25)
  - Hybrid search (RRF fusion)
  - Hierarchical search (document-then-chunk)
  - Graph search (LightRAG)
- Chat resource with SSE streaming support
  - Real-time token streaming
  - Multi-turn conversations with session management
  - Source attribution
- Authentication with API key support
- Automatic retry with exponential backoff
- Comprehensive error handling (AuthenticationError, NotFoundError, ValidationError, RateLimitError)
- Full type annotations with Pydantic v2
- 10 usage examples covering all features
- LangChain integration example

### Documentation
- Complete README with all features documented
- Examples for all major use cases
- Type definitions for all API responses

[Unreleased]: https://github.com/raghavpatnecha/Mnemosyne/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/raghavpatnecha/Mnemosyne/releases/tag/v0.1.0
