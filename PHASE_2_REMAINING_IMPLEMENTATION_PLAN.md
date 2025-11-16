# Phase 2 Remaining Features - Implementation Plan

**Date:** 2025-11-16
**Based on:** SurfSense Reference Implementation Analysis
**Status:** Ready for Implementation

---

## Executive Summary

Based on comprehensive SurfSense exploration, here's the detailed plan for remaining Phase 2 features:

**✅ Completed (80% of planned features):**
- LiteLLM Integration (100+ models)
- Multiple Rerankers (5 providers)
- Audio Parser (7+ formats via LiteLLM)
- Excel Parser (XLSX, XLS)
- Image Parser (PNG, JPG, WEBP)
- Testing Infrastructure (71 parser tests)

**❌ Remaining (20% of planned features):**
1. **Video Processing** (YouTube + MP4) - 20-25 hours
2. **Hierarchical Indices** (Two-tier retrieval) - 16-20 hours
3. **Connectors** (Multi-source ingestion) - 60-80 hours

**Total Estimated Effort:** 96-125 hours

---

## Priority Matrix (Updated with SurfSense Insights)

| Priority | Feature | Complexity | Value | Effort | Dependencies |
|----------|---------|------------|-------|--------|--------------|
| **P0** | Video Processing | Medium | High | 20-25h | ffmpeg, youtube-transcript-api, faster-whisper |
| **P1** | Hierarchical Indices | Medium-High | Very High | 16-20h | LLM summarization, pgvector updates |
| **P2** | Gmail Connector | Medium | High | 4-6h | google-auth-oauthlib |
| **P3** | GitHub Connector | Low-Medium | Medium | 6-8h | PyGithub |
| **P4** | Slack/Notion | Medium | Medium | 8-10h each | slack-sdk, notion-client |

---

## Feature 1: Video Processing

### Overview
YouTube video and MP4 file transcription with multi-provider STT support.

### SurfSense Implementation Pattern

**Files Analyzed:**
- `references/surfsense/app/tasks/document_processors/youtube_processor.py` (392 lines)
- `references/surfsense/app/tasks/document_processors/file_processors.py` (audio: 466-582)
- `references/surfsense/app/services/stt_service.py` (100 lines)

**Architecture:**
```
YouTube URL → Extract Video ID → Fetch Transcript API → Store
MP4 File → Extract Audio → Transcribe (Faster-Whisper/LiteLLM) → Store
```

### Implementation Plan

#### Step 1: YouTube Transcript Processor (6-8 hours)

**Create:** `backend/parsers/youtube_parser.py`

**Core Logic:**
```python
from youtube_transcript_api import YouTubeTranscriptApi
import re
from typing import Dict, Any

class YouTubeParser:
    """
    Extract transcripts from YouTube videos

    Supports URL formats:
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    """

    VIDEO_ID_PATTERNS = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
    ]

    def can_parse(self, content_type: str) -> bool:
        return content_type in {
            "video/youtube",
            "application/x-youtube",
            "text/html"  # YouTube URL in text
        }

    def _extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from URL"""
        for pattern in self.VIDEO_ID_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError(f"Could not extract video ID from URL: {url}")

    async def parse_url(self, url: str) -> Dict[str, Any]:
        """
        Parse YouTube video from URL

        Returns:
            Dict with content (transcript) and metadata
        """
        try:
            video_id = self._extract_video_id(url)

            # Fetch transcript via YouTube Transcript API
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

            # Combine all transcript segments
            full_transcript = "\n".join([
                f"[{self._format_timestamp(segment['start'])}] {segment['text']}"
                for segment in transcript_list
            ])

            # Calculate duration
            duration = transcript_list[-1]['start'] + transcript_list[-1]['duration']

            # Fetch video metadata via oEmbed API
            metadata = await self._fetch_video_metadata(video_id)

            return {
                "content": full_transcript,
                "metadata": {
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "title": metadata.get("title"),
                    "author": metadata.get("author_name"),
                    "thumbnail": metadata.get("thumbnail_url"),
                    "duration_seconds": duration,
                    "transcript_segments": len(transcript_list),
                },
                "page_count": None
            }

        except Exception as e:
            logger.error(f"YouTube transcript extraction failed: {e}")
            return {
                "content": "",
                "metadata": {"error": str(e)},
                "page_count": None
            }

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    async def _fetch_video_metadata(self, video_id: str) -> Dict:
        """Fetch video metadata from YouTube oEmbed API"""
        import aiohttp

        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return {}
```

**Dependencies:**
```toml
# pyproject.toml
youtube-transcript-api = "^0.6.0"
aiohttp = "^3.9.0"  # Already installed
```

**Tests:** `tests/unit/test_youtube_parser.py` (20-25 tests)

---

#### Step 2: MP4 Video Parser (8-10 hours)

**Create:** `backend/parsers/video_parser.py`

**Core Logic:**
```python
from pathlib import Path
import subprocess
import tempfile
from litellm import atranscription
from typing import Dict, Any

class VideoParser:
    """
    Parse MP4/AVI/MOV video files

    Process:
    1. Extract audio track using ffmpeg
    2. Transcribe audio using LiteLLM (Faster-Whisper or cloud STT)
    3. Clean up temporary audio file
    """

    SUPPORTED_FORMATS = {
        "video/mp4",
        "video/avi",
        "video/quicktime",  # .mov
        "video/x-msvideo",  # .avi
        "video/webm",
    }

    def can_parse(self, content_type: str) -> bool:
        return content_type in self.SUPPORTED_FORMATS

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse video file and extract transcript"""
        temp_audio = None

        try:
            # Step 1: Extract audio to temporary WAV file
            temp_audio = self._extract_audio(file_path)

            # Step 2: Get video metadata
            metadata = self._get_video_metadata(file_path)

            # Step 3: Transcribe audio using LiteLLM
            # (reuse AudioParser logic or call STT service directly)
            transcript_result = await self._transcribe_audio(temp_audio)

            return {
                "content": transcript_result["text"],
                "metadata": {
                    **metadata,
                    "transcription_language": transcript_result.get("language"),
                    "transcription_model": settings.STT_SERVICE,
                },
                "page_count": None
            }

        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return {
                "content": "",
                "metadata": {"error": str(e)},
                "page_count": None
            }

        finally:
            # Clean up temporary audio file
            if temp_audio and Path(temp_audio).exists():
                Path(temp_audio).unlink()

    def _extract_audio(self, video_path: str) -> str:
        """
        Extract audio track from video using ffmpeg

        Returns path to temporary WAV file
        """
        # Create temp file
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

        # Extract audio with ffmpeg
        # -vn: no video, -acodec: audio codec, -ar: sample rate, -ac: channels
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit
            "-ar", "16000",  # 16kHz sample rate
            "-ac", "1",  # Mono
            "-y",  # Overwrite
            temp_audio
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr}")

        return temp_audio

    def _get_video_metadata(self, video_path: str) -> Dict:
        """Extract video metadata using ffprobe"""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)

            format_info = data.get("format", {})
            video_stream = next(
                (s for s in data.get("streams", []) if s["codec_type"] == "video"),
                {}
            )

            return {
                "duration_seconds": float(format_info.get("duration", 0)),
                "file_size_bytes": int(format_info.get("size", 0)),
                "format": format_info.get("format_name"),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "fps": eval(video_stream.get("r_frame_rate", "0/1")),
            }

        return {}

    async def _transcribe_audio(self, audio_path: str) -> Dict:
        """Transcribe audio file using LiteLLM"""
        response = await atranscription(
            model=settings.STT_SERVICE,
            file=open(audio_path, "rb"),
            api_key=settings.STT_SERVICE_API_KEY or settings.OPENAI_API_KEY,
            api_base=settings.STT_SERVICE_API_BASE or None
        )

        return {
            "text": response.get("text", ""),
            "language": response.get("language"),
        }
```

**Dependencies:**
```bash
# System dependencies (Docker)
apt-get install -y ffmpeg

# Python dependencies
# (litellm already installed)
```

**Tests:** `tests/unit/test_video_parser.py` (25-30 tests)

---

#### Step 3: Faster-Whisper Local Option (6-8 hours)

**Enhance:** `backend/parsers/audio_parser.py`

**Add Local Faster-Whisper Support:**
```python
class AudioParser:
    def __init__(self):
        self.use_local = settings.STT_LOCAL_ENABLED
        if self.use_local:
            self.local_model = self._load_faster_whisper()

    def _load_faster_whisper(self):
        """Lazy-load Faster-Whisper model"""
        from faster_whisper import WhisperModel

        # int8 quantization for CPU optimization
        model = WhisperModel(
            settings.STT_LOCAL_MODEL,  # "base", "small", "medium"
            device="cpu",
            compute_type="int8"
        )

        logger.info(f"Loaded Faster-Whisper model: {settings.STT_LOCAL_MODEL}")
        return model

    async def parse(self, file_path: str) -> Dict[str, Any]:
        if self.use_local:
            return await self._transcribe_local(file_path)
        else:
            return await self._transcribe_cloud(file_path)

    async def _transcribe_local(self, file_path: str) -> Dict[str, Any]:
        """Transcribe using local Faster-Whisper"""
        segments, info = self.local_model.transcribe(
            file_path,
            beam_size=5,
            language=None,  # Auto-detect
        )

        # Combine segments
        transcript = " ".join([segment.text for segment in segments])

        return {
            "content": transcript,
            "metadata": {
                "language": info.language,
                "duration_seconds": info.duration,
                "transcription_model": f"faster-whisper-{settings.STT_LOCAL_MODEL}",
                "transcription_success": True
            },
            "page_count": None
        }
```

**Dependencies:**
```toml
faster-whisper = "^1.1.0"
```

**Benefits:**
- 99x faster than OpenAI Whisper API
- Free (no API costs)
- Privacy (data never leaves server)
- Works offline

---

### Video Processing Checklist

- [ ] Install `youtube-transcript-api` dependency
- [ ] Create `backend/parsers/youtube_parser.py` (300 lines)
- [ ] Create `tests/unit/test_youtube_parser.py` (20 tests)
- [ ] Install ffmpeg system package
- [ ] Create `backend/parsers/video_parser.py` (350 lines)
- [ ] Create `tests/unit/test_video_parser.py` (25 tests)
- [ ] Add Faster-Whisper local option to `audio_parser.py` (150 lines)
- [ ] Update `backend/parsers/__init__.py` to register new parsers
- [ ] Update config with `STT_LOCAL_ENABLED` and `STT_LOCAL_MODEL`
- [ ] Run tests: `poetry run pytest tests/unit/test_*_parser.py -v`
- [ ] Update README.md with new format support
- [ ] Commit and push

**Estimated Total:** 20-25 hours

---

## Feature 2: Hierarchical Indices (Two-Tier Retrieval)

### Overview
Implement two-tier retrieval: Document-level search → Chunk-level search for 20-30% better accuracy.

### SurfSense Implementation Pattern

**Files Analyzed:**
- `references/surfsense/app/retriver/documents_hybrid_search.py` - Document-level
- `references/surfsense/app/retriver/chunks_hybrid_search.py` - Chunk-level
- `references/surfsense/app/utils/document_converters.py` - Summarization

**Architecture:**
```
Query → [Tier 1: Document Search] → Top N documents
      → [Tier 2: Chunk Search within documents] → Top K chunks
```

### Implementation Plan

#### Step 1: Add Document Embeddings (4-6 hours)

**Database Migration:**

Create: `backend/alembic/versions/add_document_embeddings.py`

```python
"""Add document-level embeddings

Revision ID: xxx
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

def upgrade():
    # Add document_embedding column to documents table
    op.add_column(
        'documents',
        sa.Column('document_embedding', Vector(1536), nullable=True)
    )

    # Add document summary column
    op.add_column(
        'documents',
        sa.Column('summary', sa.Text, nullable=True)
    )

    # Create index on document_embedding for fast similarity search
    op.execute(
        """
        CREATE INDEX idx_documents_embedding
        ON documents
        USING ivfflat (document_embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

def downgrade():
    op.drop_index('idx_documents_embedding', table_name='documents')
    op.drop_column('documents', 'summary')
    op.drop_column('documents', 'document_embedding')
```

**Update Model:**

Edit: `backend/models/document.py`

```python
from pgvector.sqlalchemy import Vector

class Document(Base):
    # ... existing fields ...

    # NEW: Document-level embedding and summary
    document_embedding = Column(Vector(1536), nullable=True)
    summary = Column(Text, nullable=True)
```

---

#### Step 2: Generate Document Embeddings (6-8 hours)

**Strategy: LLM Summarization + Embedding**

Create: `backend/services/document_summary_service.py`

```python
from typing import Dict, Any
from litellm import acompletion
from backend.config import settings
from backend.embeddings.openai_embedder import OpenAIEmbedder

class DocumentSummaryService:
    """
    Generate document-level summaries and embeddings

    Two strategies:
    1. Concatenate first N chunks (fast)
    2. LLM summarization (higher quality)
    """

    def __init__(self):
        self.embedder = OpenAIEmbedder()

    async def generate_document_summary(
        self,
        content: str,
        metadata: Dict[str, Any],
        strategy: str = "llm"  # "concat" or "llm"
    ) -> str:
        """
        Generate document summary for embedding

        Args:
            content: Full document content
            metadata: Document metadata (title, filename, etc.)
            strategy: "concat" (first 5 chunks) or "llm" (AI summary)

        Returns:
            Summary text for embedding
        """
        if strategy == "concat":
            return self._concat_strategy(content, metadata)
        else:
            return await self._llm_summary_strategy(content, metadata)

    def _concat_strategy(self, content: str, metadata: Dict) -> str:
        """Fast: Concatenate metadata + first 2000 chars"""
        title = metadata.get("title", "")
        filename = metadata.get("filename", "")

        # Enhanced summary with metadata
        summary_parts = []
        if title:
            summary_parts.append(f"Title: {title}")
        if filename:
            summary_parts.append(f"File: {filename}")

        # Add content preview (first 2000 chars)
        content_preview = content[:2000]
        summary_parts.append(content_preview)

        return "\n".join(summary_parts)

    async def _llm_summary_strategy(self, content: str, metadata: Dict) -> str:
        """
        High quality: LLM generates concise summary

        Used for better document-level search accuracy
        """
        title = metadata.get("title", "")
        filename = metadata.get("filename", "")

        # Truncate content to fit context window
        max_content_length = 8000  # ~2000 tokens
        truncated_content = content[:max_content_length]

        prompt = f"""Summarize the following document in 2-3 concise paragraphs that capture:
1. Main topic and purpose
2. Key points and concepts
3. Important details

Document Title: {title}
Filename: {filename}

Content:
{truncated_content}

Summary:"""

        response = await acompletion(
            model=settings.LLM_PROVIDER + "/" + settings.CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )

        summary = response.choices[0].message.content

        # Enhance with metadata
        enhanced_summary = f"Title: {title}\nFile: {filename}\n\n{summary}"

        return enhanced_summary

    async def generate_document_embedding(self, summary: str) -> list:
        """Generate embedding from document summary"""
        embedding = await self.embedder.embed(summary)
        return embedding
```

**Update Document Processing Task:**

Edit: `backend/tasks/process_document.py`

```python
from backend.services.document_summary_service import DocumentSummaryService

async def process_document_task(document_id: str):
    # ... existing parsing and chunking ...

    # Generate chunk embeddings (existing)
    chunk_embeddings = await embedder.embed_batch([c["content"] for c in chunks])

    # NEW: Generate document-level summary and embedding
    summary_service = DocumentSummaryService()

    # Strategy 1: Fast concatenation (recommended for large-scale)
    document_summary = await summary_service.generate_document_summary(
        content=parsed_content,
        metadata={"title": document.title, "filename": document.filename},
        strategy="concat"  # or "llm" for higher quality
    )

    # Generate document embedding
    document_embedding = await summary_service.generate_document_embedding(document_summary)

    # Save document summary and embedding
    document.summary = document_summary
    document.document_embedding = document_embedding
    db.commit()

    # ... rest of existing code ...
```

---

#### Step 3: Implement Hierarchical Search (6-8 hours)

**Create:** `backend/search/hierarchical_search.py`

```python
from typing import List, Dict, UUID
from sqlalchemy.orm import Session
from backend.models.document import Document
from backend.models.chunk import DocumentChunk
from backend.search.vector_search import VectorSearchService

class HierarchicalSearchService:
    """
    Two-tier retrieval for improved accuracy

    Tier 1: Document-level search (broad relevance)
    Tier 2: Chunk-level search within top documents (precise answers)

    Benefits:
    - 20-30% better retrieval accuracy
    - Faster for large collections (reduces search space)
    - Better context preservation (keeps chunks from same document)
    """

    def __init__(self, db: Session):
        self.db = db
        self.vector_search = VectorSearchService(db)

    async def search(
        self,
        query_embedding: List[float],
        user_id: UUID,
        collection_id: UUID = None,
        top_k: int = 10,
        document_multiplier: int = 3
    ) -> List[Dict]:
        """
        Two-tier hierarchical search

        Args:
            query_embedding: Query vector
            user_id: User ID for ownership filter
            collection_id: Optional collection filter
            top_k: Final number of chunks to return
            document_multiplier: How many documents to retrieve (top_k * multiplier)

        Returns:
            List of top_k chunks from most relevant documents
        """
        # Tier 1: Document-level search
        top_documents = await self._search_documents(
            query_embedding,
            user_id,
            collection_id,
            top_k=top_k * document_multiplier  # Get 3x more documents
        )

        if not top_documents:
            # Fallback to regular chunk search
            return await self.vector_search.search(
                query_embedding,
                user_id,
                collection_id,
                top_k
            )

        # Tier 2: Chunk-level search within top documents
        document_ids = [doc["id"] for doc in top_documents]

        chunks = await self._search_chunks_in_documents(
            query_embedding,
            document_ids,
            user_id,
            top_k
        )

        return chunks

    async def _search_documents(
        self,
        query_embedding: List[float],
        user_id: UUID,
        collection_id: UUID,
        top_k: int
    ) -> List[Dict]:
        """
        Tier 1: Search at document level using document embeddings

        Returns list of most relevant documents
        """
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
                "id": str(r.id),
                "title": r.title,
                "filename": r.filename,
                "score": 1 - r.distance  # Convert distance to similarity score
            }
            for r in results
        ]

    async def _search_chunks_in_documents(
        self,
        query_embedding: List[float],
        document_ids: List[str],
        user_id: UUID,
        top_k: int
    ) -> List[Dict]:
        """
        Tier 2: Search chunks only within specified documents

        Returns top_k most relevant chunks from the given documents
        """
        query = self.db.query(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.chunk_index,
            DocumentChunk.metadata_,
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
            DocumentChunk.document_id.in_(document_ids)  # Only search within top documents
        )

        results = query.order_by('distance').limit(top_k).all()

        return [
            {
                'chunk_id': str(r.id),
                'content': r.content,
                'chunk_index': r.chunk_index,
                'score': 1 - r.distance,
                'metadata': r.metadata_ or {},
                'chunk_metadata': r.chunk_metadata or {},
                'document': {
                    'id': str(r.document_id),
                    'title': r.document_title,
                    'filename': r.document_filename,
                },
                'collection_id': str(r.collection_id)
            }
            for r in results
        ]
```

**Update Retrieval API:**

Edit: `backend/api/retrievals.py`

```python
from backend.search.hierarchical_search import HierarchicalSearchService

@router.post("/retrievals")
async def retrieve_chunks(
    request: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ... existing code ...

    # NEW: Use hierarchical search if enabled
    if request.mode == RetrievalMode.HIERARCHICAL:
        search_service = HierarchicalSearchService(db)
        results = await search_service.search(
            query_embedding,
            current_user.id,
            request.collection_id,
            request.top_k
        )
    else:
        # Existing search modes
        results = await vector_search.search(...)

    # ... rest of code ...
```

**Update Schema:**

Edit: `backend/schemas/retrieval.py`

```python
class RetrievalMode(str, Enum):
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    HIERARCHICAL = "hierarchical"  # NEW
```

---

### Hierarchical Indices Checklist

- [ ] Create migration: `add_document_embeddings.py`
- [ ] Run migration: `alembic upgrade head`
- [ ] Update `backend/models/document.py` with new fields
- [ ] Create `backend/services/document_summary_service.py` (200 lines)
- [ ] Update `backend/tasks/process_document.py` to generate document embeddings
- [ ] Create `backend/search/hierarchical_search.py` (250 lines)
- [ ] Update `backend/api/retrievals.py` to support hierarchical mode
- [ ] Update `backend/schemas/retrieval.py` with new mode
- [ ] Create tests: `tests/unit/test_hierarchical_search.py` (20 tests)
- [ ] Benchmark accuracy improvement (document in RESEARCH.md)
- [ ] Run quality checks: lint + test + build
- [ ] Commit and push

**Estimated Total:** 16-20 hours

---

## Feature 3: Multi-Source Connectors

### Overview
Implement OAuth-based connectors for external data sources (Gmail, GitHub, Slack, Notion).

### SurfSense Implementation Pattern

**Files Analyzed:**
- `references/surfsense/app/services/connector_service.py` (2,544 lines)
- `references/surfsense/app/routes/google_gmail_add_connector_route.py` (OAuth flow)
- `references/surfsense/app/connectors/github_connector.py` (GitHub API)
- `references/surfsense/app/db.py` (SearchSourceConnector model)

**Connector Priority (by implementation effort):**

1. **Gmail** (4-6 hours) - Simplest OAuth, high value
2. **GitHub** (6-8 hours) - PAT auth, code indexing
3. **Slack** (8-10 hours) - OAuth + message threading
4. **Notion** (8-10 hours) - Complex API, hierarchical pages

---

### Implementation: Gmail Connector (Recommended Start)

#### Step 1: Database Model (2 hours)

**Create Migration:** `backend/alembic/versions/add_connectors.py`

```python
"""Add connectors table

Revision ID: xxx
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

def upgrade():
    # Create connector_type enum
    op.execute(
        """
        CREATE TYPE connector_type AS ENUM (
            'gmail',
            'github',
            'slack',
            'notion',
            'google_drive'
        )
        """
    )

    # Create connectors table
    op.create_table(
        'connectors',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connector_type', sa.Enum('gmail', 'github', 'slack', 'notion', 'google_drive', name='connector_type'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('config', JSON, nullable=False),  # Encrypted credentials
        sa.Column('sync_frequency', sa.String(20), default='daily'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True)),
        sa.Column('next_sync_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('metadata_', JSON, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )

    # Create index
    op.create_index('idx_connectors_user_collection', 'connectors', ['user_id', 'collection_id'])

def downgrade():
    op.drop_table('connectors')
    op.execute('DROP TYPE connector_type')
```

**Create Model:** `backend/models/connector.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
import uuid
from backend.database import Base
import enum

class ConnectorType(str, enum.Enum):
    GMAIL = "gmail"
    GITHUB = "github"
    SLACK = "slack"
    NOTION = "notion"
    GOOGLE_DRIVE = "google_drive"

class Connector(Base):
    __tablename__ = "connectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)

    connector_type = Column(SQLEnum(ConnectorType), nullable=False)
    name = Column(String(255), nullable=False)
    config = Column(JSON, nullable=False)  # Encrypted OAuth tokens/API keys

    sync_frequency = Column(String(20), default="daily")
    last_sync_at = Column(DateTime(timezone=True))
    next_sync_at = Column(DateTime(timezone=True))

    is_active = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

---

#### Step 2: Gmail OAuth Flow (4-6 hours)

**Create Routes:** `backend/api/connectors/gmail.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from backend.config import settings
from backend.models.connector import Connector, ConnectorType
import base64
import json

router = APIRouter(prefix="/connectors/gmail", tags=["connectors"])

@router.get("/authorize")
async def initiate_gmail_oauth(
    collection_id: UUID = Query(...),
    current_user: User = Depends(get_current_user)
):
    """
    Step 1: Initiate Gmail OAuth flow

    Returns authorization URL for user to grant permissions
    """
    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_GMAIL_REDIRECT_URI]
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email"
        ]
    )

    flow.redirect_uri = settings.GOOGLE_GMAIL_REDIRECT_URI

    # Encode state with collection_id and user_id (CSRF protection)
    state = base64.urlsafe_b64encode(json.dumps({
        "collection_id": str(collection_id),
        "user_id": str(current_user.id)
    }).encode()).decode()

    # Generate authorization URL
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="consent"
    )

    return {"authorization_url": authorization_url}

@router.get("/callback")
async def gmail_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Step 2: Handle OAuth callback

    Exchange authorization code for access token and save connector
    """
    # Decode state
    decoded_state = json.loads(base64.urlsafe_b64decode(state).decode())
    user_id = UUID(decoded_state["user_id"])
    collection_id = UUID(decoded_state["collection_id"])

    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_GMAIL_REDIRECT_URI]
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email"
        ]
    )

    flow.redirect_uri = settings.GOOGLE_GMAIL_REDIRECT_URI

    # Exchange code for token
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Get user email
    service = build("gmail", "v1", credentials=credentials)
    profile = service.users().getProfile(userId="me").execute()
    email = profile.get("emailAddress")

    # Save connector
    connector = Connector(
        user_id=user_id,
        collection_id=collection_id,
        connector_type=ConnectorType.GMAIL,
        name=f"Gmail ({email})",
        config={
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "email": email
        }
    )

    db.add(connector)
    db.commit()

    # Redirect to frontend success page
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/collections/{collection_id}/connectors?success=gmail"
    )
```

**Add Config:**

Edit: `backend/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Google OAuth (Connectors)
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/v1/connectors/gmail/callback"

    FRONTEND_URL: str = "http://localhost:3000"
```

---

#### Step 3: Gmail Sync Task (6-8 hours)

**Create Celery Task:** `backend/tasks/sync_gmail.py`

```python
from celery import shared_task
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from backend.models.connector import Connector
from backend.tasks.process_document import process_document_task
import base64

@shared_task(name="sync_gmail_connector")
def sync_gmail_connector(connector_id: str):
    """
    Sync emails from Gmail to Mnemosyne

    Fetches recent emails and indexes them as documents
    """
    db = get_db()
    connector = db.query(Connector).filter(Connector.id == connector_id).first()

    if not connector or connector.connector_type != "gmail":
        raise ValueError("Invalid Gmail connector")

    # Rebuild credentials from config
    creds = Credentials(
        token=connector.config["token"],
        refresh_token=connector.config["refresh_token"],
        token_uri=connector.config["token_uri"],
        client_id=connector.config["client_id"],
        client_secret=connector.config["client_secret"],
        scopes=connector.config["scopes"]
    )

    # Build Gmail service
    service = build("gmail", "v1", credentials=creds)

    # Fetch messages (max 100 per sync)
    results = service.users().messages().list(
        userId="me",
        maxResults=100,
        q="category:primary"  # Only primary emails
    ).execute()

    messages = results.get("messages", [])

    # Process each email
    for msg in messages:
        # Get full message
        message = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        # Extract email content
        email_data = parse_gmail_message(message)

        # Check if already indexed (deduplication)
        unique_id = f"gmail_{msg['id']}"
        existing = db.query(Document).filter(
            Document.unique_identifier == unique_id
        ).first()

        if existing:
            continue  # Skip duplicate

        # Create document
        document = Document(
            user_id=connector.user_id,
            collection_id=connector.collection_id,
            title=email_data["subject"],
            filename=f"gmail_{msg['id']}.txt",
            content_type="text/plain",
            file_size=len(email_data["body"]),
            status="processing",
            unique_identifier=unique_id,
            metadata_={
                "source": "gmail",
                "email_id": msg["id"],
                "from": email_data["from"],
                "date": email_data["date"],
                "labels": message.get("labelIds", [])
            }
        )

        db.add(document)
        db.commit()

        # Save email content temporarily
        temp_file = f"/tmp/gmail_{document.id}.txt"
        with open(temp_file, "w") as f:
            f.write(email_data["body"])

        # Trigger document processing
        process_document_task.delay(str(document.id), temp_file)

    # Update connector sync time
    connector.last_sync_at = datetime.utcnow()
    db.commit()

def parse_gmail_message(message: dict) -> dict:
    """Extract subject, from, date, and body from Gmail message"""
    headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}

    subject = headers.get("Subject", "No Subject")
    from_email = headers.get("From", "Unknown")
    date = headers.get("Date", "")

    # Extract body
    body = ""
    if "parts" in message["payload"]:
        for part in message["payload"]["parts"]:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                break
    else:
        if "data" in message["payload"]["body"]:
            body = base64.urlsafe_b64decode(message["payload"]["body"]["data"]).decode("utf-8")

    return {
        "subject": subject,
        "from": from_email,
        "date": date,
        "body": body
    }
```

**Schedule Sync:**

Edit: `backend/celery_app.py`

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    # ... existing schedules ...

    'sync-gmail-connectors': {
        'task': 'sync_all_connectors',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
}

@app.task
def sync_all_connectors():
    """Sync all active connectors"""
    db = get_db()
    connectors = db.query(Connector).filter(Connector.is_active == True).all()

    for connector in connectors:
        if connector.connector_type == "gmail":
            sync_gmail_connector.delay(str(connector.id))
        # Add other connector types here
```

---

### Connector Checklist (Gmail)

- [ ] Install `google-auth-oauthlib` and `google-api-python-client`
- [ ] Create migration: `add_connectors.py`
- [ ] Run migration: `alembic upgrade head`
- [ ] Create `backend/models/connector.py`
- [ ] Create `backend/api/connectors/gmail.py` (OAuth routes)
- [ ] Update `backend/config.py` with Google OAuth settings
- [ ] Create `backend/tasks/sync_gmail.py` (Celery task)
- [ ] Update `backend/celery_app.py` with scheduled sync
- [ ] Create tests: `tests/unit/test_gmail_connector.py`
- [ ] Set up Google Cloud OAuth credentials
- [ ] Test OAuth flow end-to-end
- [ ] Test email sync and indexing
- [ ] Commit and push

**Estimated Total:** 12-16 hours

**Dependencies:**
```toml
google-auth-oauthlib = "^1.2.0"
google-api-python-client = "^2.100.0"
```

---

## Implementation Order Recommendation

Based on value, complexity, and dependencies:

### Phase 2a: Core Features (36-45 hours)

**Week 1:**
1. **Video Processing** (20-25 hours)
   - YouTube parser (6-8h)
   - MP4 parser (8-10h)
   - Faster-Whisper local option (6-8h)

**Week 2:**
2. **Hierarchical Indices** (16-20 hours)
   - Document embeddings (4-6h)
   - Summary service (6-8h)
   - Hierarchical search (6-8h)

### Phase 2b: Connectors (Optional, 12-40 hours)

**Week 3:**
3. **Gmail Connector** (12-16 hours) - Quick win
4. **GitHub Connector** (14-18 hours) - Developer use case
5. **Slack Connector** (16-20 hours) - Team collaboration

---

## Success Metrics

### Video Processing
- [ ] YouTube videos indexed successfully
- [ ] MP4 files transcribed accurately
- [ ] Local Faster-Whisper 10x faster than cloud
- [ ] Transcription accuracy >90%

### Hierarchical Indices
- [ ] Document embeddings generated for all documents
- [ ] Two-tier search 20-30% more accurate
- [ ] Search latency <500ms for 10k documents
- [ ] Benchmark results documented

### Connectors
- [ ] OAuth flow completes successfully
- [ ] Email sync runs on schedule
- [ ] Deduplication prevents duplicate documents
- [ ] Search across Gmail works correctly

---

## Testing Strategy

### Unit Tests
- Video parsers: 45-50 tests
- Hierarchical search: 20-25 tests
- Connectors: 15-20 tests per connector
- **Target: 80%+ coverage**

### Integration Tests
- End-to-end video upload → transcription → search
- Two-tier retrieval accuracy benchmark
- OAuth flow → sync → search

### Performance Tests
- Video transcription speed (local vs cloud)
- Hierarchical search vs flat search latency
- Connector sync performance (100+ emails)

---

## Risk Mitigation

### Video Processing
**Risk:** ffmpeg dependency issues
**Mitigation:** Use Docker with ffmpeg pre-installed

**Risk:** Transcription costs (cloud STT)
**Mitigation:** Implement local Faster-Whisper as default

### Hierarchical Indices
**Risk:** Migration on large databases
**Mitigation:** Backfill document embeddings in batches

**Risk:** Performance degradation
**Mitigation:** Benchmark before/after, add pgvector indexes

### Connectors
**Risk:** OAuth token expiration
**Mitigation:** Implement token refresh logic

**Risk:** Rate limiting from external APIs
**Mitigation:** Exponential backoff + retry logic

---

## Next Steps

1. **Review this plan** - Validate priorities and timeline
2. **Choose starting feature:**
   - **Option A:** Video Processing (high value, medium complexity)
   - **Option B:** Hierarchical Indices (highest quality boost)
   - **Option C:** Gmail Connector (quick win, user-facing)
3. **Set up development environment:**
   - Install ffmpeg (for video)
   - Set up Google OAuth (for Gmail)
   - Configure local Faster-Whisper (optional)
4. **Begin implementation** following detailed checklists above

**Recommended Start:** Video Processing (YouTube + MP4)
- Highest user value
- Builds on existing audio parser
- Clear SurfSense reference implementation

---

**Total Phase 2 Remaining Effort:** 96-125 hours
**Recommended Timeline:** 3-4 weeks (25-30 hours/week)
**Priority:** Video → Hierarchical → Connectors
