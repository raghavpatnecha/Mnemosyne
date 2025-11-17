# Mnemosyne Documentation

Welcome to Mnemosyne - an open-source RAG-as-a-Service platform.

## Quick Links

- [Main README](../README.md) - Project overview and quick start
- [Python SDK](../sdk/README.md) - Python SDK documentation
- [TypeScript SDK](../sdk-ts/README.md) - TypeScript SDK documentation
- [API Documentation](https://api.mnemosyne.dev/docs) - Interactive API docs

## User Documentation

For users of the Mnemosyne platform:

- **[Getting Started](user/getting-started.md)** - Quick start guide and basic usage
- **[Python SDK Guide](user/sdk-guide.md)** - Python SDK installation and usage ⭐
- **[TypeScript SDK Guide](user/sdk-typescript-guide.md)** - TypeScript SDK installation and usage ⭐
- **[Configuration Guide](user/configuration.md)** - Environment variables and setup
- **[API Reference](user/api-reference.md)** - Complete API specification
- **[Architecture](user/architecture.md)** - System architecture overview
- **[Deployment Guide](user/deployment.md)** - Production deployment instructions
- **[Deployment Options](user/deployment-options.md)** - Different deployment strategies

## Developer Documentation

For contributors and developers:

- **[Product Requirements](developer/product-requirements.md)** - PRD and vision
- **[TypeScript SDK Plan](developer/typescript-sdk-plan.md)** - TypeScript SDK implementation
- **[Research](developer/research.md)** - Initial research and analysis
- **[Setup Guide](developer/setup.md)** - Development environment setup
- **[Reference Analysis](developer/reference-analysis.md)** - Technical reference docs

## SDK Documentation

Official SDKs for interacting with Mnemosyne API:

### Python SDK
- **[Python SDK Guide](user/sdk-guide.md)** - Quick SDK reference (start here!)
- **[Full Python SDK Docs](../sdk/README.md)** - Complete SDK documentation
- **[SDK Examples](../sdk/examples/)** - 6 working code examples
  - `basic_retrieval.py` - All 5 search modes
  - `ingestion_workflow.py` - Document upload workflow
  - `streaming_chat.py` - Real-time chat
  - `async_streaming.py` - Async/await usage
  - `video_ingestion.py` - YouTube & MP4 videos
  - `langchain_integration.py` - LangChain integration

### TypeScript SDK
- **[TypeScript SDK Guide](user/sdk-typescript-guide.md)** - Quick SDK reference (start here!)
- **[Full TypeScript SDK Docs](../sdk-ts/README.md)** - Complete SDK documentation
- **Platform Support**: Node.js 18+ and modern browsers
- **Features**: Zero dependencies, full TypeScript support, streaming, dual format (CJS/ESM)

## Archive

Historical documentation from the development process:

- **[Planning](archive/planning/)** - Weekly and phase-based implementation plans
- **[Implementation](archive/implementation/)** - Implementation summaries and reports
- **[Verification](archive/verification/)** - Code reviews and validation reports

## Project Structure

```
mnemosyne/
├── backend/         # FastAPI backend (RAG-as-a-Service)
├── src/            # Legacy Medium articles search (deprecated)
├── sdk/            # Python SDK
├── sdk-ts/         # TypeScript SDK
├── docs/           # Documentation (you are here)
├── examples/       # Usage examples
└── tests/          # Test suites
```

## Key Concepts

### Collections
Logical groupings of documents. Each user can create multiple collections to organize their content.

### Documents
Files (PDF, DOCX, MP4, YouTube) uploaded to collections. Documents are processed, chunked, and indexed.

### Search Modes
- **Semantic**: Vector similarity search
- **Keyword**: BM25 full-text search
- **Hybrid**: Combined semantic + keyword (recommended)
- **Hierarchical**: Two-tier document → chunk retrieval
- **Graph**: LightRAG knowledge graph search

### Chat
Conversational AI with RAG-powered responses. Supports streaming and multi-turn conversations.

## Technology Stack

- **API**: FastAPI + Pydantic + SQLAlchemy
- **Database**: PostgreSQL 16 + pgvector
- **Search**: LightRAG + hybrid search + reranking
- **Processing**: Celery + Redis + Docling + Chonkie
- **LLM**: LiteLLM (150+ models supported)
- **Embeddings**: OpenAI text-embedding-3-large

## Getting Help

- **Documentation**: You're reading it!
- **API Docs**: https://api.mnemosyne.dev/docs
- **Issues**: https://github.com/raghavpatnecha/Mnemosyne/issues
- **Discussions**: https://github.com/raghavpatnecha/Mnemosyne/discussions

## Contributing

See [CLAUDE.md](../CLAUDE.md) for development guidelines and best practices.

## License

MIT License - see [LICENSE](../LICENSE) file for details.
