# SurfSense Deep Dive - Architecture Patterns for Mnemosyne

**Date:** 2025-11-14
**Purpose:** Document reusable patterns from SurfSense for Mnemosyne RAG-as-a-Service platform
**SurfSense Repository:** Cloned to `/home/user/SurfSense/` for reference

---

## Table of Contents
1. [Project Structure](#project-structure)
2. [Database Architecture](#database-architecture)
3. [API Design Patterns](#api-design-patterns)
4. [Document Processing Pipeline](#document-processing-pipeline)
5. [Hybrid Search Implementation](#hybrid-search-implementation)
6. [Celery Task Architecture](#celery-task-architecture)
7. [Service Layer Patterns](#service-layer-patterns)
8. [Key Takeaways for Mnemosyne](#key-takeaways-for-mnemosyne)

---

## 1. Project Structure

### SurfSense Backend Structure
```
surfsense_backend/
├── main.py                    # Entry point (uvicorn runner)
├── app.py                     # FastAPI app setup
├── celery_app.py              # Celery configuration
├── celery_worker.py           # Celery worker entry
├── app/
│   ├── __init__.py
│   ├── db.py                  # Database models (ALL models in one file)
│   ├── users.py               # FastAPI Users setup
│   ├── app.py                 # Main FastAPI app
│   │
│   ├── config/                # Configuration
│   │   ├── __init__.py
│   │   └── uvicorn.py
│   │
│   ├── routes/                # API routes (one file per resource)
│   │   ├── documents_routes.py
│   │   ├── chats_routes.py
│   │   ├── podcasts_routes.py
│   │   ├── llm_config_routes.py
│   │   ├── search_source_connectors_routes.py
│   │   ├── google_gmail_add_connector_route.py
│   │   └── ... (connector-specific routes)
│   │
│   ├── schemas/               # Pydantic models
│   │   └── ... (request/response models)
│   │
│   ├── services/              # Business logic services
│   │   ├── llm_service.py
│   │   ├── reranker_service.py
│   │   ├── docling_service.py
│   │   ├── query_service.py
│   │   ├── connector_service.py
│   │   └── task_logging_service.py
│   │
│   ├── retriver/              # Search/retrieval logic
│   │   ├── chunks_hybrid_search.py
│   │   └── documents_hybrid_search.py
│   │
│   ├── tasks/                 # Celery tasks
│   │   ├── celery_tasks/
│   │   │   ├── document_tasks.py
│   │   │   ├── connector_tasks.py
│   │   │   └── podcast_tasks.py
│   │   ├── document_processors/
│   │   │   ├── base.py
│   │   │   ├── file_processors.py
│   │   │   ├── url_crawler.py
│   │   │   └── youtube_processor.py
│   │   └── connector_indexers/
│   │       └── ... (connector-specific)
│   │
│   ├── agents/                # LangGraph agents
│   │   ├── qna/
│   │   └── podcaster/
│   │
│   ├── prompts/               # LLM prompts
│   ├── connectors/            # Connector configs
│   └── utils/                 # Utility functions
```

**Pattern: Flat File Organization**
- **All database models in ONE file** (`db.py` - 500+ lines)
- **One route file per resource** (documents, chats, connectors)
- **Services are independent modules** (no subdirectories)
- **Tasks organized by type** (celery_tasks, document_processors, connector_indexers)

**What This Means for Mnemosyne:**
- ✅ Keep models in single `models.py` (easier to see relationships)
- ✅ One route file per API resource (`documents.py`, `retrievals.py`, `chat.py`)
- ✅ Flat service structure (don't over-nest directories)
- ✅ Separate tasks by purpose (ingestion tasks, indexing tasks, sync tasks)

---

## 2. Database Architecture

### Core Models (from `db.py`)

**1. User Model (FastAPI Users)**
```python
from fastapi_users.db import SQLAlchemyBaseUserTableUUID

class User(SQLAlchemyBaseUserTableUUID, Base):
    # Built-in fields: id (UUID), email, hashed_password, is_active, is_verified
    # Relationships to other models
    pass
```

**Pattern: FastAPI Users Integration**
- Uses UUID for user IDs
- Built-in email/password + OAuth support
- JWT authentication via auth_backend

**2. Document Model**
```python
class Document(BaseModel, TimestampMixin):
    __tablename__ = "documents"

    title = Column(String, nullable=False, index=True)
    document_type = Column(SQLAlchemyEnum(DocumentType), nullable=False)
    document_metadata = Column(JSON, nullable=True)  # Flexible metadata

    content = Column(Text, nullable=False)
    content_hash = Column(String, nullable=False, index=True, unique=True)  # Deduplication
    unique_identifier_hash = Column(String, nullable=True, index=True, unique=True)  # Source ID
    embedding = Column(Vector(dimension))  # pgvector

    # Foreign keys
    search_space_id = Column(Integer, ForeignKey("searchspaces.id", ondelete="CASCADE"))

    # Relationships
    search_space = relationship("SearchSpace", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
```

**Key Patterns:**
- ✅ **Content hashing for deduplication** (`content_hash`)
- ✅ **Unique identifier for updates** (`unique_identifier_hash` - from source like Slack message ID)
- ✅ **Document-level embeddings** (for coarse retrieval)
- ✅ **Flexible metadata** (JSON column for varying metadata)
- ✅ **Cascade deletes** (delete document → auto-delete chunks)
- ✅ **Enum for document types** (enforces valid types)

**3. Chunk Model**
```python
class Chunk(BaseModel, TimestampMixin):
    __tablename__ = "chunks"

    content = Column(Text, nullable=False)
    embedding = Column(Vector(dimension))

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    document = relationship("Document", back_populates="chunks")
```

**Pattern: Simple Chunk Model**
- ✅ **Just content + embedding** (minimal)
- ✅ **Link to parent document** (cascade delete)
- ✅ **No chunk metadata** (inherits from document)

**4. SearchSpace (Multi-Tenancy)**
```python
class SearchSpace(BaseModel, TimestampMixin):
    __tablename__ = "searchspaces"

    name = Column(String, nullable=False)
    user_id = Column(UUID, ForeignKey("user.id", ondelete="CASCADE"))

    # Relationships
    user = relationship("User", back_populates="search_spaces")
    documents = relationship("Document", back_populates="search_space", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="search_space", cascade="all, delete-orphan")
```

**Pattern: Multi-Tenancy via Search Spaces**
- ✅ **Users have multiple search spaces** (like "Personal", "Work", "Research")
- ✅ **Documents belong to search space** (user → search space → documents)
- ✅ **Isolation enforced at query level** (WHERE search_space.user_id = current_user.id)

**What This Means for Mnemosyne:**
- ✅ Use similar multi-tenancy pattern (user → collections → documents)
- ✅ Content hashing for deduplication
- ✅ Flexible JSON metadata
- ✅ Cascade deletes
- ❌ **We'll add:** Entity and Relationship tables (for LightRAG)

---

## 3. API Design Patterns

### Pattern 1: File Upload Endpoint

**SurfSense Implementation:**
```python
@router.post("/documents/fileupload")
async def create_documents_file_upload(
    files: list[UploadFile],
    search_space_id: int = Form(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    # 1. Check ownership
    await check_ownership(session, SearchSpace, search_space_id, user)

    # 2. Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        temp_path = temp_file.name
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

    # 3. Queue Celery task
    from app.tasks.celery_tasks.document_tasks import process_file_upload_task
    process_file_upload_task.delay(temp_path, file.filename, search_space_id, str(user.id))

    return {"message": "Files uploaded for processing"}
```

**Key Patterns:**
- ✅ **Ownership check** (user can only upload to their spaces)
- ✅ **Temp file handling** (avoid stream issues)
- ✅ **Async task queue** (immediate response, background processing)
- ✅ **Celery task receives:** file path, metadata, user ID

**Mnemosyne Adaptation:**
```python
@router.post("/documents")
async def create_document(
    file: UploadFile,
    metadata: dict = Form(default={}),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    # 1. Validate user quota
    await check_user_quota(session, user)

    # 2. Save to storage (S3 or local)
    file_path = await save_file(file)

    # 3. Queue processing
    from app.tasks.ingestion import process_document_task
    task = process_document_task.delay(file_path, user.id, metadata)

    # 4. Return document ID immediately
    return {"document_id": task.id, "status": "processing"}
```

### Pattern 2: Chat/Query Endpoint with Streaming

**SurfSense Implementation:**
```python
@router.post("/chat")
async def handle_chat_data(
    request: AISDKChatRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    # 1. Validate messages
    messages = validate_messages(request.messages)

    # 2. Extract request data
    search_space_id = validate_search_space_id(request.data.get("search_space_id"))
    top_k = validate_top_k(request.data.get("top_k"))
    search_mode = validate_search_mode(request.data.get("search_mode"))

    # 3. Check ownership
    await check_ownership(session, SearchSpace, search_space_id, user)

    # 4. Stream response
    return StreamingResponse(
        stream_connector_search_results(...),
        media_type="text/event-stream"
    )
```

**Key Patterns:**
- ✅ **Request validation** (separate validator functions)
- ✅ **Ownership check** (before processing)
- ✅ **SSE streaming** (StreamingResponse with text/event-stream)
- ✅ **Flexible request data** (optional parameters in nested dict)

**Mnemosyne Adaptation:**
```python
@router.post("/chat")
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    # 1. Validate input
    messages = validate_messages(request.messages)
    filters = validate_filters(request.filters)

    # 2. Stream LLM response
    async def stream_chat():
        # Retrieve context
        context = await retrieve_context(query=messages[-1].content, user=user, filters=filters)

        # Stream LLM
        async for chunk in llm_service.stream(messages, context):
            yield f"data: {json.dumps({'delta': chunk})}\n\n"

        # Final metadata
        yield f"data: {json.dumps({'done': True, 'sources': context.sources})}\n\n"

    return StreamingResponse(stream_chat(), media_type="text/event-stream")
```

### Pattern 3: List Documents with Pagination

**SurfSense Implementation:**
```python
@router.get("/documents", response_model=PaginatedResponse[DocumentRead])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search_space_id: int | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    # Build query with ownership filter
    query = (
        select(Document)
        .join(SearchSpace)
        .where(SearchSpace.user_id == user.id)
    )

    if search_space_id:
        query = query.where(Document.search_space_id == search_space_id)

    # Count total
    total_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(total_query)

    # Paginate
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    documents = result.scalars().all()

    return PaginatedResponse(items=documents, total=total, skip=skip, limit=limit)
```

**Key Patterns:**
- ✅ **Pagination** (skip/limit with bounds)
- ✅ **Total count** (for pagination UI)
- ✅ **Optional filters** (search_space_id)
- ✅ **Ownership filter always applied** (WHERE user_id = ...)

---

## 4. Document Processing Pipeline

### High-Level Flow

```
1. File Upload (API)
   ↓
2. Save to Temp File
   ↓
3. Queue Celery Task (process_file_upload_task)
   ↓
4. Celery Worker Picks Up Task
   ↓
5. Document Processor (file_processors.py)
   ├─ Detect file type
   ├─ Parse with Docling/Unstructured/LlamaCloud
   ├─ Extract text + metadata
   ├─ Hash content (deduplication check)
   └─ If duplicate: skip, else continue
   ↓
6. Chunking (Chonkie or custom)
   ├─ Split document into chunks
   └─ Maintain context/overlap
   ↓
7. Embedding Generation
   ├─ Embed full document
   └─ Embed each chunk
   ↓
8. Database Insertion
   ├─ Insert Document
   ├─ Insert Chunks
   └─ Commit transaction
   ↓
9. Update Status (in database or return to user)
```

### Celery Task Pattern

**Task Definition:**
```python
@celery_app.task(name="process_file_upload", bind=True)
def process_file_upload_task(self, file_path: str, filename: str, search_space_id: int, user_id: str):
    import asyncio

    # Create new event loop (Celery tasks run in separate loop)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_process_file_upload(file_path, filename, search_space_id, user_id))
    finally:
        loop.close()


async def _process_file_upload(file_path, filename, search_space_id, user_id):
    # Get new DB session for task
    async with get_celery_session_maker()() as session:
        task_logger = TaskLoggingService(session, search_space_id)

        log_entry = await task_logger.log_task_start(
            task_name="process_file_upload",
            source="document_processor",
            message=f"Starting processing of file: {filename}"
        )

        try:
            # Process document
            result = await add_file_document(session, file_path, filename, search_space_id, user_id)

            await task_logger.log_task_success(log_entry, f"Successfully processed: {filename}")
        except Exception as e:
            await task_logger.log_task_failure(log_entry, f"Failed: {filename}", str(e))
            raise
```

**Key Patterns:**
- ✅ **New event loop for Celery** (avoid loop conflicts)
- ✅ **Separate DB session** (Celery session != API session)
- ✅ **NullPool for Celery** (no connection pooling in workers)
- ✅ **Task logging** (track start, success, failure in DB)
- ✅ **Async processing function** (actual work in separate `_process_*` function)

### Document Processor Pattern

**Base Processor (`base.py`):**
```python
async def check_duplicate_document(session: AsyncSession, content_hash: str) -> Document | None:
    """Check if document with content hash exists."""
    result = await session.execute(
        select(Document).where(Document.content_hash == content_hash)
    )
    return result.scalars().first()


async def check_document_by_unique_identifier(session: AsyncSession, unique_identifier_hash: str) -> Document | None:
    """Check if document with unique identifier exists (for updates)."""
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.chunks))  # Eagerly load chunks
        .where(Document.unique_identifier_hash == unique_identifier_hash)
    )
    return result.scalars().first()
```

**File Processor (`file_processors.py` - simplified):**
```python
async def add_file_document(session, file_path, filename, search_space_id, user_id):
    # 1. Parse file
    parsed_content = await docling_service.process_file(file_path)

    # 2. Hash content
    content_hash = hashlib.sha256(parsed_content.encode()).hexdigest()

    # 3. Check duplicate
    existing = await check_duplicate_document(session, content_hash)
    if existing:
        return None  # Skip duplicate

    # 4. Chunk content
    chunks = chunk_text(parsed_content)

    # 5. Generate embeddings
    doc_embedding = embedding_service.embed(parsed_content)
    chunk_embeddings = [embedding_service.embed(chunk) for chunk in chunks]

    # 6. Create document
    document = Document(
        title=filename,
        document_type=DocumentType.FILE,
        content=parsed_content,
        content_hash=content_hash,
        embedding=doc_embedding,
        search_space_id=search_space_id
    )
    session.add(document)
    await session.flush()  # Get document.id

    # 7. Create chunks
    for chunk_text, chunk_emb in zip(chunks, chunk_embeddings):
        chunk = Chunk(
            content=chunk_text,
            embedding=chunk_emb,
            document_id=document.id
        )
        session.add(chunk)

    await session.commit()
    return document
```

**Key Patterns:**
- ✅ **Parse → Hash → Check Duplicate → Chunk → Embed → Insert**
- ✅ **Flush after document insert** (to get document.id for chunks)
- ✅ **Batch embed chunks** (more efficient)

---

## 5. Hybrid Search Implementation

### Hybrid Search Pattern (`chunks_hybrid_search.py`)

**1. Vector Search:**
```python
async def vector_search(self, query_text: str, top_k: int, user_id: str, search_space_id: int | None = None):
    # 1. Embed query
    query_embedding = embedding_model.embed(query_text)

    # 2. Build query with ownership check
    query = (
        select(Chunk)
        .options(joinedload(Chunk.document).joinedload(Document.search_space))
        .join(Document, Chunk.document_id == Document.id)
        .join(SearchSpace, Document.search_space_id == SearchSpace.id)
        .where(SearchSpace.user_id == user_id)
    )

    # 3. Filter by search space (optional)
    if search_space_id:
        query = query.where(Document.search_space_id == search_space_id)

    # 4. Vector similarity ordering (pgvector)
    query = query.order_by(Chunk.embedding.op("<=>")(query_embedding)).limit(top_k)

    # 5. Execute
    result = await self.db_session.execute(query)
    return result.scalars().all()
```

**Key Pattern:**
- ✅ **pgvector distance operator** (`<=>` is cosine distance)
- ✅ **Eager loading relationships** (`joinedload` to avoid N+1)
- ✅ **User ownership enforced** (always check user_id)

**2. Full-Text Search:**
```python
async def full_text_search(self, query_text: str, top_k: int, user_id: str, search_space_id: int | None = None):
    # 1. Create tsvector and tsquery (PostgreSQL)
    tsvector = func.to_tsvector("english", Chunk.content)
    tsquery = func.plainto_tsquery("english", query_text)

    # 2. Build query
    query = (
        select(Chunk)
        .options(joinedload(Chunk.document).joinedload(Document.search_space))
        .join(Document, Chunk.document_id == Document.id)
        .join(SearchSpace, Document.search_space_id == SearchSpace.id)
        .where(SearchSpace.user_id == user_id)
        .where(tsvector.op("@@")(tsquery))  # Full-text match
    )

    # 3. Order by relevance rank
    query = query.order_by(func.ts_rank(tsvector, tsquery).desc()).limit(top_k)

    result = await self.db_session.execute(query)
    return result.scalars().all()
```

**Key Pattern:**
- ✅ **PostgreSQL full-text search** (`to_tsvector`, `plainto_tsquery`)
- ✅ **Relevance ranking** (`ts_rank`)
- ✅ **Filter before ranking** (only match results included)

**3. Reciprocal Rank Fusion (RRF):**
```python
async def hybrid_search(self, query_text: str, top_k: int, user_id: str, search_space_id: int | None = None):
    # 1. Run both searches in parallel
    vector_results, fts_results = await asyncio.gather(
        self.vector_search(query_text, top_k * 2, user_id, search_space_id),
        self.full_text_search(query_text, top_k * 2, user_id, search_space_id)
    )

    # 2. Reciprocal Rank Fusion
    rrf_scores = {}
    k = 60  # RRF constant

    # Score vector results
    for rank, chunk in enumerate(vector_results, start=1):
        rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0) + 1 / (k + rank)

    # Score FTS results
    for rank, chunk in enumerate(fts_results, start=1):
        rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0) + 1 / (k + rank)

    # 3. Deduplicate and sort by RRF score
    all_chunks = {chunk.id: chunk for chunk in vector_results + fts_results}
    sorted_chunks = sorted(
        all_chunks.values(),
        key=lambda c: rrf_scores[c.id],
        reverse=True
    )

    return sorted_chunks[:top_k]
```

**Key Pattern:**
- ✅ **Parallel searches** (`asyncio.gather`)
- ✅ **RRF formula:** `1 / (k + rank)` where k=60
- ✅ **Sum scores** (chunk appears in both → higher score)
- ✅ **Deduplication** (chunk appears only once in final results)

---

## 6. Celery Task Architecture

### Pattern 1: Task Configuration (`celery_app.py`)

```python
celery_app = Celery(
    "surfsense",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.celery_tasks.document_tasks",
        "app.tasks.celery_tasks.connector_tasks",
        # ...
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_track_started=True,
    task_time_limit=28800,  # 8 hour hard limit
    task_soft_time_limit=28200,
    result_expires=86400,  # 24 hours
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,  # Re-queue on worker crash
    task_reject_on_worker_lost=True,
)
```

**Key Patterns:**
- ✅ **JSON serialization** (safer than pickle)
- ✅ **Time limits** (soft + hard)
- ✅ **Result expiration** (don't store forever)
- ✅ **Prefetch 1** (better for long tasks)
- ✅ **Late acks** (re-queue failed tasks)

### Pattern 2: Periodic Tasks (Celery Beat)

```python
celery_app.conf.beat_schedule = {
    "check-periodic-connector-schedules": {
        "task": "check_periodic_schedules",
        "schedule": crontab(minute="*/2"),  # Every 2 minutes
        "options": {"expires": 30},
    },
}
```

**Pattern: Meta-Scheduler**
- ✅ **One beat task** checks DB for connectors needing sync
- ✅ **Dynamic scheduling** (no restart needed to add connectors)
- ✅ **Task expiration** (if worker busy, task expires)

### Pattern 3: Task Logging Service

```python
class TaskLoggingService:
    async def log_task_start(self, task_name, source, message, metadata=None):
        log_entry = TaskLog(
            task_name=task_name,
            source=source,
            status=LogStatus.IN_PROGRESS,
            message=message,
            metadata=metadata,
            search_space_id=self.search_space_id
        )
        self.session.add(log_entry)
        await self.session.commit()
        return log_entry

    async def log_task_success(self, log_entry, message, metadata=None):
        log_entry.status = LogStatus.SUCCESS
        log_entry.message = message
        if metadata:
            log_entry.metadata = {**log_entry.metadata, **metadata}
        await self.session.commit()

    async def log_task_failure(self, log_entry, message, error, metadata=None):
        log_entry.status = LogStatus.FAILED
        log_entry.message = message
        log_entry.error_message = error
        await self.session.commit()
```

**Key Pattern:**
- ✅ **Track task lifecycle** (start → success/failure)
- ✅ **Store in database** (user can see processing status)
- ✅ **Flexible metadata** (task-specific info)

---

## 7. Service Layer Patterns

### Pattern 1: Reranker Service

```python
class RerankerService:
    def __init__(self, reranker_instance=None):
        self.reranker_instance = reranker_instance

    def rerank_documents(self, query_text: str, documents: list[dict]) -> list[dict]:
        if not self.reranker_instance or not documents:
            return documents  # No reranker → return as-is

        try:
            # Convert to reranker format
            reranker_docs = [
                RerankerDocument(text=doc["content"], doc_id=doc["chunk_id"], metadata=doc)
                for doc in documents
            ]

            # Rerank
            results = self.reranker_instance.rank(query=query_text, docs=reranker_docs)

            # Convert back
            reranked = []
            for result in results.results:
                original_doc = next(d for d in documents if d["chunk_id"] == result.document.doc_id)
                reranked_doc = original_doc.copy()
                reranked_doc["score"] = float(result.score)
                reranked_doc["rank"] = result.rank
                reranked.append(reranked_doc)

            return reranked

        except Exception as e:
            # Fallback to original on error
            return documents
```

**Key Patterns:**
- ✅ **Graceful degradation** (no reranker → return original)
- ✅ **Error handling** (fallback on failure)
- ✅ **Format conversion** (to/from reranker library)
- ✅ **Preserve original metadata** (just add rerank score)

### Pattern 2: Docling Service (Document Parsing)

```python
class DoclingService:
    def __init__(self):
        self._configure_ssl_environment()
        self._check_wsl2_gpu_support()
        self._initialize_docling()

    def process_file(self, file_path: str) -> str:
        # Parse document
        result = self.converter.convert(file_path)

        # Extract markdown
        markdown_text = result.document.export_to_markdown()

        return markdown_text
```

**Key Patterns:**
- ✅ **Lazy initialization** (converter created in __init__)
- ✅ **GPU detection** (use CUDA if available)
- ✅ **SSL handling** (for model downloads)
- ✅ **Markdown export** (standardized output format)

---

## 8. Key Takeaways for Mnemosyne

### Architecture Decisions

**✅ ADOPT from SurfSense:**

1. **Database:**
   - PostgreSQL + pgvector (proven, production-ready)
   - Content hashing for deduplication
   - Cascade deletes (documents → chunks)
   - Flexible JSON metadata columns
   - FastAPI Users for auth (UUID-based)

2. **API Design:**
   - FastAPI with async/await
   - Ownership checks on all queries
   - Pagination with total counts
   - SSE streaming for chat
   - Form-based file uploads

3. **Celery Tasks:**
   - JSON serialization (not pickle)
   - New event loop per task
   - Separate DB session (NullPool)
   - Task logging in database
   - Time limits + late acks

4. **Hybrid Search:**
   - Vector search (pgvector `<=>` operator)
   - Full-text search (PostgreSQL `to_tsvector`)
   - RRF fusion (k=60)
   - Parallel search execution

5. **Processing Pipeline:**
   - Docling for document parsing
   - Content hashing before processing
   - Chunk + embed pattern
   - Deduplication checks

**❌ MODIFY for Mnemosyne:**

1. **Multi-Tenancy:**
   - **SurfSense:** SearchSpace model (user → search spaces → documents)
   - **Mnemosyne:** Simpler (user → collections → documents)
   - **Reason:** API-first service needs simpler model

2. **File Organization:**
   - **SurfSense:** All models in one `db.py` (500+ lines)
   - **Mnemosyne:** Split models into categories (adhering to 300-line limit)
   - **Reason:** CLAUDE.md guideline (max 300 lines per file)

3. **API Structure:**
   - **SurfSense:** `/documents/fileupload`, `/chat`, `/documents`
   - **Mnemosyne:** `/documents`, `/retrievals`, `/chat` (cleaner, SDK-friendly)
   - **Reason:** Ragie.ai-style API simplicity

**➕ ADD to Mnemosyne:**

1. **LightRAG Integration:**
   - Entity and Relationship models (knowledge graph)
   - Graph-based retrieval layer
   - Dual-level queries (low + high)

2. **SDK-First Design:**
   - Python SDK (PyPI)
   - TypeScript SDK (npm)
   - Consistent API contracts

3. **Connector Framework:**
   - Abstract Connector base class
   - Pluggable connector system
   - Scheduled sync tasks

---

## Recommended Mnemosyne Architecture (Based on Learnings)

### Database Models
```python
# models/user.py
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
class User(SQLAlchemyBaseUserTableUUID, Base):
    collections = relationship("Collection", back_populates="user")

# models/collection.py
class Collection(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    user_id = Column(UUID, ForeignKey("user.id"))
    user = relationship("User", back_populates="collections")
    documents = relationship("Document", back_populates="collection", cascade="all, delete-orphan")

# models/document.py
class Document(Base):
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, index=True)
    content_type = Column(String)
    content = Column(Text, nullable=False)
    content_hash = Column(String, unique=True, index=True)  # Deduplication
    embedding = Column(Vector(3072))
    metadata = Column(JSON, default={})
    collection_id = Column(Integer, ForeignKey("collections.id"))
    collection = relationship("Collection", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

# models/chunk.py
class Chunk(Base):
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(3072))
    document_id = Column(Integer, ForeignKey("documents.id"))
    document = relationship("Document", back_populates="chunks")

# models/entity.py (for LightRAG)
class Entity(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    type = Column(String)  # person, organization, concept, etc.
    description = Column(Text)
    embedding = Column(Vector(3072))
    metadata = Column(JSON, default={})

# models/relationship.py (for LightRAG)
class Relationship(Base):
    id = Column(Integer, primary_key=True)
    source_entity_id = Column(Integer, ForeignKey("entities.id"))
    target_entity_id = Column(Integer, ForeignKey("entities.id"))
    relationship_type = Column(String)
    confidence = Column(Float)
    document_ids = Column(ARRAY(Integer))  # Which docs mention this
```

### API Endpoints
```python
# routes/documents.py
@router.post("/documents")  # File upload
@router.get("/documents")   # List docs (paginated)
@router.get("/documents/{id}")  # Get doc details
@router.delete("/documents/{id}")  # Delete doc

# routes/retrievals.py
@router.post("/retrievals")  # Query + retrieve

# routes/chat.py
@router.post("/chat")  # Chat with streaming

# routes/connectors.py
@router.get("/connectors")  # List available
@router.post("/connectors/{type}/connect")  # Connect source
@router.post("/connectors/{id}/sync")  # Sync now
```

### Services
```python
# services/ingest_service.py (< 300 lines)
# services/embedding_service.py (< 300 lines)
# services/chunking_service.py (< 300 lines)
# services/lightrag_service.py (< 300 lines)
# services/retrieval_service.py (< 300 lines)
# services/llm_service.py (< 300 lines)
# services/reranker_service.py (< 300 lines)
```

### Tasks
```python
# tasks/ingestion/
#   - process_document.py
#   - extract_entities.py
#   - build_graph.py

# tasks/connectors/
#   - sync_google_drive.py
#   - sync_notion.py
#   - sync_slack.py
```

---

## Summary

**SurfSense provides excellent patterns for:**
- ✅ Multi-tenant architecture
- ✅ Hybrid search implementation
- ✅ Celery task organization
- ✅ Document processing pipeline
- ✅ FastAPI + PostgreSQL + pgvector

**For Mnemosyne, we'll:**
- ✅ Use these proven patterns as reference
- ✅ Simplify API design (SDK-friendly)
- ✅ Add LightRAG for graph retrieval
- ✅ Maintain 300-line file limit
- ✅ Build API-first (not web-app-first)

---

**Next Step:** Design Mnemosyne API contracts based on these learnings!
