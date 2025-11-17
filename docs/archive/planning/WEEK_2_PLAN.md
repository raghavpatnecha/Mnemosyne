# Week 2 Implementation Plan - Document Processing Pipeline

**Goal:** Implement asynchronous document processing with Celery, Docling parsing, Chonkie chunking, and pgvector embeddings

**Status:** Planning
**Duration:** 5-7 days
**Dependencies:** Week 1 (CRUD endpoints, database models)

---

## Overview

Week 2 focuses on **processing pipeline**:
- Celery + Redis for async task queue
- Docling for document parsing (PDF, DOCX, etc.)
- Chonkie for intelligent chunking (semantic + sentence-level)
- OpenAI text-embedding-3-large for embeddings
- pgvector for vector storage
- Status tracking (pending → processing → completed/failed)
- NO retrieval/search yet (Week 3)

---

## Architecture

```
Document Upload (POST /documents)
    ↓
Store metadata in PostgreSQL (status="pending")
    ↓
Trigger Celery task (process_document.delay(document_id))
    ↓
Celery Worker:
    1. Update status to "processing"
    2. Download/read file from storage
    3. Parse with Docling → extract text
    4. Chunk with Chonkie → semantic chunks
    5. Generate embeddings (OpenAI)
    6. Store in pgvector (chunks table)
    7. Update status to "completed"
    ↓
On error: Update status to "failed", log error
```

---

## Database Changes

### New Table: document_chunks

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,

    -- Embedding
    embedding VECTOR(1536) NOT NULL,  -- text-embedding-3-large dimension

    -- Metadata
    metadata JSONB DEFAULT '{}',
    chunk_metadata JSONB DEFAULT '{}',  -- Chonkie metadata (type, tokens, etc.)

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    CONSTRAINT unique_document_chunk UNIQUE(document_id, chunk_index)
);

-- Vector similarity index
CREATE INDEX idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Query indexes
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_collection_id ON document_chunks(collection_id);
CREATE INDEX idx_chunks_user_id ON document_chunks(user_id);
```

### Update documents table

```sql
-- Add processing fields
ALTER TABLE documents ADD COLUMN processed_at TIMESTAMPTZ;
ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN total_tokens INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN error_message TEXT;
```

---

## Optimal Implementation Order (7 Steps)

### Step 1: Redis + Celery Setup (Day 1, Morning)

**Priority:** CRITICAL - Foundation for async processing
**Time:** 2-3 hours

**Tasks:**

1. **Update `docker-compose.yml`:**
```yaml
services:
  postgres:
    # ... existing config ...

  redis:
    image: redis:7-alpine
    container_name: mnemosyne-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  celery-worker:
    build: .
    container_name: mnemosyne-celery-worker
    command: celery -A backend.worker worker --loglevel=info
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend:/app/backend
      - ./uploads:/app/uploads

  celery-beat:
    build: .
    container_name: mnemosyne-celery-beat
    command: celery -A backend.worker beat --loglevel=info
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0

volumes:
  postgres_data:
  redis_data:
```

2. **Create `backend/worker.py`:**
```python
from celery import Celery
from backend.config import settings

celery_app = Celery(
    "mnemosyne",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.tasks.process_document"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
)
```

3. **Update `pyproject.toml`:**
```toml
[tool.poetry.dependencies]
celery = {extras = ["redis"], version = "^5.3.0"}
redis = "^5.0.0"
```

**Deliverables:**
- Redis running in Docker
- Celery worker configured
- Celery beat scheduler configured
- Workers can connect to Redis

---

### Step 2: File Storage System (Day 1, Afternoon)

**Priority:** HIGH - Need to store uploaded files
**Time:** 2-3 hours

**Tasks:**

1. **Create `backend/storage/` module:**
```python
# backend/storage/local.py
import os
import hashlib
from pathlib import Path
from typing import BinaryIO
from backend.config import settings

class LocalStorage:
    """Local file storage with content-based paths"""

    def __init__(self, base_path: str = settings.UPLOAD_DIR):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, file: BinaryIO, content_hash: str) -> str:
        """
        Save file to local storage using content hash

        Args:
            file: File object to save
            content_hash: SHA-256 hash of content

        Returns:
            str: Relative path to saved file
        """
        # Create subdirectory from first 2 chars of hash (sharding)
        subdir = content_hash[:2]
        file_dir = self.base_path / subdir
        file_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = file_dir / content_hash
        with open(file_path, "wb") as f:
            f.write(file.read())

        return f"{subdir}/{content_hash}"

    def get_path(self, relative_path: str) -> Path:
        """Get absolute path from relative path"""
        return self.base_path / relative_path

    def exists(self, relative_path: str) -> bool:
        """Check if file exists"""
        return self.get_path(relative_path).exists()

    def delete(self, relative_path: str):
        """Delete file"""
        path = self.get_path(relative_path)
        if path.exists():
            path.unlink()
```

2. **Update `backend/config.py`:**
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Storage
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # Celery
    REDIS_URL: str = "redis://redis:6379/0"

    # OpenAI
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 1536
```

3. **Update Document Upload Endpoint:**
```python
# backend/api/documents.py
from backend.storage.local import LocalStorage

storage = LocalStorage()

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_document(
    collection_id: UUID = Form(...),
    file: UploadFile = File(...),
    metadata: Optional[str] = Form("{}"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ... existing validation ...

    # Read file content
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    # ... existing duplicate check ...

    # Save file to storage
    file_path = storage.save(io.BytesIO(content), content_hash)

    # Create document
    document = Document(
        # ... existing fields ...
        content_hash=content_hash,
        status="pending",
        processing_info={"file_path": file_path}
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # Trigger async processing
    from backend.tasks.process_document import process_document_task
    process_document_task.delay(str(document.id))

    return document
```

**Deliverables:**
- Local file storage implemented
- Files saved with content-based paths
- Upload endpoint saves files and triggers processing

---

### Step 3: Database Models for Chunks (Day 2, Morning)

**Priority:** HIGH - Need to store chunks and embeddings
**Time:** 2 hours

**Implementation:**

1. **Create `backend/models/chunk.py`:**
```python
from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from backend.database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    # Embedding (1536 dimensions for text-embedding-3-large)
    embedding = Column(Vector(1536), nullable=False)

    # Metadata
    metadata = Column(JSON, default=dict)
    chunk_metadata = Column(JSON, default=dict)  # Chonkie metadata

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")
    collection = relationship("Collection")
    user = relationship("User")
```

2. **Update `backend/models/document.py`:**
```python
class Document(Base):
    # ... existing fields ...

    # Processing fields
    processed_at = Column(DateTime(timezone=True))
    chunk_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    error_message = Column(Text)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
```

3. **Update `backend/models/__init__.py`:**
```python
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.models.collection import Collection
from backend.models.document import Document
from backend.models.chunk import DocumentChunk

__all__ = ["User", "APIKey", "Collection", "Document", "DocumentChunk"]
```

4. **Create Alembic migration:**
```bash
alembic revision --autogenerate -m "Add document_chunks table and processing fields"
alembic upgrade head
```

**Deliverables:**
- DocumentChunk model created
- Vector column with pgvector
- Cascade deletes configured
- Migration applied

---

### Step 4: Docling Parser Integration (Day 2, Afternoon)

**Priority:** HIGH - Core parsing capability
**Time:** 3-4 hours

**Implementation:**

1. **Update `pyproject.toml`:**
```toml
[tool.poetry.dependencies]
docling = "^1.0.0"  # Document parsing
python-magic = "^0.4.27"  # MIME type detection
```

2. **Create `backend/parsers/docling_parser.py`:**
```python
from pathlib import Path
from typing import Dict, Any
from docling.document_converter import DocumentConverter

class DoclingParser:
    """Parser for documents using Docling (PDF, DOCX, PPTX, etc.)"""

    SUPPORTED_FORMATS = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-powerpoint",
    }

    def __init__(self):
        self.converter = DocumentConverter()

    def can_parse(self, content_type: str) -> bool:
        """Check if this parser can handle the content type"""
        return content_type in self.SUPPORTED_FORMATS

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse document and extract text

        Args:
            file_path: Path to document file

        Returns:
            Dict with:
                - content: Extracted text
                - metadata: Document metadata
                - page_count: Number of pages (if applicable)
        """
        result = self.converter.convert(file_path)

        # Extract text from all pages
        content = result.document.export_to_markdown()

        # Extract metadata
        metadata = {
            "page_count": len(result.document.pages) if hasattr(result.document, "pages") else None,
            "title": result.document.title if hasattr(result.document, "title") else None,
            "language": result.document.language if hasattr(result.document, "language") else None,
        }

        return {
            "content": content,
            "metadata": metadata,
            "page_count": metadata["page_count"],
        }
```

3. **Create fallback parser for plain text:**
```python
# backend/parsers/text_parser.py
class TextParser:
    """Parser for plain text files"""

    SUPPORTED_FORMATS = {
        "text/plain",
        "text/markdown",
        "text/html",
    }

    def can_parse(self, content_type: str) -> bool:
        return content_type in self.SUPPORTED_FORMATS

    async def parse(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "content": content,
            "metadata": {},
            "page_count": None,
        }
```

4. **Create parser factory:**
```python
# backend/parsers/__init__.py
from backend.parsers.docling_parser import DoclingParser
from backend.parsers.text_parser import TextParser

class ParserFactory:
    """Factory for selecting appropriate parser based on content type"""

    def __init__(self):
        self.parsers = [
            DoclingParser(),
            TextParser(),
        ]

    def get_parser(self, content_type: str):
        """Get parser for content type"""
        for parser in self.parsers:
            if parser.can_parse(content_type):
                return parser

        raise ValueError(f"No parser available for content type: {content_type}")
```

**Deliverables:**
- Docling parser implemented
- Text parser as fallback
- Parser factory for selection
- Supports PDF, DOCX, PPTX, TXT

---

### Step 5: Chonkie Chunking Integration (Day 3, Morning)

**Priority:** HIGH - Intelligent chunking
**Time:** 3 hours

**Implementation:**

1. **Update `pyproject.toml`:**
```toml
[tool.poetry.dependencies]
chonkie = "^0.1.0"  # Intelligent chunking
tiktoken = "^0.5.0"  # Token counting
```

2. **Create `backend/chunking/chonkie_chunker.py`:**
```python
from typing import List, Dict, Any
from chonkie import SemanticChunker
import tiktoken

class ChonkieChunker:
    """Intelligent chunking using Chonkie"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 128,
        embedding_model: str = "text-embedding-3-large"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = SemanticChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=embedding_model
        )
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk text using semantic chunking

        Args:
            text: Input text to chunk

        Returns:
            List of chunks with metadata
        """
        # Use Chonkie for semantic chunking
        chunks = self.chunker.chunk(text)

        # Convert to our format
        result = []
        for idx, chunk in enumerate(chunks):
            tokens = len(self.tokenizer.encode(chunk.text))
            result.append({
                "content": chunk.text,
                "chunk_index": idx,
                "metadata": {
                    "type": "semantic",
                    "tokens": tokens,
                    "start_char": chunk.start_index,
                    "end_char": chunk.end_index,
                }
            })

        return result
```

**Deliverables:**
- Chonkie integration complete
- Semantic chunking working
- Token counting included
- Chunk metadata preserved

---

### Step 6: OpenAI Embeddings (Day 3, Afternoon)

**Priority:** CRITICAL - Required for vector search
**Time:** 2 hours

**Implementation:**

1. **Update `pyproject.toml`:**
```toml
[tool.poetry.dependencies]
openai = "^1.0.0"
```

2. **Create `backend/embeddings/openai_embedder.py`:**
```python
from typing import List
import asyncio
from openai import AsyncOpenAI
from backend.config import settings

class OpenAIEmbedder:
    """Generate embeddings using OpenAI API"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for batch of texts

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        # OpenAI has max batch size of 2048
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            response = await self.client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions
            )

            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        embeddings = await self.embed_batch([text])
        return embeddings[0]
```

**Deliverables:**
- OpenAI client configured
- Batch embedding support
- Error handling for API failures
- Rate limiting handled

---

### Step 7: Document Processing Task (Day 4-5)

**Priority:** CRITICAL - Ties everything together
**Time:** 6-8 hours

**Implementation:**

1. **Create `backend/tasks/process_document.py`:**
```python
from celery import Task
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import logging

from backend.worker import celery_app
from backend.database import SessionLocal
from backend.models.document import Document
from backend.models.chunk import DocumentChunk
from backend.storage.local import LocalStorage
from backend.parsers import ParserFactory
from backend.chunking.chonkie_chunker import ChonkieChunker
from backend.embeddings.openai_embedder import OpenAIEmbedder

logger = logging.getLogger(__name__)

class ProcessDocumentTask(Task):
    """Celery task for processing documents"""

    def __init__(self):
        self.storage = LocalStorage()
        self.parser_factory = ParserFactory()
        self.chunker = ChonkieChunker()
        self.embedder = OpenAIEmbedder()

    def run(self, document_id: str):
        """
        Process document: parse → chunk → embed → store

        Args:
            document_id: UUID of document to process
        """
        db = SessionLocal()

        try:
            # Get document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return

            # Update status to processing
            document.status = "processing"
            document.processing_info["started_at"] = datetime.utcnow().isoformat()
            db.commit()

            # Step 1: Parse document
            logger.info(f"Parsing document {document_id}")
            file_path = self.storage.get_path(document.processing_info["file_path"])
            parser = self.parser_factory.get_parser(document.content_type)
            parsed = parser.parse(str(file_path))

            # Step 2: Chunk text
            logger.info(f"Chunking document {document_id}")
            chunks = self.chunker.chunk(parsed["content"])

            # Step 3: Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            texts = [chunk["content"] for chunk in chunks]
            embeddings = asyncio.run(self.embedder.embed_batch(texts))

            # Step 4: Store chunks
            logger.info(f"Storing {len(chunks)} chunks")
            for chunk_data, embedding in zip(chunks, embeddings):
                chunk = DocumentChunk(
                    document_id=document.id,
                    collection_id=document.collection_id,
                    user_id=document.user_id,
                    content=chunk_data["content"],
                    chunk_index=chunk_data["chunk_index"],
                    embedding=embedding,
                    chunk_metadata=chunk_data["metadata"]
                )
                db.add(chunk)

            # Update document
            document.status = "completed"
            document.processed_at = datetime.utcnow()
            document.chunk_count = len(chunks)
            document.total_tokens = sum(c["metadata"]["tokens"] for c in chunks)
            document.processing_info["completed_at"] = datetime.utcnow().isoformat()

            db.commit()
            logger.info(f"Document {document_id} processed successfully")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")

            # Update status to failed
            if document:
                document.status = "failed"
                document.error_message = str(e)
                document.processing_info["error"] = str(e)
                document.processing_info["failed_at"] = datetime.utcnow().isoformat()
                db.commit()

            raise

        finally:
            db.close()

# Register task
process_document_task = celery_app.task(bind=True, base=ProcessDocumentTask, name="process_document")
```

2. **Create status check endpoint:**
```python
# backend/api/documents.py

@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document processing status"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise http_404_not_found("Document not found")

    return {
        "document_id": document.id,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "total_tokens": document.total_tokens,
        "error_message": document.error_message,
        "processing_info": document.processing_info,
        "created_at": document.created_at,
        "processed_at": document.processed_at,
    }
```

**Deliverables:**
- Complete processing pipeline working
- Status updates throughout process
- Error handling and logging
- Status check endpoint

---

## Week 2 Success Criteria

Week 2 is complete when:
1. Document upload triggers async Celery task
2. Status changes: pending → processing → completed
3. Documents are parsed with Docling
4. Text is chunked with Chonkie (semantic)
5. Embeddings generated with OpenAI
6. Chunks stored in pgvector
7. Can query document status
8. Failed documents show error message
9. Celery worker runs in Docker
10. All processing is asynchronous

---

## Testing Strategy

### Manual Testing Flow:

1. **Start all services:**
```bash
docker-compose up -d
```

2. **Upload a PDF document:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -F "collection_id=$COLLECTION_ID" \
  -F "file=@test.pdf"

# Response: {"id": "...", "status": "pending", ...}
```

3. **Check processing status:**
```bash
curl -X GET "http://localhost:8000/api/v1/documents/{document_id}/status" \
  -H "Authorization: Bearer $API_KEY"

# Response: {"status": "processing", ...}
```

4. **Wait for completion and check again:**
```bash
# After a few seconds
curl -X GET "http://localhost:8000/api/v1/documents/{document_id}/status" \
  -H "Authorization: Bearer $API_KEY"

# Response: {"status": "completed", "chunk_count": 15, ...}
```

5. **Verify chunks in database:**
```sql
SELECT COUNT(*) FROM document_chunks WHERE document_id = '...';
-- Should match chunk_count
```

---

## What's NOT in Week 2

- Vector similarity search (Week 3)
- Hybrid search (Week 3)
- Reranking (Week 3)
- Chat API (Week 3)
- LightRAG integration (Week 3-4)
- External connectors (Week 4+)
- Additional file format parsers (Week 4+)

---

## Estimated Timeline

| Day | Tasks | Hours |
|-----|-------|-------|
| Day 1 | Redis + Celery + File Storage | 5-6 |
| Day 2 | Chunk models + Docling parser | 5-6 |
| Day 3 | Chonkie chunking + OpenAI embeddings | 5 |
| Day 4-5 | Processing task + testing + polish | 8-10 |

**Total:** ~25-30 hours over 5 days

---

## Next Week Preview

**Week 3: Vector Search + Retrieval API**
- Implement vector similarity search
- Add hybrid search (semantic + keyword)
- Implement reranking
- Create `/retrievals` endpoint
- Integrate LightRAG (optional)
