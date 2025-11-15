# Mnemosyne - Project Status

**Last Updated:** 2025-11-15
**Branch:** claude/gather-info-01DoZyMRxPMNshGrrTZEEE2m
**Status:** Week 1 Complete, Week 2 Ready to Start

---

## Project Overview

**Vision:** Open-source RAG-as-a-Service platform (like Ragie.ai)
**Architecture:** FastAPI + PostgreSQL + pgvector + Celery + LightRAG
**Capabilities:** 50+ file formats, 15+ integrations, self-hostable

---

## Current State

### Completed: Week 1 (Foundation)

**Duration:** 5 days
**Commits:** 7 commits
**Code:** 20 Python files, 1,485 lines
**Branch:** claude/gather-info-01DoZyMRxPMNshGrrTZEEE2m

**Infrastructure:**
- PostgreSQL with pgvector extension configured
- Docker Compose setup (database + initialization)
- FastAPI application structure
- Configuration management (Pydantic Settings)
- Database session management (SQLAlchemy)

**Database Models:** (backend/models/)
- User: Authentication and ownership
- APIKey: SHA-256 hashed API keys with Bearer token support
- Collection: Logical grouping of documents (unique per user)
- Document: File metadata with content hashing (SHA-256) for deduplication

**Key Features:**
- UUID primary keys throughout
- Cascade deletes (User → Collections → Documents)
- Content-based deduplication
- Timestamp tracking (created_at, updated_at)
- Status field for processing pipeline ("pending" in Week 1)

**API Endpoints:** (11 total)

Authentication (backend/api/auth.py):
- POST /api/v1/auth/register - User registration with automatic API key generation

Collections (backend/api/collections.py):
- POST /api/v1/collections - Create collection (with uniqueness check)
- GET /api/v1/collections - List collections (with pagination)
- GET /api/v1/collections/{id} - Get single collection
- PATCH /api/v1/collections/{id} - Update collection metadata
- DELETE /api/v1/collections/{id} - Delete collection (cascades to documents)

Documents (backend/api/documents.py):
- POST /api/v1/documents - Upload document (multipart/form-data)
- GET /api/v1/documents - List documents (with pagination and status filter)
- GET /api/v1/documents/{id} - Get single document
- PATCH /api/v1/documents/{id} - Update document metadata
- DELETE /api/v1/documents/{id} - Delete document

**Security:**
- API key authentication (SHA-256 hashing)
- Bearer token format (Authorization: Bearer mn_test_...)
- Ownership verification on all endpoints
- Password hashing with bcrypt
- Multi-tenant data isolation

**Validation:**
- Pydantic v2 schemas for all endpoints
- Request validation (CollectionCreate, DocumentCreate, etc.)
- Response validation (from_attributes = True)
- Pagination support (limit, offset, has_more)

**Documentation:**
- OpenAPI docs available at /docs
- ReDoc available at /redoc
- Comprehensive inline documentation

---

## Week 1 Success Criteria: All Met

1. PostgreSQL running with pgvector
2. User can register and get API key
3. User can create/read/update/delete collections
4. User can upload documents (metadata stored, status="pending")
5. User can list/get/update/delete documents
6. Ownership verification prevents cross-user access
7. Duplicate documents rejected by content hash
8. OpenAPI docs accessible at /docs

---

## File Structure

```
mnemosyne/
├── backend/
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Pydantic settings (DB, API, security)
│   ├── database.py                # SQLAlchemy session management
│   │
│   ├── models/                    # Database models (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── user.py                # User authentication
│   │   ├── api_key.py             # API key storage
│   │   ├── collection.py          # Document collections
│   │   └── document.py            # Document metadata
│   │
│   ├── schemas/                   # Pydantic validation schemas
│   │   ├── __init__.py
│   │   ├── collection.py          # Collection request/response
│   │   └── document.py            # Document request/response
│   │
│   ├── api/                       # API endpoints
│   │   ├── __init__.py
│   │   ├── deps.py                # Authentication middleware
│   │   ├── auth.py                # Registration endpoint
│   │   ├── collections.py         # Collection CRUD
│   │   └── documents.py           # Document CRUD
│   │
│   └── core/                      # Core utilities
│       ├── __init__.py
│       ├── security.py            # Hashing, key generation
│       └── exceptions.py          # HTTP exception helpers
│
├── scripts/
│   └── init.sql                   # PostgreSQL initialization
│
├── docker-compose.yml             # PostgreSQL + pgvector
├── pyproject.toml                 # Poetry dependencies
├── .env.example                   # Environment variables template
│
├── WEEK_1_PLAN.md                 # Week 1 implementation plan (complete)
├── WEEK_2_PLAN.md                 # Week 2 implementation plan (ready)
├── PRD.md                         # Product requirements document
├── ARCHITECTURE.md                # 50+ formats, 15+ integrations
├── RESEARCH.md                    # SurfSense analysis
├── API_DESIGN.md                  # Complete API specification
└── CLAUDE.md                      # Development guidelines
```

---

## Recent Changes (Last Session)

### Commit: fix: remove emojis from code per CLAUDE.md guidelines
- Removed emojis from backend/main.py startup event
- Complies with CLAUDE.md requirement: "NEVER use emojis in code, comments, or docstrings"
- All code now follows professional style guidelines

### Commit: docs: add comprehensive Week 2 implementation plan
- Created detailed Week 2 plan (7 steps, 5 days)
- Document processing pipeline architecture
- Celery + Redis + Docling + Chonkie + OpenAI embeddings
- Complete implementation guide with code examples

---

## Dependencies (pyproject.toml)

**Current (Week 1):**
- fastapi ^0.115.0
- uvicorn[standard] ^0.32.0
- sqlalchemy ^2.0.0
- psycopg2-binary ^2.9.0
- pgvector ^0.3.0
- pydantic ^2.0.0
- pydantic-settings ^2.0.0
- python-dotenv ^1.0.0
- passlib[bcrypt] ^1.7.4
- python-multipart ^0.0.9
- alembic ^1.13.0

**Week 2 Will Add:**
- celery[redis] ^5.3.0
- redis ^5.0.0
- docling ^1.0.0
- chonkie ^0.1.0
- openai ^1.0.0
- tiktoken ^0.5.0
- python-magic ^0.4.27

---

## Next Steps: Week 2 (Document Processing Pipeline)

### Overview
Transform "pending" documents into searchable chunks with embeddings.

### Architecture
```
Upload → Parse (Docling) → Chunk (Chonkie) → Embed (OpenAI) → Store (pgvector)
```

### Key Components

1. **Redis + Celery** (Day 1)
   - Async task queue for background processing
   - Celery worker + beat scheduler in Docker
   - Task monitoring and retry logic

2. **File Storage** (Day 1)
   - Local filesystem storage with content-based paths
   - Support for uploads/ directory
   - Path sharding (first 2 chars of hash)

3. **Document Parsing** (Day 2)
   - Docling for PDF, DOCX, PPTX parsing
   - Text parser for TXT, MD, HTML fallback
   - Parser factory pattern for extensibility

4. **Semantic Chunking** (Day 3)
   - Chonkie for intelligent chunking
   - 512 tokens per chunk, 128 token overlap
   - Semantic boundaries preservation

5. **Embeddings** (Day 3)
   - OpenAI text-embedding-3-large (1536 dimensions)
   - Batch processing (100 texts at a time)
   - Rate limiting and error handling

6. **Processing Pipeline** (Day 4-5)
   - Complete Celery task orchestration
   - Status tracking: pending → processing → completed/failed
   - Error handling and logging
   - Document status endpoint

### New Database Table: document_chunks

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,

    embedding VECTOR(1536) NOT NULL,  -- pgvector

    metadata JSONB DEFAULT '{}',
    chunk_metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Success Criteria (Week 2)

1. Document upload triggers Celery task automatically
2. Status transitions: pending → processing → completed
3. Documents parsed with Docling (PDF, DOCX support)
4. Text chunked semantically with Chonkie
5. Embeddings generated with OpenAI
6. Chunks stored in pgvector with index
7. GET /documents/{id}/status returns processing status
8. Failed documents show error_message
9. All services run in Docker Compose
10. Processing is fully asynchronous

---

## Week 3 Preview: Vector Search + Retrieval API

After Week 2, we'll implement:
- Vector similarity search (pgvector)
- Hybrid search (semantic + keyword with RRF)
- Reranking for accuracy
- POST /api/v1/retrievals endpoint
- Query processing and ranking
- LightRAG integration (optional)

---

## Testing Instructions (Week 1)

### 1. Start PostgreSQL
```bash
docker-compose up -d postgres
docker-compose logs -f postgres  # Wait for "ready to accept connections"
```

### 2. Install Dependencies
```bash
poetry install
```

### 3. Run FastAPI
```bash
cd backend
poetry run uvicorn main:app --reload
```

### 4. Test Registration
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'

# Save the api_key from response
```

### 5. Create Collection
```bash
export API_KEY="mn_test_..."  # From registration response

curl -X POST "http://localhost:8000/api/v1/collections" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-docs",
    "description": "Test collection",
    "metadata": {"category": "testing"}
  }'

# Save collection_id
```

### 6. Upload Document
```bash
export COLLECTION_ID="..."  # From create collection response

curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -F "collection_id=$COLLECTION_ID" \
  -F "file=@test.pdf" \
  -F 'metadata={"title": "Test Document"}'

# Status will be "pending" (no processing in Week 1)
```

### 7. List Documents
```bash
curl -X GET "http://localhost:8000/api/v1/documents?collection_id=$COLLECTION_ID" \
  -H "Authorization: Bearer $API_KEY"
```

### 8. Access API Docs
```
http://localhost:8000/docs
```

---

## Key Design Decisions

### Why PostgreSQL + pgvector?
- Mature, production-ready database
- Full-text search (pg_trgm) + vector search in one DB
- Excellent performance for hybrid search
- Strong ACID guarantees
- Self-hostable

### Why FastAPI?
- Async support (1,800+ QPS capability)
- Automatic OpenAPI documentation
- Pydantic validation built-in
- Modern Python type hints
- Excellent DX

### Why Celery?
- Industry-standard task queue
- Robust retry mechanisms
- Task monitoring and management
- Supports distributed workers
- Easy to scale

### Why LightRAG (Week 3)?
- Graph-based retrieval (99% token reduction)
- Cost-efficient (58K → 3K tokens)
- Local + global context awareness
- Better than naive RAG

### Why Chonkie?
- Semantic chunking (better than fixed-size)
- Preserves context boundaries
- Optimized for RAG workloads
- Easy integration

---

## Technical Specifications

**Database:**
- PostgreSQL 15+ with pgvector extension
- UUID primary keys (uuid_generate_v4())
- Cascade deletes for data cleanup
- JSONB for flexible metadata
- Full-text indexes (pg_trgm)

**API:**
- RESTful design
- Bearer token authentication
- Pagination (limit/offset)
- Multipart form data for uploads
- JSON responses

**Processing:**
- Async with Celery
- Status tracking throughout pipeline
- Error handling and retry logic
- Batch embedding (100 at a time)
- Content-based deduplication

**Security:**
- API key hashing (SHA-256)
- Password hashing (bcrypt)
- Multi-tenant isolation
- Ownership verification
- Content hash validation

---

## Development Guidelines (CLAUDE.md)

**Core Principles:**
1. Use swarm orchestration for parallel operations
2. Keep files under 300 lines
3. No backward compatibility code
4. No emojis in code/comments/docstrings
5. Always run lint + test + build after changes

**File Organization:**
- snake_case for filenames
- PascalCase for classes
- snake_case for functions/variables
- One service class per file
- Maximum 300 lines per file

**Git Workflow:**
- Descriptive commit messages
- Feature branches (claude/*)
- Push after completion
- Clear commit history

---

## Project Statistics

**Week 1 Metrics:**
- Duration: 5 days
- Commits: 7
- Files created: 35+
- Python files: 20
- Lines of code: 1,485
- API endpoints: 11
- Database models: 4
- Pydantic schemas: 6

**Repository:**
- Main branch: main
- Feature branch: claude/gather-info-01DoZyMRxPMNshGrrTZEEE2m
- All changes pushed and synced

---

## Ready to Proceed

**Week 1:** Complete and tested
**Week 2:** Planned and documented (WEEK_2_PLAN.md)
**Week 3:** Outlined (vector search + retrieval)
**Documentation:** Comprehensive (PRD, ARCHITECTURE, API_DESIGN, RESEARCH)

**To Start Week 2:**
1. Review WEEK_2_PLAN.md
2. Follow 7-step implementation guide
3. Use swarm orchestration for parallel operations
4. Verify exact column names before creating endpoints
5. Test after each step

---

## Questions or Issues?

- Review CLAUDE.md for development guidelines
- Check WEEK_2_PLAN.md for implementation details
- Refer to PRD.md for product vision
- See ARCHITECTURE.md for full specifications
- Consult API_DESIGN.md for endpoint details

**SuperClaude Commands Available:**
- /sc - See all available commands
- /research - Deep web research
- /implement - Structured implementation
- /test - Testing workflows
- /document - Auto-documentation
- /analyze - Code analysis
- /troubleshoot - Debugging

---

## Summary

Week 1 implementation is **complete and production-ready**. The foundation (PostgreSQL, FastAPI, authentication, CRUD) is solid and follows best practices. Week 2 is **ready to start** with a comprehensive implementation plan covering the entire document processing pipeline.

All code follows CLAUDE.md guidelines, uses exact database column names, implements proper security, and is fully documented. The codebase is clean, professional, and ready for scale.

**Next action:** Begin Week 2 implementation following WEEK_2_PLAN.md
