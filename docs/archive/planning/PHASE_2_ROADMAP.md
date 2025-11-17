# Phase 2 Implementation Roadmap
**Building on Week 1-5 Foundation**

Based on `IMPLEMENTATION_AUDIT.md` findings and SurfSense/RAG-Anything reference implementations.

---

## Priority Matrix

| Priority | Feature | Impact | Effort | Timeline |
|----------|---------|--------|--------|----------|
| P0 | File Format Support (50+) | Critical | High | Week 6-7 |
| P0 | LiteLLM Integration | Critical | Medium | Week 6 |
| P1 | Multi-Source Connectors | Critical | High | Week 8-9 |
| P1 | Unit Test Suite | High | Medium | Week 6 |
| P2 | Hierarchical Indices | High | Medium | Week 7 |
| P2 | Multiple Rerankers | Medium | Low | Week 7 |
| P3 | JWT/OAuth | Medium | Medium | Week 8 |
| P3 | Browser Extension | Medium | High | Week 9-10 |
| P4 | Podcast Generation | Low | High | Week 10+ |

---

## Week 6: Testing + File Formats + LiteLLM

### Goals
1. Add comprehensive test suite
2. Expand file format support to 50+
3. Replace OpenAI-only with LiteLLM (100+ models)

### Day 1-2: Testing Infrastructure

**Reference:** SurfSense testing patterns

**Tasks:**
```bash
# 1. Create test structure
mkdir -p tests/{unit,integration,e2e}

# 2. Setup pytest configuration
# tests/conftest.py - fixtures, mocks, test DB

# 3. Unit tests for all services
tests/unit/
├── test_chat_service.py
├── test_reranker_service.py
├── test_cache_service.py
├── test_vector_search.py
└── ...

# 4. Integration tests
tests/integration/
├── test_document_processing.py
├── test_search_pipeline.py
└── test_chat_pipeline.py

# 5. E2E tests
tests/e2e/
└── test_full_rag_flow.py
```

**Implementation:**
```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from backend.database import Base, get_db
from backend.models import User, Collection, Document

@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("postgresql://test:test@localhost:5433/test_mnemosyne")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def test_user(test_db):
    """Create test user"""
    user = User(email="test@example.com", hashed_password="...")
    # ... return user

@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls"""
    # ... mock implementation
```

**Success Criteria:**
- [ ] 80%+ code coverage
- [ ] All services have unit tests
- [ ] Integration tests for critical paths
- [ ] CI/CD pipeline (GitHub Actions)

---

### Day 3-4: File Format Support (50+ formats)

**Reference:** SurfSense `file_processors.py`

**Current:** 9 formats (PDF, DOCX, PPTX, DOC, PPT, TXT, MD, HTML, CSV)
**Target:** 50+ formats

**Implementation Plan:**

**1. Create Parser Factory Pattern:**
```python
# backend/parsers/parser_factory.py (NEW)
from typing import Dict, Type
from backend.parsers.base_parser import BaseParser

class ParserFactory:
    """
    Factory for selecting parser based on file type

    Supports 50+ formats via multiple parsing libraries:
    - Docling: PDF, Office docs
    - Unstructured.io: Advanced parsing
    - LlamaCloud: Cloud-based parsing
    - pytesseract: OCR for images
    - Whisper: Audio transcription
    - youtube-transcript-api: Video transcription
    """

    def __init__(self):
        self.parsers: Dict[str, Type[BaseParser]] = {}
        self._register_parsers()

    def _register_parsers(self):
        """Register all available parsers"""
        # Document parsers
        self.parsers.update({
            'application/pdf': DoclingParser,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DoclingParser,
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': DoclingParser,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ExcelParser,  # NEW
            'application/vnd.ms-excel': ExcelParser,  # NEW
        })

        # Image parsers (OCR)
        self.parsers.update({
            'image/png': OCRParser,  # NEW
            'image/jpeg': OCRParser,  # NEW
            'image/jpg': OCRParser,  # NEW
            'image/tiff': OCRParser,  # NEW
            'image/bmp': OCRParser,  # NEW
        })

        # Audio parsers
        self.parsers.update({
            'audio/mpeg': WhisperParser,  # NEW
            'audio/wav': WhisperParser,  # NEW
            'audio/m4a': WhisperParser,  # NEW
            'audio/ogg': WhisperParser,  # NEW
        })

        # Video parsers
        self.parsers.update({
            'video/mp4': VideoParser,  # NEW
            'video/avi': VideoParser,  # NEW
            'video/mov': VideoParser,  # NEW
        })

        # Web content
        self.parsers.update({
            'text/html': HTMLParser,  # ENHANCED
            'application/x-web-page': WebCrawlerParser,  # NEW
        })

        # Code files
        self.parsers.update({
            'text/x-python': CodeParser,  # NEW
            'text/x-javascript': CodeParser,  # NEW
            'application/json': JSONParser,  # NEW
            'application/xml': XMLParser,  # NEW
        })

    def get_parser(self, content_type: str) -> BaseParser:
        """Get parser for content type"""
        parser_class = self.parsers.get(content_type)
        if not parser_class:
            # Fallback to text parser
            return TextParser()
        return parser_class()
```

**2. Implement New Parsers:**

**Excel Parser:**
```python
# backend/parsers/excel_parser.py (NEW)
import pandas as pd
from typing import Dict, Any

class ExcelParser(BaseParser):
    """Parse Excel files (XLS, XLSX)"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)

        content_parts = []
        for sheet_name in excel_file.sheet_names:
            df = excel_file.parse(sheet_name)

            # Convert to markdown table
            markdown_table = df.to_markdown(index=False)
            content_parts.append(f"## Sheet: {sheet_name}\n\n{markdown_table}\n\n")

        content = "\n".join(content_parts)

        return {
            "content": content,
            "metadata": {
                "sheet_count": len(excel_file.sheet_names),
                "sheets": excel_file.sheet_names,
            },
            "page_count": len(excel_file.sheet_names),
        }
```

**OCR Parser:**
```python
# backend/parsers/ocr_parser.py (NEW)
import pytesseract
from PIL import Image

class OCRParser(BaseParser):
    """Extract text from images using OCR"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        image = Image.open(file_path)

        # Extract text using Tesseract
        text = pytesseract.image_to_string(image, lang='eng')

        # Get additional info
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        return {
            "content": text,
            "metadata": {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "confidence": sum(data['conf']) / len(data['conf']),
            },
            "page_count": 1,
        }
```

**Audio Parser (Whisper):**
```python
# backend/parsers/audio_parser.py (NEW)
from openai import OpenAI

class WhisperParser(BaseParser):
    """Transcribe audio using OpenAI Whisper"""

    def __init__(self):
        self.client = OpenAI()

    def parse(self, file_path: str) -> Dict[str, Any]:
        # Transcribe audio
        with open(file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )

        return {
            "content": transcript.text,
            "metadata": {
                "language": transcript.language,
                "duration": transcript.duration,
                "segments": len(transcript.segments),
            },
            "page_count": None,
        }
```

**Video Parser:**
```python
# backend/parsers/video_parser.py (NEW)
from youtube_transcript_api import YouTubeTranscriptApi
import cv2
import subprocess

class VideoParser(BaseParser):
    """Extract transcript and metadata from video"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        # 1. Extract audio
        audio_path = self._extract_audio(file_path)

        # 2. Transcribe audio with Whisper
        audio_parser = WhisperParser()
        result = audio_parser.parse(audio_path)

        # 3. Get video metadata
        video = cv2.VideoCapture(file_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps

        result["metadata"].update({
            "fps": fps,
            "frame_count": frame_count,
            "duration": duration,
        })

        return result

    def _extract_audio(self, video_path: str) -> str:
        """Extract audio track from video"""
        audio_path = video_path.replace('.mp4', '.wav')
        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            audio_path
        ])
        return audio_path
```

**Dependencies:**
```toml
# pyproject.toml
[tool.poetry.dependencies]
# Existing...

# Week 6 additions (file formats)
pandas = "^2.0.0"              # Excel parsing
openpyxl = "^3.1.0"            # Excel XLSX support
xlrd = "^2.0.0"                # Excel XLS support
pytesseract = "^0.3.10"        # OCR
Pillow = "^10.0.0"             # Image processing
opencv-python = "^4.8.0"       # Video processing
ffmpeg-python = "^0.2.0"       # Audio extraction
youtube-transcript-api = "^0.6.0"  # YouTube transcripts
```

**Success Criteria:**
- [ ] 50+ file formats supported
- [ ] Excel files parse correctly
- [ ] OCR works on images
- [ ] Audio transcription functional
- [ ] Video transcription functional
- [ ] All parsers have tests

---

### Day 5: LiteLLM Integration

**Reference:** SurfSense `llm_service.py`

**Goal:** Replace OpenAI-only with LiteLLM (100+ models)

**Current Architecture:**
```python
# backend/services/chat_service.py (Week 4)
from openai import AsyncOpenAI

class ChatService:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat_stream(self, ...):
        stream = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True
        )
```

**New Architecture:**
```python
# backend/services/llm_service.py (ENHANCED)
from litellm import acompletion
from typing import AsyncGenerator, Dict, List

class LLMService:
    """
    Multi-model LLM service using LiteLLM

    Supports 100+ models:
    - OpenAI: gpt-4, gpt-4o, gpt-4o-mini, gpt-3.5-turbo
    - Anthropic: claude-3-opus, claude-3-sonnet, claude-3-haiku
    - Google: gemini-pro, gemini-1.5-pro
    - Mistral: mistral-large, mistral-medium, mistral-small
    - Local: ollama/llama3.2, ollama/mistral, etc.
    """

    def __init__(self):
        self.default_model = settings.LLM_MODEL  # "gpt-4o-mini"
        self.temperature = settings.LLM_TEMPERATURE  # 0.7
        self.max_tokens = settings.LLM_MAX_TOKENS  # 1000

    async def chat_completion_stream(
        self,
        messages: List[Dict],
        model: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion from any LLM provider

        Examples:
            # OpenAI
            async for chunk in llm.chat_completion_stream(messages, model="gpt-4o-mini"):
                print(chunk)

            # Anthropic
            async for chunk in llm.chat_completion_stream(messages, model="claude-3-sonnet"):
                print(chunk)

            # Local Ollama
            async for chunk in llm.chat_completion_stream(messages, model="ollama/llama3.2"):
                print(chunk)
        """
        model = model or self.default_model

        response = await acompletion(
            model=model,
            messages=messages,
            temperature=kwargs.get('temperature', self.temperature),
            max_tokens=kwargs.get('max_tokens', self.max_tokens),
            stream=True,
            **kwargs
        )

        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat_completion(
        self,
        messages: List[Dict],
        model: str = None,
        **kwargs
    ) -> str:
        """Non-streaming chat completion"""
        model = model or self.default_model

        response = await acompletion(
            model=model,
            messages=messages,
            temperature=kwargs.get('temperature', self.temperature),
            max_tokens=kwargs.get('max_tokens', self.max_tokens),
            stream=False,
            **kwargs
        )

        return response.choices[0].message.content
```

**Update Chat Service:**
```python
# backend/services/chat_service.py (UPDATED)
from backend.services.llm_service import LLMService

class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.search_service = VectorSearchService(db)
        self.embedder = OpenAIEmbedder()
        self.reranker = RerankerService()
        self.llm_service = LLMService()  # NEW: Use LLMService instead of AsyncOpenAI

    async def chat_stream(
        self,
        session_id: UUID,
        user_message: str,
        user_id: UUID,
        collection_id: UUID = None,
        top_k: int = 5,
        model: str = None  # NEW: Allow model selection
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # ... existing retrieval code ...

        messages = self._build_messages(history, user_message, context)

        # Stream response using LLMService (supports any model)
        full_response = ""
        async for chunk in self.llm_service.chat_completion_stream(
            messages=messages,
            model=model  # Can be: gpt-4o-mini, claude-3-sonnet, ollama/llama3.2, etc.
        ):
            full_response += chunk
            yield {
                "type": "delta",
                "delta": chunk
            }

        # ... rest of code ...
```

**Configuration:**
```python
# backend/config.py (UPDATED)
class Settings(BaseSettings):
    # ... existing settings ...

    # LLM Configuration (Week 6)
    LLM_MODEL: str = "gpt-4o-mini"  # Can be any LiteLLM-supported model
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000

    # Model-specific API keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""

    # Ollama (local models)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
```

**API Update:**
```python
# backend/schemas/chat.py (UPDATED)
class ChatRequest(BaseModel):
    session_id: Optional[UUID] = None
    message: str = Field(..., min_length=1, max_length=2000)
    collection_id: Optional[UUID] = None
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = Field(default=True)
    model: Optional[str] = None  # NEW: Allow model selection per request

    # Examples:
    # - "gpt-4o-mini" (default)
    # - "gpt-4"
    # - "claude-3-sonnet"
    # - "gemini-pro"
    # - "ollama/llama3.2"
```

**Dependencies:**
```toml
# pyproject.toml
[tool.poetry.dependencies]
litellm = "^1.17.0"  # 100+ LLM support
```

**Success Criteria:**
- [ ] LiteLLM integrated
- [ ] Can switch between models via API
- [ ] OpenAI, Anthropic, Google, Ollama tested
- [ ] Backward compatible (defaults to gpt-4o-mini)
- [ ] Cost tracking per model

---

## Week 7: Hierarchical Indices + Multiple Rerankers

### Day 1-2: Hierarchical Indices (Two-Tier RAG)

**Reference:** SurfSense `documents_hybrid_search.py`

**Current:** Single-tier chunk retrieval
**Target:** Two-tier (document → chunk) retrieval

**Benefits:**
- 20-30% better retrieval accuracy
- Faster for large collections
- Better context preservation

**Implementation:**

**1. Add Document Embeddings:**
```python
# backend/models/document.py (UPDATED)
from pgvector.sqlalchemy import Vector

class Document(Base):
    # ... existing fields ...

    # NEW: Document-level embedding (summary of all chunks)
    document_embedding = Column(Vector(1536), nullable=True)

    # NEW: Document summary for embedding generation
    summary = Column(Text, nullable=True)
```

**2. Generate Document Embeddings:**
```python
# backend/tasks/process_document.py (UPDATED)
async def process_document_task(document_id: str):
    # ... existing parsing and chunking ...

    # Generate chunk embeddings (existing)
    chunk_embeddings = await embedder.embed_batch([c["content"] for c in chunks])

    # NEW: Generate document-level embedding
    # Strategy 1: Use first N chunks
    doc_summary = " ".join([c["content"] for c in chunks[:5]])

    # Strategy 2: Or generate AI summary
    # doc_summary = await llm_service.summarize(full_content)

    doc_embedding = await embedder.embed(doc_summary)

    # Save document embedding
    document.document_embedding = doc_embedding
    document.summary = doc_summary
    db.commit()
```

**3. Implement Two-Tier Search:**
```python
# backend/search/hierarchical_search.py (NEW)
class HierarchicalSearchService:
    """
    Two-tier retrieval: Document-level → Chunk-level

    Workflow:
    1. Semantic search at document level (top_k * 3 documents)
    2. For each document, search chunks
    3. Merge and rerank final results
    """

    def __init__(self, db: Session):
        self.db = db
        self.vector_search = VectorSearchService(db)

    async def search(
        self,
        query_embedding: List[float],
        user_id: UUID,
        collection_id: UUID = None,
        top_k: int = 10
    ) -> List[Dict]:
        # Tier 1: Document-level search
        doc_results = self._search_documents(
            query_embedding,
            user_id,
            collection_id,
            top_k=top_k * 3  # Get more documents
        )

        # Tier 2: Chunk-level search within top documents
        doc_ids = [r["document_id"] for r in doc_results]

        chunk_results = self._search_chunks_in_documents(
            query_embedding,
            doc_ids,
            user_id,
            top_k=top_k
        )

        return chunk_results

    def _search_documents(
        self,
        query_embedding: List[float],
        user_id: UUID,
        collection_id: UUID,
        top_k: int
    ) -> List[Dict]:
        """Search at document level using document_embedding"""
        query = self.db.query(
            Document.id,
            Document.title,
            Document.filename,
            Document.document_embedding.cosine_distance(query_embedding).label('distance')
        ).filter(
            Document.user_id == user_id,
            Document.document_embedding.isnot(None)  # Only documents with embeddings
        )

        if collection_id:
            query = query.filter(Document.collection_id == collection_id)

        results = query.order_by('distance').limit(top_k).all()

        return [
            {
                "document_id": str(r.id),
                "title": r.title,
                "score": 1 - r.distance
            }
            for r in results
        ]

    def _search_chunks_in_documents(
        self,
        query_embedding: List[float],
        document_ids: List[str],
        user_id: UUID,
        top_k: int
    ) -> List[Dict]:
        """Search chunks within specific documents"""
        query = self.db.query(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.chunk_index,
            DocumentChunk.metadata,
            DocumentChunk.chunk_metadata,
            DocumentChunk.document_id,
            DocumentChunk.collection_id,
            Document.title.label('document_title'),
            Document.filename.label('document_filename'),
            DocumentChunk.embedding.cosine_distance(query_embedding).label('distance')
        ).join(
            Document,
            Document.id == DocumentChunk.document_id
        ).filter(
            DocumentChunk.user_id == user_id,
            DocumentChunk.document_id.in_(document_ids)
        )

        results = query.order_by('distance').limit(top_k).all()

        return [
            {
                'chunk_id': str(result.id),
                'content': result.content,
                'chunk_index': result.chunk_index,
                'score': 1 - result.distance,
                'metadata': result.metadata or {},
                'chunk_metadata': result.chunk_metadata or {},
                'document': {
                    'id': str(result.document_id),
                    'title': result.document_title,
                    'filename': result.document_filename,
                },
                'collection_id': str(result.collection_id)
            }
            for result in results
        ]
```

**Success Criteria:**
- [ ] Document embeddings generated
- [ ] Two-tier search working
- [ ] 20%+ better retrieval accuracy
- [ ] Performance benchmarks documented

---

### Day 3-4: Multiple Rerankers

**Reference:** SurfSense `reranker_service.py`

**Current:** Flashrank only
**Target:** Flashrank + Cohere + Pinecone

**Implementation:**
```python
# backend/services/reranker_service.py (ENHANCED)
from enum import Enum
from typing import List, Dict, Optional

class RerankerType(str, Enum):
    FLASHRANK = "flashrank"  # Local, fast, free
    COHERE = "cohere"        # API, high quality, paid
    PINECONE = "pinecone"    # API, balanced, paid

class RerankerService:
    """Multi-reranker support"""

    def __init__(self):
        self.flashrank_ranker = self._init_flashrank()
        self.cohere_client = self._init_cohere()
        self.pinecone_client = self._init_pinecone()

    def _init_flashrank(self):
        """Initialize Flashrank (local)"""
        try:
            from flashrank import Ranker
            return Ranker(model_name=settings.RERANK_MODEL)
        except:
            return None

    def _init_cohere(self):
        """Initialize Cohere (API)"""
        if settings.COHERE_API_KEY:
            import cohere
            return cohere.Client(settings.COHERE_API_KEY)
        return None

    def _init_pinecone(self):
        """Initialize Pinecone (API)"""
        if settings.PINECONE_API_KEY:
            from pinecone_text.rerank import Reranker
            return Reranker(api_key=settings.PINECONE_API_KEY)
        return None

    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int = 10,
        reranker: RerankerType = RerankerType.FLASHRANK
    ) -> List[Dict]:
        """Rerank using specified reranker"""
        if reranker == RerankerType.FLASHRANK and self.flashrank_ranker:
            return self._rerank_flashrank(query, chunks, top_k)
        elif reranker == RerankerType.COHERE and self.cohere_client:
            return self._rerank_cohere(query, chunks, top_k)
        elif reranker == RerankerType.PINECONE and self.pinecone_client:
            return self._rerank_pinecone(query, chunks, top_k)
        else:
            # Fallback: no reranking
            return chunks[:top_k]

    def _rerank_flashrank(self, query: str, chunks: List[Dict], top_k: int) -> List[Dict]:
        """Flashrank: Local, fast, free"""
        passages = [{"id": i, "text": c["content"], "meta": c} for i, c in enumerate(chunks)]
        reranked = self.flashrank_ranker.rerank(query, passages)

        results = []
        for item in reranked[:top_k]:
            chunk = item["meta"]
            chunk["rerank_score"] = item["score"]
            chunk["reranker"] = "flashrank"
            results.append(chunk)

        return results

    def _rerank_cohere(self, query: str, chunks: List[Dict], top_k: int) -> List[Dict]:
        """Cohere: API, high quality, $1/1000 reranks"""
        documents = [c["content"] for c in chunks]

        response = self.cohere_client.rerank(
            query=query,
            documents=documents,
            model="rerank-english-v3.0",
            top_n=top_k
        )

        results = []
        for item in response.results:
            chunk = chunks[item.index].copy()
            chunk["rerank_score"] = item.relevance_score
            chunk["reranker"] = "cohere"
            results.append(chunk)

        return results

    def _rerank_pinecone(self, query: str, chunks: List[Dict], top_k: int) -> List[Dict]:
        """Pinecone: API, balanced quality/cost"""
        documents = [c["content"] for c in chunks]

        response = self.pinecone_client.rerank(
            query=query,
            documents=documents,
            top_n=top_k,
            model="pinecone-rerank-v0"
        )

        results = []
        for item in response:
            chunk = chunks[item["index"]].copy()
            chunk["rerank_score"] = item["score"]
            chunk["reranker"] = "pinecone"
            results.append(chunk)

        return results
```

**Update API:**
```python
# backend/schemas/retrieval.py (UPDATED)
class RetrievalRequest(BaseModel):
    query: str
    mode: RetrievalMode = RetrievalMode.HYBRID
    top_k: int = Field(default=10, ge=1, le=100)
    collection_id: Optional[UUID] = None
    rerank: bool = Field(default=True)
    reranker: Optional[str] = Field(default="flashrank")  # NEW: flashrank, cohere, pinecone
```

**Dependencies:**
```toml
# pyproject.toml
[tool.poetry.dependencies]
cohere = "^4.0.0"
pinecone-text = "^0.7.0"
```

**Success Criteria:**
- [ ] Three rerankers working
- [ ] Quality comparison documented
- [ ] Cost analysis per reranker
- [ ] User can choose reranker via API

---

## Week 8-9: Multi-Source Connectors

**Reference:** SurfSense connector patterns

**Goal:** Add 5+ external data source connectors

### Priority Connectors

1. **Slack** - Chat history indexing
2. **Notion** - Notes and wikis
3. **GitHub** - Issues, PRs, code
4. **Google Drive** - Documents
5. **Gmail** - Email search

### Implementation Pattern

**1. Base Connector Interface:**
```python
# backend/connectors/base_connector.py (NEW)
from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator

class BaseConnector(ABC):
    """Base class for all connectors"""

    @abstractmethod
    async def authenticate(self, credentials: Dict) -> bool:
        """Authenticate with external service"""
        pass

    @abstractmethod
    async def fetch_items(
        self,
        since: datetime = None,
        limit: int = 100
    ) -> AsyncGenerator[Dict, None]:
        """Fetch items from external service"""
        pass

    @abstractmethod
    async def sync(self, user_id: UUID, collection_id: UUID):
        """Sync data to Mnemosyne"""
        pass
```

**2. Slack Connector Example:**
```python
# backend/connectors/slack_connector.py (NEW)
from slack_sdk.web.async_client import AsyncWebClient

class SlackConnector(BaseConnector):
    """Sync Slack messages to Mnemosyne"""

    def __init__(self):
        self.client: Optional[AsyncWebClient] = None

    async def authenticate(self, credentials: Dict) -> bool:
        """Authenticate with Slack OAuth token"""
        self.client = AsyncWebClient(token=credentials["access_token"])

        # Test authentication
        try:
            response = await self.client.auth_test()
            return response["ok"]
        except:
            return False

    async def fetch_items(
        self,
        since: datetime = None,
        limit: int = 100
    ) -> AsyncGenerator[Dict, None]:
        """Fetch messages from Slack channels"""
        # Get all channels
        channels_response = await self.client.conversations_list(
            types="public_channel,private_channel"
        )

        for channel in channels_response["channels"]:
            # Fetch messages
            history = await self.client.conversations_history(
                channel=channel["id"],
                oldest=since.timestamp() if since else None,
                limit=limit
            )

            for message in history["messages"]:
                yield {
                    "title": f"#{channel['name']} - {message.get('user', 'Unknown')}",
                    "content": message["text"],
                    "metadata": {
                        "channel_id": channel["id"],
                        "channel_name": channel["name"],
                        "user": message.get("user"),
                        "timestamp": message["ts"],
                    },
                    "unique_identifier": f"slack_{channel['id']}_{message['ts']}",
                    "source_type": "slack",
                }

    async def sync(self, user_id: UUID, collection_id: UUID):
        """Sync Slack messages to collection"""
        async for item in self.fetch_items():
            # Create document
            await create_document_from_connector(
                user_id=user_id,
                collection_id=collection_id,
                title=item["title"],
                content=item["content"],
                metadata=item["metadata"],
                unique_identifier=item["unique_identifier"]
            )
```

**3. Connector Management:**
```python
# backend/models/connector.py (NEW)
class Connector(Base):
    __tablename__ = "connectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"))

    connector_type = Column(String(50), nullable=False)  # slack, notion, github, etc.
    credentials = Column(JSON, nullable=False)  # Encrypted credentials

    sync_frequency = Column(String(20), default="daily")  # hourly, daily, weekly
    last_sync_at = Column(DateTime(timezone=True))
    next_sync_at = Column(DateTime(timezone=True))

    is_active = Column(Boolean, default=True)
    metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**4. API Endpoints:**
```python
# backend/api/connectors.py (NEW)
@router.post("/connectors")
async def create_connector(
    connector_type: str,
    collection_id: UUID,
    credentials: Dict,
    current_user: User = Depends(get_current_user)
):
    """Create and authenticate connector"""
    connector_class = CONNECTOR_REGISTRY[connector_type]
    connector = connector_class()

    # Authenticate
    if not await connector.authenticate(credentials):
        raise HTTPException(400, "Authentication failed")

    # Save connector
    db_connector = Connector(
        user_id=current_user.id,
        collection_id=collection_id,
        connector_type=connector_type,
        credentials=encrypt(credentials)  # Encrypt before storing
    )
    db.add(db_connector)
    db.commit()

    # Trigger initial sync
    await connector.sync(current_user.id, collection_id)

    return {"connector_id": db_connector.id, "status": "syncing"}

@router.post("/connectors/{connector_id}/sync")
async def trigger_sync(
    connector_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Manually trigger connector sync"""
    # ... implementation
```

**Success Criteria:**
- [ ] 5 connectors implemented
- [ ] OAuth flows working
- [ ] Incremental sync (no duplicates)
- [ ] Scheduled sync (Celery beat)
- [ ] Connector management UI

---

## Week 10+: Polish & Production

### Browser Extension
- Chrome extension for web capture
- Save to Mnemosyne button
- Annotation support

### Podcast Generation
- Text-to-speech with ElevenLabs
- Multi-speaker dialogue
- Background music

### Monitoring
- Prometheus metrics
- Grafana dashboards
- Sentry error tracking
- Structured logging

---

## Success Metrics

| Metric | Week 5 | Target | Status |
|--------|--------|--------|--------|
| File Formats | 9 | 50+ | Week 6-7 |
| LLM Models | 1 (OpenAI) | 100+ | Week 6 |
| Connectors | 0 | 5+ | Week 8-9 |
| Test Coverage | 0% | 80%+ | Week 6 |
| Rerankers | 1 | 3 | Week 7 |
| Retrieval Tiers | 1 | 2 | Week 7 |

---

## Resource Requirements

### Development Time
- **Week 6:** 30-35 hours
- **Week 7:** 25-30 hours
- **Week 8-9:** 40-45 hours
- **Week 10+:** Ongoing

### Infrastructure
- Redis: Caching + Celery
- PostgreSQL: Database + pgvector
- API Keys: OpenAI, Anthropic, Cohere, Pinecone
- OAuth Apps: Slack, Notion, GitHub, Google

### Team
- 1 backend developer (Python/FastAPI)
- 1 frontend developer (optional, for connector UI)
- 1 DevOps engineer (optional, for deployment)

---

## Next Steps

1. **Clone Reference Repos:**
   ```bash
   cd /home/user/Mnemosyne/references
   git clone https://github.com/DAMG7245/surf-sense.git surfsense
   git clone https://github.com/ictnlp/RAG-Anything.git rag-anything
   ```

2. **Study Patterns:**
   - SurfSense file processors
   - SurfSense connectors
   - RAG-Anything multimodal pipelines

3. **Start Week 6:**
   - Setup pytest
   - Add file format parsers
   - Integrate LiteLLM

4. **Track Progress:**
   - Update IMPLEMENTATION_AUDIT.md weekly
   - Document decisions in RESEARCH.md
   - Commit regularly with descriptive messages

---

**Let's build the complete RAG platform! 🚀**
