# Mnemosyne Universal RAG - Research & Implementation Plan

**Date:** 2025-11-14
**Objective:** Transform Mnemosyne from a Medium-article-only search system into a universal RAG platform supporting all content types (documents, images, videos, audio, code, etc.)

---

## Executive Summary

Based on analysis of 5 leading RAG implementations (SurfSense, RAG-Anything, Pathway, Airweave, LightRAG, GraphRAG) and the current Mnemosyne architecture, this plan outlines a phased approach to building a production-ready universal RAG system.

**Key Decision:** Adopt **LightRAG + RAG-Anything** hybrid architecture for optimal balance of:
- Graph-based retrieval (99% token reduction vs GraphRAG)
- Multimodal support (50+ file formats)
- Cost efficiency (single API call retrieval)
- Real-time performance

---

## Current State Analysis

### Existing Mnemosyne Architecture

**Backend:**
- FastAPI/Quart dual server setup
- MongoDB + pgvector for vector storage
- LangChain orchestration (OpenAI + Ollama strategies)
- Streaming SSE responses (sync/async modes)
- Service layer: MnemsoyneService, LLMService, MongoService

**Frontend:**
- Chat interface with streaming support ✓
- Follow-up questions ✓
- Image display ✓
- Sources/citations ✓
- Markdown rendering ✓
- **Missing:** File upload UI

**Limitations:**
- Medium articles only (single domain)
- Text-only retrieval
- No multimodal understanding
- Flat vector search (no graph relationships)
- Manual data ingestion via Firecrawl

---

## Research Findings: RAG System Comparison

### 1. SurfSense (NotebookLM Clone)

**Architecture:**
- FastAPI + PostgreSQL (pgvector) + Celery + Redis
- Next.js 15 frontend with Vercel AI SDK
- LlamaCloud/Unstructured.io/Docling for parsing
- Hybrid search (semantic + full-text with RRF)

**Strengths:**
- 50+ file format support (PDF, Office, audio, video)
- Hierarchical indices (two-tier RAG)
- Podcast generation (3min in 20sec)
- Multiple rerankers (Pinecone, Cohere, Flashrank)
- Chonkie chunking with LateChunker optimization

**Tech Stack Insights:**
- PostgreSQL pgvector (mature, production-ready)
- Temporal for workflow orchestration
- Strong multimodal parsing layer

**Adoption Considerations:**
- Heavy infrastructure (requires Celery, Redis, Temporal)
- Focused on document processing over graph reasoning
- Frontend is React-based (we have vanilla JS)

---

### 2. RAG-Anything (Multimodal Specialist)

**Architecture:**
- Built on top of LightRAG
- MinerU + Docling for document parsing
- Concurrent text/multimodal processing pipelines
- VLM integration for image understanding

**Strengths:**
- Seamless multimodal handling (text, images, tables, equations)
- Direct content injection (bypass parsing when needed)
- Knowledge graph construction with cross-modal relationships
- Modality-aware retrieval (vector + graph traversal)

**Tech Stack Insights:**
- Text-embedding-3-large (3072 dimensions)
- GPT-4o/4o-mini for LLM
- Autonomous content categorization

**Adoption Considerations:**
- **Best choice for multimodal content**
- Integrates with LightRAG (synergistic)
- Handles complex documents (PDFs with mixed content)

---

### 3. Pathway (Real-Time Streaming RAG)

**Architecture:**
- Rust-based differential dataflow engine
- In-memory real-time vector index
- 300+ data source connectors (Airbyte)
- Unified batch-and-streaming architecture

**Strengths:**
- Live document updates (no batch delays)
- Incremental computation
- Native Kafka/PostgreSQL/SharePoint connectors
- Superior performance vs Flink/Spark/Kafka Streaming

**Tech Stack Insights:**
- LangChain/LlamaIndex integration
- Handles late/out-of-order data points
- Stateful transformations (joins, windowing)

**Adoption Considerations:**
- Overkill for MVP (enterprise-grade streaming)
- Consider for Phase 3 (live data sources)
- Good fit if we need real-time Medium article updates

---

### 4. Airweave (Context Retrieval Layer)

**Architecture:**
- FastAPI + PostgreSQL + Qdrant (vectors)
- 30+ app integrations (Slack, Notion, GitHub, etc.)
- MCP (Model Context Protocol) server
- Multi-tenant with OAuth2

**Strengths:**
- Production-ready connectors
- Incremental updates via content hashing
- Entity extraction & transformation
- REST API + MCP interfaces

**Tech Stack Insights:**
- Temporal for workflows
- Redis pub/sub
- Docker Compose + Kubernetes deployment

**Adoption Considerations:**
- Strong for SaaS integrations
- Less focus on multimodal content
- Infrastructure complexity high

---

### 5. LightRAG (Graph-Enhanced Retrieval)

**Architecture:**
- Graph-based text indexing
- Dual-level retrieval (low-level + high-level queries)
- Knowledge graph with entities/relationships
- Incremental updates (no full reindexing)

**Strengths:**
- **99% token reduction** vs GraphRAG (100 vs 600-10K tokens)
- **Single API call** retrieval (GraphRAG needs multiple)
- **86.4% better performance** in complex domains
- Handles both specific ("Who wrote X?") and abstract queries
- **Scalable** (incremental updates)

**Recent 2025 Features:**
- RAG-Anything multimodal integration ✓
- Reranker support ✓
- RAGAS evaluation framework ✓
- Langfuse observability ✓

**Tech Stack Insights:**
- Graph structure preserves relationships
- Lower retrieval overhead than community-based traversal
- Cost-effective (fewer tokens = lower API costs)

**Adoption Considerations:**
- **Top choice for core RAG engine**
- Proven performance gains
- Active development (2025 updates)
- Integrates with RAG-Anything for multimodal

---

### 6. GraphRAG (Microsoft Research)

**Architecture:**
- LLM-generated knowledge graph
- Community detection (Leiden algorithm)
- Hierarchical community summaries
- Map-reduce parallel query execution

**Strengths:**
- Excellent for dataset-wide aggregation queries
- Structured information retrieval
- Reveals dataset themes/structure
- Azure-hosted solution accelerator

**Tech Stack Insights:**
- Community-based approach
- Pre-summarized semantic clusters
- Graph + LLM fusion

**Adoption Considerations:**
- **High cost** (600-10K tokens per retrieval)
- **Multiple API calls** needed
- Overkill for general Q&A
- Better for analytical queries over large corpora
- LightRAG outperforms in most use cases

---

## Recommended Architecture: Hybrid LightRAG + RAG-Anything

### Core Decision Rationale

**Why LightRAG as Foundation:**
1. **Cost Efficiency:** 99% token reduction = lower API costs
2. **Performance:** 86.4% better in complex queries
3. **Scalability:** Incremental updates, no reindexing
4. **Single Call:** One API call vs multiple (GraphRAG)
5. **Dual-Level:** Handles both specific and abstract queries

**Why Add RAG-Anything:**
1. **Multimodal Support:** Text, images, tables, equations, videos
2. **Synergy:** Built on LightRAG (seamless integration)
3. **Content Categorization:** Autonomous routing
4. **VLM Integration:** Vision language models for images

**Why NOT GraphRAG:**
- 10x more expensive (600-10K tokens)
- Multiple API calls (latency)
- LightRAG achieves better results with less cost

**Why NOT SurfSense as Base:**
- Too heavy (Celery, Redis, Temporal)
- Over-engineered for MVP
- Can adopt specific components (Chonkie chunking, rerankers)

**Why NOT Pathway (for now):**
- Real-time streaming unnecessary for MVP
- Consider Phase 3 for live feeds
- Current batch ingestion sufficient

**Why NOT Airweave as Core:**
- Focused on SaaS integrations
- Weak multimodal support
- Can borrow connector patterns

---

## Proposed Tech Stack

### Backend Services

**Core RAG Engine:**
```
LightRAG (graph-based retrieval)
  └── RAG-Anything (multimodal processing)
      ├── MinerU (document parsing)
      ├── Docling (privacy-focused, no API keys)
      └── VLM (image understanding)
```

**Database Layer:**
```
PostgreSQL + pgvector (mature, production-ready)
  ├── Vector embeddings (text-embedding-3-large, 3072d)
  ├── Knowledge graph (entities, relationships)
  └── Metadata (file info, sources, timestamps)
```

**API Framework:**
```
FastAPI (async, high-performance)
  ├── Streaming SSE responses
  ├── File upload endpoints
  ├── Chat/query endpoints
  └── Admin/management APIs
```

**Task Queue (Optional for Phase 2):**
```
Celery + Redis
  ├── Async document processing
  ├── Batch ingestion
  └── Background reindexing
```

**LLM Integration:**
```
LangChain (existing)
  ├── OpenAI (GPT-4o-mini, GPT-4)
  ├── Ollama (local models)
  └── Strategy pattern (extensible)
```

**Document Processing Pipeline:**
```
Chonkie (SurfSense chunking)
  ├── LateChunker (embedding-aware)
  ├── Semantic chunking
  └── Adaptive chunk sizes
```

**Reranking Layer:**
```
Flashrank (lightweight, local)
  OR
Cohere Rerank API (cloud, accurate)
```

**Embedding Models:**
```
text-embedding-3-large (OpenAI, 3072d)
  OR
sentence-transformers (local, privacy)
```

### Frontend Enhancements

**Existing (Keep):**
- Vanilla JS + marked.js + highlight.js
- SSE streaming support
- Chat interface
- Follow-up questions UI

**New Components:**
```
File Upload UI
  ├── Drag & drop zone
  ├── Multi-file selection
  ├── Progress indicators
  ├── File type icons
  └── Upload queue management

Content Management
  ├── Document library view
  ├── Delete/archive files
  ├── Tag/categorize content
  └── Search within documents

Multimodal Display
  ├── Image preview in results
  ├── Video thumbnails
  ├── Audio player embeds
  └── PDF viewer integration
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Replace MongoDB with PostgreSQL + pgvector, integrate LightRAG

**Tasks:**
1. **Database Migration**
   - Set up PostgreSQL with pgvector extension
   - Migrate schema from MongoDB
   - Create vector indices
   - Implement connection pooling

2. **LightRAG Integration**
   - Install LightRAG library
   - Configure knowledge graph storage
   - Set up entity extraction
   - Implement dual-level retrieval

3. **Backend Refactoring**
   - Update MongoService → PostgresService
   - Integrate LightRAG into MnemsoyneService
   - Maintain LLMService strategy pattern
   - Update API endpoints

4. **Testing**
   - Migrate existing Medium articles
   - Compare retrieval quality vs old system
   - Benchmark query performance
   - Validate graph relationships

**Deliverables:**
- Working LightRAG-based system
- PostgreSQL fully operational
- Parity with existing functionality

---

### Phase 2: Multimodal Support (Weeks 3-4)

**Goal:** Add file upload and multimodal content processing

**Tasks:**
1. **RAG-Anything Integration**
   - Install RAG-Anything + MinerU + Docling
   - Configure multimodal pipelines
   - Set up VLM for image analysis
   - Implement content categorization

2. **Document Processing**
   - Integrate Chonkie chunking
   - Support 50+ file formats
   - Extract text from PDFs, Office files
   - Transcribe audio/video (Whisper API)
   - OCR for images

3. **File Upload System**
   - Create upload API endpoints
   - Implement file validation
   - Add background processing (Celery)
   - Store files in S3/local storage
   - Track processing status

4. **Frontend File Upload**
   - Drag & drop UI component
   - Multi-file selector
   - Upload progress bars
   - File type indicators
   - Error handling

**Deliverables:**
- Upload and process PDFs, Word docs, images, videos
- Multimodal content in knowledge graph
- Frontend file management UI

---

### Phase 3: Advanced Features (Weeks 5-6)

**Goal:** Reranking, citations, and UX polish

**Tasks:**
1. **Reranking Layer**
   - Integrate Flashrank (local) or Cohere (API)
   - Implement RRF (Reciprocal Rank Fusion)
   - A/B test reranker impact
   - Optimize for accuracy vs latency

2. **Enhanced Citations**
   - Highlight source passages
   - Link to specific document pages
   - Show confidence scores
   - Display entity relationships

3. **Content Management**
   - Document library view
   - Delete/archive documents
   - Tag and categorize files
   - Search within uploaded content

4. **Observability**
   - Langfuse integration
   - Query analytics
   - Cost tracking (API usage)
   - Performance monitoring

**Deliverables:**
- Improved retrieval accuracy with reranking
- Better citation tracking
- Content management dashboard

---

### Phase 4: Optimization & Scale (Weeks 7-8)

**Goal:** Production-ready performance and deployment

**Tasks:**
1. **Performance Optimization**
   - Index tuning (pgvector HNSW)
   - Caching layer (Redis)
   - Query optimization
   - Batch processing improvements

2. **Real-Time Updates (Optional)**
   - Consider Pathway integration
   - Live document watching
   - Incremental graph updates
   - Webhook support

3. **Deployment**
   - Docker Compose setup
   - Kubernetes manifests (optional)
   - Environment configuration
   - CI/CD pipeline

4. **Testing & QA**
   - Load testing
   - Integration tests
   - E2E test suite
   - Documentation

**Deliverables:**
- Production-ready system
- Deployment artifacts
- Comprehensive tests
- User documentation

---

## File Structure (Proposed)

```
mnemosyne/
├── src/
│   ├── api/
│   │   ├── upload.py          # File upload endpoints
│   │   ├── search.py          # Query/chat endpoints (updated)
│   │   ├── manage.py          # Content management
│   │   └── health.py          # Health checks
│   ├── service/
│   │   ├── lightrag_service.py       # LightRAG integration
│   │   ├── rag_anything_service.py   # Multimodal processing
│   │   ├── postgres_service.py       # PostgreSQL operations
│   │   ├── llm_service.py            # Existing LLM strategies
│   │   ├── chunking_service.py       # Chonkie integration
│   │   ├── reranker_service.py       # Reranking layer
│   │   └── file_processor.py         # Document parsing
│   ├── model/
│   │   ├── document.py        # Document models
│   │   ├── graph.py           # Knowledge graph models
│   │   └── embedding.py       # Embedding utilities
│   ├── tasks/
│   │   ├── celery_app.py      # Celery configuration
│   │   ├── process_document.py # Async processing
│   │   └── index_document.py   # Indexing tasks
│   ├── static/
│   │   ├── js/
│   │   │   ├── script.js      # Existing chat logic
│   │   │   ├── upload.js      # File upload UI
│   │   │   └── library.js     # Document library
│   │   └── css/
│   └── templates/
│       ├── index.html         # Updated with upload UI
│       └── library.html       # Document management page
├── tests/
│   ├── unit/
│   │   ├── test_lightrag_service.py
│   │   ├── test_rag_anything_service.py
│   │   └── test_file_processor.py
│   ├── integration/
│   │   ├── test_multimodal_pipeline.py
│   │   └── test_upload_flow.py
│   └── e2e/
│       └── test_full_workflow.py
├── migrations/           # Database migrations
├── docker/              # Docker configs
├── .claude/
│   └── skills/          # Memory & swarm skills
├── CLAUDE.md            # Development guidelines
├── RESEARCH_PLAN.md     # This document
├── requirements.txt
└── docker-compose.yml
```

---

## API Endpoints (New/Updated)

### Upload & Management

```
POST   /api/v1/upload                # Upload files
GET    /api/v1/documents              # List uploaded docs
DELETE /api/v1/documents/{id}         # Delete document
GET    /api/v1/documents/{id}/status  # Processing status
POST   /api/v1/documents/{id}/reindex # Re-process document
```

### Query & Chat

```
GET    /api/v1/search/{query}?mode=async  # Existing search
POST   /api/v1/chat                       # Chat interface
GET    /api/v1/chat/{session_id}/history  # Chat history
```

### Graph & Analytics

```
GET    /api/v1/graph/entities             # Knowledge graph entities
GET    /api/v1/graph/relationships        # Entity relationships
GET    /api/v1/analytics/queries          # Query stats
```

---

## Database Schema (PostgreSQL)

### Documents Table
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    content_type VARCHAR(100),
    file_size BIGINT,
    storage_path TEXT,
    upload_date TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(50),
    error_message TEXT,
    metadata JSONB
);
```

### Chunks Table
```sql
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    content TEXT,
    embedding vector(3072),  -- pgvector extension
    chunk_index INTEGER,
    metadata JSONB
);

CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops);
```

### Knowledge Graph Tables
```sql
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(100),
    description TEXT,
    embedding vector(3072),
    metadata JSONB
);

CREATE TABLE relationships (
    id SERIAL PRIMARY KEY,
    source_entity_id INTEGER REFERENCES entities(id),
    target_entity_id INTEGER REFERENCES entities(id),
    relationship_type VARCHAR(100),
    confidence FLOAT,
    metadata JSONB
);
```

---

## Configuration Updates

### New Environment Variables

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mnemosyne_universal
POSTGRES_USER=mnemosyne
POSTGRES_PASSWORD=secure_password

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Storage
UPLOAD_DIR=/data/uploads
MAX_FILE_SIZE=100MB

# Processing
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# LightRAG
LIGHTRAG_GRAPH_STORAGE=postgres
LIGHTRAG_MAX_ENTITIES=10000

# RAG-Anything
RAG_ANYTHING_VLM_ENABLED=true
RAG_ANYTHING_PROCESS_IMAGES=true
RAG_ANYTHING_PROCESS_TABLES=true

# Embeddings
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=3072

# Reranker
RERANKER_TYPE=flashrank  # or cohere
COHERE_API_KEY=your_key_if_using_cohere
```

---

## Dependencies (New)

```txt
# Core RAG
lightrag>=0.2.0
rag-anything>=0.1.0

# Document Processing
mineru>=0.1.0
docling>=1.0.0
chonkie>=0.1.0
python-magic>=0.4.27
pypdf2>=3.0.0
python-docx>=0.8.11

# Database
psycopg2-binary>=2.9.9
pgvector>=0.2.0

# Task Queue
celery>=5.3.0
redis>=5.0.0

# Reranking
flashrank>=0.2.0
# cohere>=4.0.0  # optional

# Observability
langfuse>=2.0.0

# File Upload
python-multipart>=0.0.6
aiofiles>=23.0.0

# Keep existing
langchain>=0.3.1
openai>=1.47.0
sentence-transformers>=3.1.0
```

---

## Testing Strategy

### Unit Tests
- Document parsing (MinerU, Docling)
- Chunking strategies (Chonkie)
- LightRAG retrieval
- RAG-Anything multimodal processing
- Embedding generation
- Reranking logic

### Integration Tests
- Upload → Process → Index → Retrieve flow
- Multimodal content pipeline
- Graph construction from documents
- LLM query with graph context

### Performance Tests
- Upload speed (various file sizes)
- Query latency (with/without reranking)
- Concurrent user simulations
- Graph traversal performance

### E2E Tests
- User uploads PDF → asks question → gets cited answer
- Multimodal query (text + images in results)
- Follow-up questions with context

---

## Migration Strategy from Current System

### Option 1: Clean Slate (Recommended)
1. Archive existing Medium articles data
2. Deploy new LightRAG system
3. Re-ingest Medium articles as documents
4. Add new content types incrementally

**Pros:** Clean architecture, no legacy baggage
**Cons:** Data re-processing time

### Option 2: Dual System
1. Keep MongoDB for Medium articles (read-only)
2. New uploads go to PostgreSQL + LightRAG
3. Union results from both systems
4. Migrate MongoDB data gradually

**Pros:** Zero downtime, gradual migration
**Cons:** Complexity maintaining two systems

**Recommendation:** Option 1 (Clean Slate) - simpler long-term

---

## Risk Assessment

### Technical Risks

**Risk 1: LightRAG Performance at Scale**
- *Mitigation:* Start with document limit (10K docs), monitor graph size
- *Fallback:* GraphRAG if needed (though more expensive)

**Risk 2: Multimodal Processing Latency**
- *Mitigation:* Async processing with Celery, user sees progress
- *Fallback:* Disable heavy features (video transcription) initially

**Risk 3: PostgreSQL Vector Search Performance**
- *Mitigation:* Proper indexing (HNSW), query optimization
- *Fallback:* Dedicated vector DB (Qdrant, Weaviate) if needed

**Risk 4: API Costs (OpenAI embeddings)**
- *Mitigation:* Cache embeddings, use local models when possible
- *Fallback:* sentence-transformers for embeddings

### Operational Risks

**Risk 5: File Storage Scaling**
- *Mitigation:* S3/object storage integration in Phase 2
- *Fallback:* File size limits, storage quotas

**Risk 6: Processing Queue Overload**
- *Mitigation:* Rate limiting, user quotas
- *Fallback:* Manual processing approval

---

## Success Metrics

### Functional Metrics
- [ ] Support 50+ file formats (PDF, Office, images, video, audio)
- [ ] Graph-based retrieval working (entities + relationships)
- [ ] Multimodal queries return relevant results
- [ ] Citations link to source documents
- [ ] File upload UI functional and intuitive

### Performance Metrics
- [ ] Query latency < 3s (p95)
- [ ] Upload processing < 30s for 10MB PDF (p95)
- [ ] Support 100 concurrent users
- [ ] Graph construction < 1min for 100-page doc

### Quality Metrics
- [ ] Retrieval accuracy > 85% (RAGAS evaluation)
- [ ] User satisfaction > 4/5
- [ ] Citation accuracy > 90%

---

## Next Steps

1. **Review & Approve Plan** (User decision)
   - Confirm LightRAG + RAG-Anything approach
   - Approve tech stack choices
   - Set timeline expectations

2. **Phase 1 Kickoff**
   - Set up PostgreSQL + pgvector
   - Install LightRAG
   - Begin backend migration

3. **Create Detailed Task Breakdown**
   - User stories for each phase
   - Sprint planning (2-week sprints)
   - Assign priorities

4. **Set Up Development Environment**
   - Docker Compose for local dev
   - Test data preparation
   - CI/CD pipeline

---

## References

### GitHub Repositories
1. SurfSense: https://github.com/MODSetter/SurfSense
2. RAG-Anything: https://github.com/HKUDS/RAG-Anything
3. LightRAG: https://github.com/HKUDS/LightRAG
4. Pathway: https://github.com/pathwaycom/pathway
5. Airweave: https://github.com/airweave-ai/airweave
6. GraphRAG: https://github.com/microsoft/graphrag

### Research Papers
- LightRAG Paper: https://arxiv.org/pdf/2410.05779
- GraphRAG Microsoft Research: https://www.microsoft.com/en-us/research/project/graphrag/

### Documentation
- pgvector: https://github.com/pgvector/pgvector
- LangChain: https://python.langchain.com/
- Chonkie: https://github.com/bhavnicksm/chonkie

---

## Conclusion

The proposed **LightRAG + RAG-Anything hybrid architecture** offers the best balance of:

✅ **Cost Efficiency** (99% token reduction)
✅ **Multimodal Support** (50+ file formats)
✅ **Performance** (single API call, fast retrieval)
✅ **Scalability** (incremental graph updates)
✅ **Proven Results** (86.4% better in complex queries)

This approach leverages the strengths of multiple systems while avoiding their weaknesses:
- Skip GraphRAG's high costs
- Use SurfSense's parsing/chunking components
- Borrow Airweave's connector patterns (future)
- Reserve Pathway for Phase 3 real-time features

**Timeline:** 8 weeks to production-ready universal RAG
**Risk Level:** Medium (mitigated with phased approach)
**Expected Outcome:** NotebookLM-like experience with self-hosted control

---

**Prepared by:** Claude (Mnemosyne Development Team)
**Status:** Awaiting User Approval
**Next Action:** Review plan → Approve tech choices → Begin Phase 1
