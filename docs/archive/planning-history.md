# Planning History

Chronological record of project planning, roadmaps, and strategic decisions.

---

## Phase 2: Advanced Features (2025-10 - 2025-11)

**Goal**: Transform Mnemosyne from basic RAG to production-grade platform

### Week 5 - Performance & Graph Enhancement
**Focus**: HybridRAG implementation
- Add `enable_graph` parameter for graph enhancement
- Parallel execution of base search + LightRAG
- Research-backed: 35-80% accuracy improvement for complex queries
- Remove silent fallbacks, enforce fail-fast

**Delivered**:
- ✅ HybridRAG with parallel execution
- ✅ Fail-fast enforcement
- ✅ Critical bug fixes (dict mutation, None crashes, top_k)
- ✅ Updated docs (API reference, architecture, configuration)

---

### Week 4 - Optimization & Hidden Gems
**Focus**: Activate implemented but unused features
- Search results caching (50-70% faster)
- Query reformulation (10-15% better quality)
- Reranker integration (15-25% accuracy)
- Singleton services (eliminate overhead)

**Delivered**:
- ✅ Redis caching for search results
- ✅ Query reformulation with LLM
- ✅ Connected reranker to API
- ✅ Singleton pattern for services
- ✅ Fixed timeout and separator bugs

---

### Week 3 - LightRAG Source Extraction
**Focus**: Real citations for graph mode
- Extract actual chunk IDs from PostgreSQL
- Consistent response format across all modes
- Semantic search for source chunks

**Delivered**:
- ✅ `_extract_source_chunks()` implementation
- ✅ Real chunk IDs and document references
- ✅ Updated docs and architecture

---

### Week 2 - Video Processing
**Focus**: Multi-format video support
- Frame extraction (sampling, scene detection)
- Audio extraction and transcription
- Metadata extraction (resolution, codec)
- Format support: MP4, AVI, MOV, MKV, WebM

**Delivered**:
- ✅ VideoParser with OpenCV and FFmpeg
- ✅ Whisper integration for audio
- ✅ Frame sampling and scene detection
- ✅ Comprehensive tests

---

### Week 1 - Format Support Expansion
**Focus**: Beyond text/PDF parsers
- Image: OCR with Tesseract
- Documents: DOCX, PPTX, XLSX
- Web: HTML, JSON, CSV, XML
- Code: Python, JavaScript, Java, Go

**Delivered**:
- ✅ 15+ format parsers
- ✅ Unified parser interface
- ✅ Format detection
- ✅ Error handling

---

## Phase 1: Core Platform (2025-08 - 2025-09)

**Goal**: Build MVP RAG-as-a-Service platform

### Core Features Implemented
- ✅ FastAPI backend with async support
- ✅ PostgreSQL + pgvector for vector storage
- ✅ 5 search modes (semantic, keyword, hybrid, hierarchical, graph)
- ✅ LightRAG integration
- ✅ Document chunking pipeline
- ✅ Celery for async processing
- ✅ Authentication with API keys
- ✅ Multi-tenancy (collections)

### API Endpoints
- ✅ Collections API (CRUD)
- ✅ Documents API (upload, process, CRUD)
- ✅ Retrievals API (5 modes, reranking)
- ✅ Chat API (streaming, history)

### SDK Development
- ✅ Sync and async clients
- ✅ Type-safe schemas
- ✅ Resource pattern
- ✅ Examples and tests

### Infrastructure
- ✅ Docker deployment
- ✅ PostgreSQL, Redis, Celery setup
- ✅ Volume persistence
- ✅ Health checks

---

## Reference Analysis

### SurfSense Study (2025-09)
**Learnings**:
- Hybrid search (semantic + keyword with RRF) as default
- Two-tier hierarchical retrieval
- Reranking instead of ensemble mode
- No LightRAG (pure vector/keyword)

**Decisions**:
- Adopt hybrid as recommended mode
- Implement reranking (Flashrank, Cohere, Jina, Voyage, Mixedbread)
- Add HybridRAG (our innovation: hybrid + graph)
- Keep separate graph mode for power users

---

### Industry Research (2025-11)
**HybridRAG Papers**:
- AWS GraphRAG blog: 35% precision improvement
- Lettria: 50% → 80% correctness with hybrid approach
- Cedars-Sinai AlzKB: Memgraph + vector for Alzheimer's research
- HybridRAG paper (arxiv.org/abs/2408.04948)

**Decisions**:
- Implement parallel execution (not sequential)
- Fail-fast when graph requested but unavailable
- Provide both `mode="graph"` and `enable_graph=True`
- Document performance trade-offs (1.5-2x latency)

---

## Technical Roadmap Decisions

### Database
**Decision**: PostgreSQL + pgvector
**Alternatives Considered**: Pinecone, Weaviate, Qdrant
**Rationale**: Simplicity, SQL familiarity, cost-effective, self-hostable

### Vector Dimensions
**Decision**: 1536 (OpenAI text-embedding-3-large)
**Alternatives**: 384 (small), 3072 (large)
**Rationale**: Balance between quality and storage

### LLM Provider
**Decision**: LiteLLM
**Alternatives**: Direct OpenAI, direct Anthropic
**Rationale**: 150+ model support, provider flexibility, cost optimization

### Graph RAG
**Decision**: LightRAG
**Alternatives**: Microsoft GraphRAG, custom
**Rationale**: 99% token reduction, built-in entity extraction, incremental updates

### Async Processing
**Decision**: Celery
**Alternatives**: RQ, Dramatiq, FastAPI BackgroundTasks
**Rationale**: Battle-tested, scalability, monitoring tools

---

## Feature Prioritization

### Must-Have (Phase 1)
1. Core RAG (embedding, chunking, retrieval)
2. Multi-mode search
3. API authentication
4. Document management
5. Chat interface

### Should-Have (Phase 2)
1. Multi-format support ✅
2. Reranking ✅
3. Caching ✅
4. Query reformulation ✅
5. Graph enhancement ✅

### Nice-to-Have (Future)
1. Multi-user organizations
2. Usage analytics
3. Custom embedding models
4. Batch processing
5. Advanced monitoring

---

## Architecture Evolution

### v0.1 (Initial)
- Basic semantic search
- Single file type (TXT)
- Synchronous processing
- No caching

### v0.5 (Phase 1 Complete)
- 5 search modes
- PDF + text support
- Async with Celery
- LightRAG integration

### v1.0 (Phase 2 Complete)
- 15+ file formats
- HybridRAG (graph + vector)
- 3-layer caching
- Query reformulation
- Reranking (5 providers)

### v1.5 (Planned)
- Organizations & teams
- Usage quotas
- Custom models
- Analytics dashboard
- Advanced monitoring

---

## Lessons from Planning

1. **Research before implementation**: HybridRAG research saved 2-3x latency
2. **Audit existing code**: Found reranker already implemented
3. **Fail-fast over fallbacks**: Better UX, easier debugging
4. **Keep docs under 300 lines**: Maintainability matters
5. **Phase planning works**: Delivered on schedule
6. **User feedback critical**: Guided feature prioritization

---

## Future Roadmap

### Short-Term (Q1 2025)
- Multi-user organizations
- Usage analytics and quotas
- Custom embedding models
- Batch document processing

### Medium-Term (Q2 2025)
- Advanced monitoring and alerting
- Multi-language support
- Custom reranking models
- Performance benchmarking tools

### Long-Term (Q3+ 2025)
- Enterprise features (SSO, RBAC)
- Advanced graph operations
- Model fine-tuning
- Managed hosting option

---

**Last Updated**: 2025-11-17
**Phases Completed**: 2/2
**Features Delivered**: 25+
**On Schedule**: ✅ Yes
