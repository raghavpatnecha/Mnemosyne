# Reference Implementation Analysis

**Date:** 2025-11-15
**Branch:** claude/check-mnemosyne-repo-01BswSWffoPM15U89RrZEtNB
**Status:** Submodules initialized ✓

---

## What We Have Access To

### SurfSense (v1.0.45-138)
- **Location:** `references/surfsense/`
- **Backend:** `references/surfsense/surfsense_backend/`
- **Key Files:** LLM service, file processors, reranker, connectors

### RAG-Anything (v1.2.8-18)
- **Location:** `references/rag-anything/`
- **Key:** Multimodal processing, LightRAG integration

---

## Key Findings from SurfSense

### 1. LiteLLM Integration (`app/services/llm_service.py`)

**What they did:**
```python
import litellm
from langchain_litellm import ChatLiteLLM

# Provider mapping for 30+ providers
provider_map = {
    "OPENAI": "openai",
    "ANTHROPIC": "anthropic",
    "GROQ": "groq",
    "GOOGLE": "gemini",
    "OLLAMA": "ollama",
    "MISTRAL": "mistral",
    "AZURE_OPENAI": "azure",
    "OPENROUTER": "openrouter",
    "XAI": "xai",
    "BEDROCK": "bedrock",
    "VERTEX_AI": "vertex_ai",
    "TOGETHER_AI": "together_ai",
    "FIREWORKS_AI": "fireworks_ai",
    "REPLICATE": "replicate",
    "PERPLEXITY": "perplexity",
    # + 15 more providers including Chinese LLMs
}

# Model string format: "{provider}/{model_name}"
model_string = f"{provider_prefix}/{model_name}"

# Create instance
llm = ChatLiteLLM(
    model=model_string,
    api_key=api_key,
    api_base=api_base,  # Optional
    timeout=30
)

# Use with LangChain
response = await llm.ainvoke([HumanMessage(content="Hello")])
```

**Key takeaways:**
- ✅ Use `langchain_litellm.ChatLiteLLM` (not direct litellm)
- ✅ Format: `{provider}/{model}` (e.g., `"anthropic/claude-3-sonnet"`)
- ✅ Validation: Test with simple message before saving config
- ✅ Graceful fallback: `litellm.drop_params = True`

---

### 2. File Processing (`app/tasks/document_processors/file_processors.py`)

**File: 1021 lines - Comprehensive processor**

**Audio Processing (lines 466-550):**
```python
# Audio formats supported
audio_extensions = (".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm")

# Two approaches:
# 1. LiteLLM transcription (OpenAI Whisper API)
from litellm import atranscription

result = await atranscription(
    model="whisper-1",  # LiteLLM handles provider routing
    file=audio_file
)
transcribed_text = result.get("text", "")

# 2. Local Faster-Whisper (for privacy/cost)
from app.services.stt_service import stt_service

result = stt_service.transcribe_file(file_path)
transcribed_text = result.get("text", "")
```

**Video Processing (`youtube_processor.py` - 14KB):**
- YouTube URL support with `youtube-transcript-api`
- Extract audio → transcribe with Whisper
- Supports timestamps and chapters

**Three ETL Services:**
1. **Unstructured.io** - Fallback for all formats
2. **LlamaCloud** - Cloud-based processing
3. **Docling** - PDF/Office docs (same as we have)

---

### 3. Reranking (`app/services/reranker_service.py`)

**What they did:**
```python
from rerankers import Document as RerankerDocument

class RerankerService:
    def __init__(self, reranker_instance=None):
        # reranker_instance is from `rerankers` library
        # Supports: Flashrank, Cohere, Jina, Voyage, etc.
        self.reranker_instance = reranker_instance

    def rerank_documents(self, query_text: str, documents: list) -> list:
        # Convert to rerankers format
        reranker_docs = [
            RerankerDocument(
                text=doc["content"],
                doc_id=doc["chunk_id"],
                metadata={"score": doc["score"]}
            )
            for doc in documents
        ]

        # Rerank
        results = self.reranker_instance.rank(query=query_text, docs=reranker_docs)

        # Convert back
        return [
            {
                **original_doc,
                "score": float(result.score),
                "rank": result.rank
            }
            for result in results.results
        ]
```

**Key takeaway:**
- ✅ Use `rerankers` library (unified API for all rerankers)
- ✅ Supports: Flashrank, Cohere, Jina, Voyage, Mixbread, etc.
- ✅ Simple interface: `reranker.rank(query, docs)`

---

## Implementation Complexity Comparison

### Easy to Implement (2-4 hours each)

1. **LiteLLM Integration**
   - **Complexity:** Low
   - **Files to create:** 1 (update `llm_service.py`)
   - **Dependencies:** `litellm`, `langchain-litellm`
   - **SurfSense pattern:** Direct copy with adjustments
   - **Impact:** Immediate access to 100+ models

2. **Multiple Rerankers**
   - **Complexity:** Low
   - **Files to create:** Update existing `reranker_service.py`
   - **Dependencies:** `rerankers` library
   - **SurfSense pattern:** Wrapper around `rerankers` library
   - **Impact:** Cohere, Jina, Voyage support

### Medium to Implement (6-10 hours each)

3. **Audio Transcription**
   - **Complexity:** Medium
   - **Files to create:** 2-3 (audio parser + STT service)
   - **Dependencies:** `litellm` (for Whisper API) or `faster-whisper` (local)
   - **SurfSense pattern:** Well-documented
   - **Impact:** MP3, WAV, M4A support

4. **Testing Infrastructure**
   - **Complexity:** Medium
   - **Files to create:** 10-15 test files
   - **Dependencies:** `pytest`, `pytest-asyncio`, `pytest-mock`
   - **SurfSense pattern:** Need to create from scratch
   - **Impact:** Foundation for all future development

### Complex to Implement (12-20 hours each)

5. **Video Processing**
   - **Complexity:** High
   - **Files to create:** 3-4 (video parser + YouTube processor)
   - **Dependencies:** `ffmpeg`, `youtube-transcript-api`
   - **SurfSense pattern:** youtube_processor.py (14KB)
   - **Impact:** MP4, YouTube support

6. **50+ File Formats**
   - **Complexity:** High
   - **Files to create:** 5-8 parser files
   - **Dependencies:** Multiple (pandas, pytesseract, etc.)
   - **SurfSense pattern:** file_processors.py (1021 lines)
   - **Impact:** Excel, Images, etc.

---

## Recommended Implementation Order

### Phase 1: Quick Wins (Week 6, Days 1-3)

**Priority 1: LiteLLM Integration** ⚡ **FASTEST**
- **Time:** 3-4 hours
- **Why first:** Unlocks flexibility immediately
- **Files:** Update `backend/services/chat_service.py`
- **Dependencies:** `litellm`, `langchain-litellm`
- **SurfSense reference:** `app/services/llm_service.py:1-150`

**Priority 2: Multiple Rerankers** ⚡ **FAST**
- **Time:** 2-3 hours
- **Why second:** Improves retrieval quality
- **Files:** Update `backend/services/reranker_service.py`
- **Dependencies:** `rerankers`
- **SurfSense reference:** `app/services/reranker_service.py:1-105`

**Priority 3: Audio Transcription** ⏱️ **MEDIUM**
- **Time:** 6-8 hours
- **Why third:** High-value format support
- **Files:** Create `backend/parsers/audio_parser.py`
- **Dependencies:** `litellm` (Whisper API)
- **SurfSense reference:** `app/tasks/document_processors/file_processors.py:466-550`

---

### Phase 2: Foundation (Week 6, Days 4-5)

**Priority 4: Testing Infrastructure** 🧪 **IMPORTANT**
- **Time:** 8-10 hours
- **Why:** Enables confident development
- **Files:** Create `tests/` directory structure
- **Dependencies:** `pytest`, `pytest-asyncio`
- **SurfSense reference:** None (we create from scratch)

---

### Phase 3: Advanced (Week 7+)

**Priority 5-7:** Video, Excel, Images, Connectors, etc.

---

## What We Can Implement TODAY

### Option A: LiteLLM + Rerankers (Combined: 5-7 hours) ⚡ RECOMMENDED

**Deliverables:**
1. Support 100+ LLM models (OpenAI, Anthropic, Google, Mistral, Ollama, etc.)
2. Support 5+ rerankers (Flashrank, Cohere, Jina, Voyage, Mixbread)
3. Per-request model selection via API
4. Cost tracking per model

**Impact:** Maximum flexibility with minimal effort

---

### Option B: Audio Transcription (6-8 hours)

**Deliverables:**
1. MP3, WAV, M4A, WEBM support
2. Whisper API integration (via LiteLLM)
3. Optional local Faster-Whisper
4. Automatic transcription in document pipeline

**Impact:** Close critical gap in file format support

---

### Option C: Testing Infrastructure (8-10 hours)

**Deliverables:**
1. pytest configuration with fixtures
2. Unit tests for all services
3. Integration tests for RAG pipeline
4. 80%+ code coverage
5. CI/CD ready

**Impact:** Foundation for all future development

---

## Decision Time

**Which do you want to implement first?**

### My Recommendation: Option A (LiteLLM + Rerankers)

**Why:**
1. ✅ **Fastest** (5-7 hours total)
2. ✅ **Highest value** (100+ models immediately)
3. ✅ **Clear reference** (SurfSense code is clean)
4. ✅ **Compound benefit** (helps with audio transcription later)
5. ✅ **User-facing** (immediate API enhancement)

**Next Steps if we choose Option A:**
1. Install dependencies: `litellm`, `langchain-litellm`, `rerankers`
2. Create enhanced `LLMService` class
3. Update `ChatService` to use new LLMService
4. Update `RerankerService` with multiple rerankers
5. Add API parameters for model/reranker selection
6. Test with different models
7. Document usage

**Estimated time:** 5-7 hours
**Complexity:** Low-Medium
**Immediate impact:** High

---

**Tell me:** Which option (A, B, or C) should we implement first?

Or would you prefer a different combination?
