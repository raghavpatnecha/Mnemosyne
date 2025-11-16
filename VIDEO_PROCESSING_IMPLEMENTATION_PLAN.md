# Video Processing Implementation Plan

**Date:** 2025-11-16
**Status:** Ready for Implementation
**Estimated Effort:** 20-25 hours

---

## Integration Analysis (from Memory + Swarm)

### Existing Patterns Discovered

**From Git History:**
- Commit 743d006: All parsers made async for fail-fast consistency
- Commit 97839ff: AudioParser migrated to LiteLLM multi-provider
- Pattern: Async parse() + can_parse() + error handling

**From Code Exploration:**
- All parsers under 300 lines ✅
  - audio_parser.py: 164 lines
  - image_parser.py: 180 lines
  - excel_parser.py: 136 lines
- ParserFactory uses ordered list
- Process pipeline: parser.parse() → chunker.chunk() → embedder.embed_batch()

**From SurfSense Reference:**
- YouTube: `get_youtube_video_id()` handles 4 URL formats
- YouTube Transcript API with timestamp preservation
- oEmbed API for metadata (title, author, thumbnail)
- Audio: Dual strategy (local Faster-Whisper OR LiteLLM)
- Local check: `settings.STT_SERVICE.startswith("local/")`

---

## Implementation Strategy

### Phase 1: YouTube Parser (~250 lines, 6-8 hours)

**File:** `backend/parsers/youtube_parser.py`

**Features:**
1. Extract video ID from 4 URL formats:
   - `https://youtu.be/VIDEO_ID`
   - `https://www.youtube.com/watch?v=VIDEO_ID`
   - `https://www.youtube.com/embed/VIDEO_ID`
   - `https://www.youtube.com/v/VIDEO_ID`

2. Fetch transcript via YouTube Transcript API
   - Preserve timestamps: `[MM:SS] text`
   - Handle multiple languages
   - Error handling for videos without captions

3. Fetch metadata via oEmbed API
   - Title, author, thumbnail, duration
   - Async with aiohttp

**MIME Type:** `text/html` (with URL detection) or `video/youtube`

**Return Format:**
```python
{
    "content": "[00:15] Transcript text...",
    "metadata": {
        "video_id": "abc123",
        "title": "Video Title",
        "author": "Channel Name",
        "thumbnail": "https://...",
        "duration_seconds": 600,
        "url": "https://www.youtube.com/watch?v=abc123",
        "transcript_segments": 150
    },
    "page_count": None
}
```

---

### Phase 2: Video Parser (~280 lines, 8-10 hours)

**File:** `backend/parsers/video_parser.py`

**Features:**
1. Support video formats: MP4, AVI, MOV, WEBM
2. Extract audio using ffmpeg subprocess
3. Transcribe using existing STT (reuse AudioParser pattern)
4. Extract video metadata using ffprobe

**MIME Types:** `video/mp4`, `video/avi`, `video/quicktime`, `video/webm`

**Workflow:**
```
Video File → ffmpeg extract audio → Temp WAV
Temp WAV → LiteLLM/Faster-Whisper → Transcript
ffprobe → Video metadata (duration, resolution, fps)
Cleanup temp file
```

**Return Format:**
```python
{
    "content": "Transcribed text",
    "metadata": {
        "duration_seconds": 300,
        "file_size_bytes": 50000000,
        "format": "mp4",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "transcription_model": "whisper-1",
        "transcription_language": "en"
    },
    "page_count": None
}
```

---

### Phase 3: Configuration (minimal, 1 hour)

**File:** `backend/config.py`

**New Settings:**
```python
# Video Processing (Phase 2)
VIDEO_FFMPEG_PATH: str = "ffmpeg"  # Path to ffmpeg binary
VIDEO_FFPROBE_PATH: str = "ffprobe"  # Path to ffprobe binary
VIDEO_TEMP_DIR: str = "/tmp/mnemosyne_video"  # Temp directory for audio extraction
VIDEO_MAX_DURATION: int = 3600  # Max video duration (1 hour)
```

**Existing Settings (reuse):**
- `STT_SERVICE` - Already supports LiteLLM
- `STT_SERVICE_API_KEY` - Already configured
- `STT_LOCAL_ENABLED` - For local Faster-Whisper

---

### Phase 4: Factory Registration (30 min)

**File:** `backend/parsers/__init__.py`

**Changes:**
```python
from backend.parsers.youtube_parser import YouTubeParser
from backend.parsers.video_parser import VideoParser

class ParserFactory:
    def __init__(self):
        self.parsers = [
            DoclingParser(),
            YouTubeParser(),    # NEW: YouTube URLs
            VideoParser(),      # NEW: Video files
            AudioParser(),
            ExcelParser(),
            ImageParser(),
            TextParser(),
        ]
```

**Order matters:** YouTube before Video (URL detection first)

---

### Phase 5: Dependencies (30 min)

**File:** `pyproject.toml`

**Add:**
```toml
youtube-transcript-api = "^0.6.0"
# aiohttp already installed ✅
```

**System Dependencies (Dockerfile):**
```dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

---

### Phase 6: Testing (6-8 hours)

**File:** `tests/unit/test_youtube_parser.py` (20-25 tests)

**Test Cases:**
- URL parsing (4 formats)
- Video ID extraction
- Transcript fetching (mock YouTubeTranscriptApi)
- Metadata fetching (mock aiohttp)
- Error handling (invalid URL, no captions)
- MIME type detection

**File:** `tests/unit/test_video_parser.py` (25-30 tests)

**Test Cases:**
- Video file parsing (mock ffmpeg)
- Audio extraction (subprocess mock)
- Transcription (mock LiteLLM)
- Metadata extraction (mock ffprobe)
- Cleanup (temp file removal)
- Error handling

---

## File Size Targets

| File | Target Lines | Complexity |
|------|--------------|------------|
| youtube_parser.py | ~250 | Medium |
| video_parser.py | ~280 | High |
| test_youtube_parser.py | ~300 | Medium |
| test_video_parser.py | ~350 | High |

**All under 300 lines per CLAUDE.md** ✅

---

## Integration Points

### 1. ParserFactory Selection
- YouTube: Detect URLs containing "youtube.com" or "youtu.be"
- Video: MIME type starts with "video/"
- Fallback: TextParser for unknown

### 2. Document Processing Pipeline
No changes needed! Existing pipeline:
```
upload → detect MIME → get_parser() → parse() → chunk() → embed() → store
```

### 3. API Endpoints
No changes needed! Existing endpoints work:
```
POST /api/v1/documents (upload)
POST /api/v1/documents/url (YouTube URLs)
```

---

## Risks & Mitigations

### Risk 1: ffmpeg Not Installed
**Mitigation:** Add to Dockerfile, document in README
**Fallback:** Return error with clear message

### Risk 2: YouTube API Rate Limits
**Mitigation:** YouTube Transcript API has no rate limits (scraping)
**Note:** May break if YouTube changes HTML structure

### Risk 3: Large Video Files
**Mitigation:**
- Set VIDEO_MAX_DURATION config (default 1 hour)
- Check file size before processing
- Stream audio extraction (don't load full file)

### Risk 4: Transcription Costs
**Mitigation:**
- Use local Faster-Whisper as default
- Add STT_LOCAL_ENABLED=True to config
- Document cost per minute ($0.006 OpenAI vs free local)

---

## Success Criteria

- [ ] YouTube URLs processed successfully
- [ ] 4 URL formats supported
- [ ] Timestamps preserved in transcript
- [ ] MP4/video files transcribed
- [ ] ffmpeg audio extraction works
- [ ] Video metadata extracted (duration, resolution)
- [ ] All parsers under 300 lines
- [ ] 45-50 tests passing
- [ ] No breaking changes to existing parsers
- [ ] Quality checks pass (pytest + lint)

---

## Implementation Order (Swarm Orchestration)

### Batch 1: Parallel File Creation (30 min)
- Create youtube_parser.py skeleton
- Create video_parser.py skeleton
- Update config.py
- Update __init__.py

### Batch 2: Parallel Implementation (12-16 hours)
- Implement YouTubeParser (6-8h)
- Implement VideoParser (8-10h)
- Update dependencies (30min)

### Batch 3: Parallel Testing (6-8 hours)
- Write YouTube tests (3-4h)
- Write video tests (3-4h)
- Run quality checks (30min)

### Batch 4: Documentation & Commit (1 hour)
- Update README.md
- Document ffmpeg requirement
- Commit with descriptive message

**Total: 20-25 hours**

---

## Next Steps

1. ✅ Memory queried - Existing patterns understood
2. ✅ Swarm exploration - Integration points identified
3. ✅ Plan created - This document
4. → **Start Implementation** - Create parsers in parallel
5. → Test & validate
6. → Commit & push

**Ready to proceed with implementation!** 🚀
