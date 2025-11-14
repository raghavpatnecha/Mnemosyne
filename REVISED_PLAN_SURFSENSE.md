# Mnemosyne Universal RAG - REVISED PLAN (SurfSense-Based)

**Date:** 2025-11-14 (Updated)
**Decision:** Use SurfSense as foundation (NOT build from scratch)
**Timeline:** 4 weeks (vs 8 weeks original plan)

---

## Executive Summary - Why SurfSense is the Clear Winner

After detailed analysis, **SurfSense provides everything needed for universal RAG out-of-the-box**:

✅ **50+ file formats** (PDF, Office, images, audio, video)
✅ **15+ external integrations** (Slack, Notion, GitHub, Jira, Gmail, YouTube, etc.)
✅ **Production-ready infrastructure** (FastAPI, PostgreSQL, Celery, Redis)
✅ **Advanced RAG features** (hybrid search, reranking, hierarchical indices)
✅ **100+ LLM support** (OpenAI, Ollama, Anthropic, etc.)
✅ **6000+ embedding models** (flexible, no vendor lock-in)
✅ **Podcast generation** (NotebookLM-style audio summaries)
✅ **Apache 2.0 license** (freely fork and customize)

**Building from scratch would take 8 weeks to replicate what SurfSense already provides.**

---

## What SurfSense Already Has (Out of the Box)

### 1. ALL File Formats You Need

**Documents & Text (50+ formats via LlamaCloud):**
```
PDF, Word (.doc, .docx), RTF, TXT, XML, EPUB, ODT, Pages,
Markdown, HTML, OpenDocument, and 30+ more
```

**Presentations:**
```
PowerPoint (.ppt, .pptx), Keynote, OpenDocument Presentation
```

**Spreadsheets:**
```
Excel (.xls, .xlsx), CSV, TSV, Numbers, OpenDocument Spreadsheet,
and 25+ legacy formats
```

**Images:**
```
JPG, JPEG, PNG, GIF, BMP, SVG, TIFF, WebP, HEIC
+ OCR support for text extraction
```

**Audio & Video (ALWAYS SUPPORTED):**
```
MP3, MP4, WAV, M4A, MPEG, WebM
+ Automatic transcription (Whisper API integration)
```

**Email:**
```
EML, MSG (Outlook)
```

### 2. ALL External Integrations You Want

**Search Engines:**
- Tavily (AI-optimized search)
- LinkUp (web search)
- SearxNG (self-hosted, privacy-focused)

**Collaboration & Productivity:**
- **Slack** (channels, DMs, threads)
- **Notion** (pages, databases)
- **Confluence** (wikis, documentation)
- **Gmail** (emails, attachments)
- **Google Calendar** (events, meetings)

**Project Management:**
- **Jira** (issues, epics, sprints)
- **Linear** (issues, projects)
- **ClickUp** (tasks, docs)
- **Airtable** (bases, tables)

**Development:**
- **GitHub** (repos, issues, PRs, code)
- **Discord** (servers, channels, messages)

**Media:**
- **YouTube Videos** (transcription + indexing)

**Data Sources:**
- **Elasticsearch** (existing indices)

**And more coming...**

### 3. Production-Ready Infrastructure

**Backend Stack (Already Integrated):**
```
FastAPI (async, high-performance)
PostgreSQL + pgvector (vector search)
Celery (async task queue)
Redis (caching + message broker)
LangGraph + LangChain (AI orchestration)
SQLAlchemy (ORM)
```

**Document Processing (Multiple Options):**
```
LlamaCloud (50+ formats, cloud-based)
Unstructured.io (34+ formats, API-based)
Docling (core formats, local, privacy-focused, NO API KEY)
```

**Chunking & Retrieval:**
```
Chonkie (smart chunking with LateChunker)
Hybrid Search (semantic + full-text with RRF)
Hierarchical Indices (two-tier RAG)
Multiple Rerankers (Pinecone, Cohere, Flashrank)
```

**LLM Flexibility:**
```
100+ LLMs via LiteLLM:
- OpenAI (GPT-4, GPT-4o, GPT-3.5)
- Anthropic (Claude)
- Ollama (local models)
- Google (Gemini)
- Mistral, Cohere, etc.

6000+ Embedding Models:
- OpenAI embeddings
- Sentence Transformers (local)
- Cohere, Voyage, etc.
```

### 4. Bonus Features (Unexpected Value)

**Podcast Generation:**
- 3-minute podcasts in 20 seconds
- Kokoro TTS (local) or OpenAI/Azure/Google (cloud)
- NotebookLM-style audio summaries

**Browser Extension:**
- Capture authenticated webpages
- Save articles with full context
- Bookmarklet integration

**Authentication:**
- JWT tokens
- OAuth2 support
- Multi-user ready

**Observability:**
- Langfuse integration (optional)
- Query analytics
- Cost tracking

---

## Comparison: Build from Scratch vs Fork SurfSense

### Option A: Build from Scratch (Original Plan)

**Timeline: 8 weeks**

| Week | Task | What You Build |
|------|------|----------------|
| 1-2  | PostgreSQL + LightRAG | Database migration, graph setup |
| 3-4  | Multimodal processing | File upload, MinerU, Docling integration |
| 5-6  | Reranking + citations | Flashrank, source highlighting |
| 7-8  | Production optimization | Docker, testing, deployment |

**Effort Required:**
- ⚠️ Set up Celery + Redis from scratch
- ⚠️ Integrate MinerU + Docling + Unstructured
- ⚠️ Build chunking strategy (Chonkie)
- ⚠️ Implement hybrid search + RRF
- ⚠️ Add reranking layer
- ⚠️ Build auth system
- ⚠️ Create admin dashboard
- ⚠️ Test at scale (no validation)
- ⚠️ Debug infrastructure issues
- ⚠️ Build external integrations (Slack, Notion, etc.)

**Total: ~320 hours of development**

---

### Option B: Fork SurfSense (RECOMMENDED)

**Timeline: 4 weeks**

| Week | Task | What You Do |
|------|------|-------------|
| 1    | Setup & Testing | Fork repo, Docker Compose, test with sample docs |
| 2    | Frontend Integration | Add upload UI to Mnemosyne, connect to SurfSense API |
| 3    | Customization | Remove unused features, match UI style, add doc library |
| 4    | Deployment | Docker production setup, testing, documentation |

**Effort Required:**
- ✅ Fork existing codebase (already working)
- ✅ Configure environment variables
- ✅ Add file upload UI to Mnemosyne frontend
- ✅ Connect frontend to SurfSense backend APIs
- ✅ Customize UI to match Mnemosyne style
- ✅ Deploy with Docker Compose
- ✅ (Optional) Add external integrations as needed

**Total: ~160 hours of development (50% less!)**

---

## Detailed 4-Week Implementation Plan

### Week 1: SurfSense Setup & Understanding

**Day 1-2: Environment Setup**
- [ ] Fork SurfSense repository to `raghavpatnecha/Mnemosyne-Universal`
- [ ] Clone locally and review codebase structure
- [ ] Set up Docker Compose (PostgreSQL, Redis, backend, frontend)
- [ ] Configure `.env` file with API keys
- [ ] Install dependencies (`pip install -r requirements.txt`)

**Day 3-4: Testing Core Features**
- [ ] Upload test documents (PDF, Word, images)
- [ ] Test search and retrieval
- [ ] Verify Celery tasks are processing
- [ ] Test different ETL services (Docling vs LlamaCloud vs Unstructured)
- [ ] Understand API response formats

**Day 5: Architecture Deep Dive**
- [ ] Map backend API endpoints
- [ ] Understand database schema (PostgreSQL tables)
- [ ] Review Celery task structure
- [ ] Document configuration options
- [ ] Identify customization points

**Deliverables:**
- ✅ SurfSense running locally
- ✅ Tested with 10+ different file types
- ✅ Architecture documentation
- ✅ Configuration guide

---

### Week 2: Mnemosyne Frontend Integration

**Day 1-2: File Upload UI**
- [ ] Design upload component (drag & drop)
- [ ] Add multi-file selector
- [ ] Implement upload progress indicators
- [ ] Add file type icons and validation
- [ ] Create upload queue management

**Day 3-4: Backend API Connection**
- [ ] Update `script.js` to call SurfSense endpoints
- [ ] Replace MongoDB search with SurfSense `/search` API
- [ ] Maintain SSE streaming support
- [ ] Map SurfSense responses to Mnemosyne UI format
- [ ] Update source/citation display

**Day 5: Testing & Refinement**
- [ ] Test upload → process → search flow
- [ ] Verify SSE streaming works correctly
- [ ] Test follow-up questions
- [ ] Ensure markdown rendering works
- [ ] Fix any UI glitches

**Deliverables:**
- ✅ Mnemosyne frontend with upload feature
- ✅ Connected to SurfSense backend
- ✅ Full chat functionality preserved
- ✅ File processing working

---

### Week 3: Customization & Polish

**Day 1-2: Backend Customization**
- [ ] Remove unused features (browser extension if not needed)
- [ ] Configure preferred LLM (GPT-4o-mini or Ollama)
- [ ] Set up preferred embedding model
- [ ] Tune Chonkie chunking parameters
- [ ] Configure reranker (Flashrank recommended)
- [ ] Adjust retrieval settings (top-k, similarity threshold)

**Day 3-4: Frontend Enhancement**
- [ ] Create document library view
  - List all uploaded documents
  - Show processing status
  - Delete/archive functionality
  - Search within documents
- [ ] Match Mnemosyne UI/UX style
  - Color scheme
  - Typography
  - Animations
  - Icon consistency
- [ ] Add multimodal result display
  - Image previews
  - Video thumbnails
  - Audio player embeds

**Day 5: External Integrations (Optional)**
- [ ] Enable desired integrations (e.g., GitHub, Notion)
- [ ] Configure OAuth credentials
- [ ] Test integration flows
- [ ] Add UI for managing connected sources

**Deliverables:**
- ✅ Customized SurfSense backend
- ✅ Polished Mnemosyne-styled frontend
- ✅ Document management interface
- ✅ Optional: External sources connected

---

### Week 4: Production Deployment & Testing

**Day 1-2: Production Setup**
- [ ] Create production `docker-compose.yml`
- [ ] Set up environment variable management
- [ ] Configure PostgreSQL persistence
- [ ] Set up Redis persistence
- [ ] Configure file storage (S3 or local volume)
- [ ] Set up SSL/TLS (if deploying publicly)

**Day 3: Testing & QA**
- [ ] Load testing (100 concurrent users)
- [ ] Upload various file types (validation)
- [ ] Query accuracy evaluation (RAGAS if time permits)
- [ ] Performance benchmarking
  - Upload speed
  - Query latency
  - Streaming response time
- [ ] Error handling verification

**Day 4: Documentation**
- [ ] User guide (how to upload, search, manage docs)
- [ ] Developer setup instructions
- [ ] API documentation
- [ ] Deployment guide
- [ ] Configuration reference
- [ ] Troubleshooting guide

**Day 5: Launch Preparation**
- [ ] Final bug fixes
- [ ] Security review
- [ ] Backup/restore procedures
- [ ] Monitoring setup
- [ ] Create demo video/screenshots

**Deliverables:**
- ✅ Production-ready deployment
- ✅ Complete documentation
- ✅ Tested with real workloads
- ✅ Ready for users

---

## Updated File Structure

```
mnemosyne-universal/
├── backend/                        # SurfSense (forked & customized)
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── search.py      # Query endpoints
│   │   │   │   ├── ingest.py      # Upload endpoints
│   │   │   │   ├── documents.py   # Doc management
│   │   │   │   ├── integrations.py # External sources
│   │   │   │   └── admin.py       # Admin APIs
│   │   ├── services/
│   │   │   ├── rag_service.py     # Core RAG logic
│   │   │   ├── llm_service.py     # LLM integration
│   │   │   ├── embedding_service.py
│   │   │   ├── chunking_service.py
│   │   │   └── reranker_service.py
│   │   ├── tasks/
│   │   │   ├── celery_app.py      # Celery config
│   │   │   ├── document_processing.py
│   │   │   └── indexing.py
│   │   ├── models/
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   └── user.py
│   │   └── core/
│   │       ├── config.py
│   │       └── dependencies.py
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                       # Mnemosyne (enhanced)
│   ├── templates/
│   │   ├── index.html             # Chat + upload UI
│   │   └── library.html           # Document library
│   ├── static/
│   │   ├── js/
│   │   │   ├── script.js          # Existing chat (updated)
│   │   │   ├── upload.js          # File upload component
│   │   │   ├── library.js         # Doc management
│   │   │   └── search_transform.js
│   │   ├── css/
│   │   │   ├── style.css
│   │   │   ├── search_style.css
│   │   │   └── upload.css         # New upload styles
│   │   └── img/
│   └── app.py                     # Lightweight server (optional)
│
├── legacy/                        # Archived original Mnemosyne
│   ├── src/
│   │   ├── LLMService.py          # Reference
│   │   ├── MongoService.py        # Reference
│   │   └── MnemsoyneService.py    # Reference
│   └── README.md                  # Why we migrated
│
├── docs/
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_SETUP.md
│   ├── API_REFERENCE.md
│   └── DEPLOYMENT.md
│
├── .claude/
│   ├── skills/
│   │   ├── memory/SKILL.md
│   │   └── swarm/SKILL.md
│   └── CLAUDE.md
│
├── RESEARCH_PLAN.md               # Original plan (build from scratch)
├── REVISED_PLAN.md                # This document (SurfSense-based)
├── docker-compose.yml             # Full stack
└── README.md                      # Project overview
```

---

## API Integration Guide

### Mnemosyne Frontend → SurfSense Backend

**Current Mnemosyne API (MongoDB-based):**
```javascript
// Old: script.js
const API_ID = "http://127.0.0.1:5000/mnemosyne/api/v1/search"
const searchUrl = `${API_ID}/${encodedQuery}-${uniqueId}`;
```

**New: SurfSense API (PostgreSQL-based):**
```javascript
// New: script.js
const SURFSENSE_API = "http://127.0.0.1:8000/api/v1"

// Search endpoint
async function performSearch(query) {
    const response = await fetch(`${SURFSENSE_API}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: query,
            mode: 'async'
        })
    });

    // SSE streaming (SurfSense supports this)
    const reader = response.body.getReader();
    // ... existing streaming logic
}

// Upload endpoint (NEW)
async function uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const response = await fetch(`${SURFSENSE_API}/ingest/file`, {
        method: 'POST',
        body: formData
    });

    return await response.json();
}
```

**SurfSense API Response Format:**
```json
{
  "answer": "Your answer here...",
  "sources": [
    {
      "title": "Document Title",
      "url": "file://path/to/doc.pdf",
      "content": "Relevant excerpt...",
      "score": 0.95
    }
  ],
  "follow_up": [
    "Related question 1?",
    "Related question 2?"
  ],
  "images": [],
  "confidence_score": 0.92
}
```

---

## Configuration Guide

### Environment Variables (.env)

**Core Settings:**
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=surfsense
POSTGRES_USER=surfsense
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
UPLOAD_DIR=/data/uploads
MAX_FILE_SIZE=100MB
```

**LLM Configuration:**
```bash
# OpenAI
OPENAI_API_KEY=sk-...
DEFAULT_LLM_MODEL=gpt-4o-mini
DEFAULT_EMBEDDING_MODEL=text-embedding-3-large

# Ollama (local alternative)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

**ETL Service (Choose ONE):**
```bash
# Option 1: Docling (local, privacy-focused, NO API KEY)
ETL_SERVICE=docling

# Option 2: LlamaCloud (50+ formats, API key required)
ETL_SERVICE=llamacloud
LLAMA_CLOUD_API_KEY=llx-...

# Option 3: Unstructured.io (34+ formats, API key required)
ETL_SERVICE=unstructured
UNSTRUCTURED_API_KEY=...
```

**Reranker:**
```bash
# Flashrank (local, fast, free)
RERANKER_TYPE=flashrank

# OR Cohere (API, more accurate)
RERANKER_TYPE=cohere
COHERE_API_KEY=...
```

**External Integrations (Optional):**
```bash
# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Notion
NOTION_API_KEY=secret_...

# GitHub
GITHUB_TOKEN=ghp_...

# Gmail
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

---

## Migration from Current Mnemosyne

### Step-by-Step Migration

**1. Backup Current Data**
```bash
# Export Medium articles from MongoDB
mongodump --db=Mnemosyne --out=/backup/mnemosyne_backup

# Archive current code
mkdir legacy/
cp -r src/ legacy/
```

**2. Fork & Setup SurfSense**
```bash
# Fork on GitHub
# Clone locally
git clone https://github.com/raghavpatnecha/Mnemosyne-Universal.git
cd Mnemosyne-Universal

# Start services
docker-compose up -d
```

**3. Re-ingest Medium Articles**
```bash
# Option A: Upload PDFs of articles
# Option B: Use Firecrawl integration
# Option C: Direct URL ingestion via SurfSense API

curl -X POST http://localhost:8000/api/v1/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://medium.com/article-url"}'
```

**4. Integrate Mnemosyne Frontend**
```bash
# Copy frontend files to SurfSense
cp -r ../Mnemosyne/src/templates/ frontend/templates/
cp -r ../Mnemosyne/src/static/ frontend/static/

# Update API endpoints in script.js
# Point to SurfSense backend (port 8000)
```

**5. Test & Deploy**
```bash
# Test upload → search flow
# Verify all features working
# Deploy to production
```

---

## External Integration Examples

### 1. Slack Integration

**Enable in SurfSense:**
```bash
# .env
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-app-token
```

**How it works:**
- SurfSense connects to your Slack workspace
- Indexes channels, DMs, threads
- Updates in real-time (new messages indexed)
- Search across Slack + documents together

### 2. Notion Integration

**Enable in SurfSense:**
```bash
# .env
NOTION_API_KEY=secret_your_key
```

**How it works:**
- Connects to Notion workspace
- Indexes pages, databases
- Syncs updates automatically
- Query Notion + files in one search

### 3. GitHub Integration

**Enable in SurfSense:**
```bash
# .env
GITHUB_TOKEN=ghp_your_token
```

**How it works:**
- Index repositories (code, issues, PRs, wikis)
- Search across codebases
- Find relevant code snippets
- Combined with documentation search

---

## Cost Analysis (Updated)

### SurfSense Approach Costs

**Infrastructure (Self-Hosted):**
- Server: $20-50/month (VPS for PostgreSQL + Redis + API)
- Storage: $5-10/month (for uploaded files)
- **Total Infrastructure: ~$30-60/month**

**API Costs (Variable):**

**Option A: Docling ETL (Local) + Local Embeddings**
- ETL: $0 (Docling is local)
- Embeddings: $0 (sentence-transformers local)
- LLM: Ollama local ($0) or OpenAI ($10-50/month)
- **Total: $0-50/month**

**Option B: LlamaCloud ETL + OpenAI Embeddings**
- ETL: LlamaCloud pricing (check their site)
- Embeddings: ~$0.01 per 1K documents (one-time)
- LLM: OpenAI GPT-4o-mini (~$20-100/month depending on usage)
- **Total: $20-150/month**

**Comparison to Building from Scratch:**
- Development time saved: 4 weeks = ~$10,000-20,000 in dev costs
- Infrastructure: Same ($30-60/month)
- API costs: Same (depends on choices)

**ROI: 50% time savings = massive cost savings**

---

## Testing Strategy

### Week 1: SurfSense Validation
- [ ] Upload 10+ different file types
- [ ] Test search accuracy
- [ ] Verify Celery processing
- [ ] Check database indexing
- [ ] Validate API responses

### Week 2: Integration Testing
- [ ] Upload via Mnemosyne UI
- [ ] Search from Mnemosyne chat
- [ ] SSE streaming works
- [ ] Follow-up questions function
- [ ] Citations display correctly

### Week 3: Feature Testing
- [ ] Document library CRUD operations
- [ ] External integration (if enabled)
- [ ] Multimodal content handling
- [ ] Reranking improves results
- [ ] Podcast generation (if using)

### Week 4: Production Testing
- [ ] Load testing (100+ concurrent users)
- [ ] Large file uploads (100MB+)
- [ ] Long-running queries
- [ ] Database performance
- [ ] Error recovery

---

## Success Metrics (Revised)

### Functional Requirements
- [x] Support 50+ file formats ✅ (SurfSense provides)
- [x] External integrations (15+) ✅ (SurfSense provides)
- [x] Hybrid search + reranking ✅ (SurfSense provides)
- [ ] Mnemosyne UI preserved (4 weeks to complete)
- [ ] File upload interface (Week 2)
- [ ] Document management (Week 3)

### Performance Requirements
- [ ] Query latency < 3s (p95)
- [ ] Upload processing < 30s for 10MB PDF
- [ ] Support 100 concurrent users
- [ ] SSE streaming latency < 500ms

### Quality Requirements
- [ ] Retrieval accuracy > 85% (RAGAS)
- [ ] User satisfaction > 4/5
- [ ] Citation accuracy > 90%
- [ ] Zero data loss in production

---

## Risk Assessment (Updated)

### Technical Risks

**Risk 1: SurfSense Learning Curve**
- *Probability:* Medium
- *Impact:* Low (well-documented codebase)
- *Mitigation:* Week 1 dedicated to understanding architecture
- *Fallback:* SurfSense community + Discord support

**Risk 2: Frontend-Backend Integration Issues**
- *Probability:* Medium
- *Impact:* Medium
- *Mitigation:* API contract defined upfront, extensive testing
- *Fallback:* Use SurfSense's React frontend temporarily

**Risk 3: Performance at Scale**
- *Probability:* Low (SurfSense is production-tested)
- *Impact:* High
- *Mitigation:* Load testing in Week 4, PostgreSQL tuning
- *Fallback:* Dedicated vector DB (Qdrant) if needed

**Risk 4: External Integration Complexity**
- *Probability:* Low
- *Impact:* Low (optional features)
- *Mitigation:* Start with file uploads, add integrations later
- *Fallback:* Disable complex integrations initially

### Operational Risks

**Risk 5: Docker Deployment Complexity**
- *Probability:* Low (Docker Compose provided)
- *Impact:* Medium
- *Mitigation:* Test locally first, staging environment
- *Fallback:* Use managed PostgreSQL + Redis (AWS RDS, ElastiCache)

**Risk 6: API Cost Overruns**
- *Probability:* Medium
- *Impact:* Medium
- *Mitigation:* Use Docling (local) + local embeddings, set budget alerts
- *Fallback:* Switch to fully local stack (Ollama + sentence-transformers)

---

## Advantages Over Original Plan

### Original Plan (Build from Scratch):
| Aspect | Status |
|--------|--------|
| Timeline | 8 weeks |
| File formats | Need to integrate MinerU + Docling + Unstructured |
| External integrations | Would need to build 15+ connectors |
| Infrastructure | Set up Celery + Redis from scratch |
| Chunking | Implement Chonkie manually |
| Reranking | Build layer manually |
| Hybrid search | Implement RRF from scratch |
| Production readiness | Untested at scale |
| Community support | None (custom codebase) |
| **Total effort** | **~320 hours** |

### Revised Plan (Fork SurfSense):
| Aspect | Status |
|--------|--------|
| Timeline | 4 weeks |
| File formats | ✅ 50+ formats built-in |
| External integrations | ✅ 15+ integrations ready |
| Infrastructure | ✅ Docker Compose provided |
| Chunking | ✅ Chonkie integrated |
| Reranking | ✅ Multiple options built-in |
| Hybrid search | ✅ RRF implemented |
| Production readiness | ✅ Battle-tested |
| Community support | ✅ Active Discord + GitHub |
| **Total effort** | **~160 hours (50% less!)** |

---

## Next Steps - ACTION PLAN

### Immediate Actions (Today):

1. **Fork SurfSense Repository**
   ```bash
   # On GitHub: Fork MODSetter/SurfSense to raghavpatnecha/Mnemosyne-Universal
   ```

2. **Clone & Initial Setup**
   ```bash
   git clone https://github.com/raghavpatnecha/Mnemosyne-Universal.git
   cd Mnemosyne-Universal
   ```

3. **Review Architecture**
   - Read SurfSense README
   - Understand Docker Compose setup
   - Review API documentation
   - Check configuration options

### Week 1 Kickoff (Start Monday):

**Day 1:**
- [ ] Docker Compose setup
- [ ] Configure .env file
- [ ] Start all services
- [ ] Verify health checks pass

**Day 2:**
- [ ] Upload test documents (PDF, Word, images)
- [ ] Test search functionality
- [ ] Review Celery task logs
- [ ] Verify PostgreSQL indexing

**Day 3-5:**
- [ ] Map API endpoints
- [ ] Test different ETL services (Docling vs LlamaCloud)
- [ ] Understand response formats
- [ ] Document customization points

---

## Final Recommendation

**Use SurfSense as the foundation for Mnemosyne Universal RAG.**

**Why:**
1. ✅ **50+ file formats** (already implemented)
2. ✅ **15+ external integrations** (Slack, Notion, GitHub, etc.)
3. ✅ **Production-ready** (battle-tested infrastructure)
4. ✅ **4 weeks vs 8 weeks** (50% faster)
5. ✅ **50% less development effort** (160 vs 320 hours)
6. ✅ **Apache 2.0 license** (freely fork and customize)
7. ✅ **Active community** (support + updates)
8. ✅ **Keep Mnemosyne frontend** (just enhance with upload UI)

**What to do:**
- Fork SurfSense repository
- Set up locally via Docker Compose
- Add file upload UI to Mnemosyne frontend
- Connect frontend to SurfSense backend
- Customize and deploy

**Timeline:** 4 weeks to production
**Risk:** Low (proven codebase)
**Cost:** Same as build-from-scratch (infrastructure + API costs)
**Effort:** 50% less than building from scratch

---

**Prepared by:** Claude (Mnemosyne Development Team)
**Status:** Ready to Execute
**Next Action:** Fork SurfSense → Start Week 1 setup
