# Mnemosyne Architecture Overview

## Core Components

Mnemosyne uses a **hybrid RAG architecture** combining multiple retrieval methods:

### 1. PostgreSQL with pgvector
- **Purpose**: Vector embeddings storage for semantic search
- **What it stores**:
  - Document chunks with embeddings
  - User data, collections, documents metadata
  - Search indexes for fast retrieval
- **Used for**: Semantic and keyword search modes

### 2. LightRAG (Knowledge Graph) ⭐
- **Purpose**: Graph-based RAG with entity extraction
- **What it stores**:
  - Knowledge graph (entities + relationships)
  - Graph embeddings
  - Entity and relationship metadata
- **Storage**: File-based in `/app/data/lightrag` (persistent volume)
- **Used for**: Graph search mode (mode="graph")

### 3. Redis
- **Purpose**: Caching and task queue
- **What it stores**:
  - Embedding cache (24h TTL)
  - Search results cache (1h TTL)
  - Celery task queue
  - Rate limiting counters
- **Used for**: Performance optimization

## Search Modes Explained

### 1. Semantic Search (PostgreSQL + pgvector)
```python
mode="semantic"
```
- Uses embeddings stored in PostgreSQL
- Vector similarity search
- Best for: Conceptual similarity

### 2. Keyword Search (PostgreSQL full-text)
```python
mode="keyword"
```
- Uses PostgreSQL full-text search
- BM25 ranking algorithm
- Best for: Exact term matching

### 3. Hybrid Search (PostgreSQL)
```python
mode="hybrid"  # Default
```
- Combines semantic + keyword
- Reciprocal Rank Fusion (RRF)
- Best for: General use (recommended)

### 4. Hierarchical Search (PostgreSQL)
```python
mode="hierarchical"
```
- Two-tier: document-level → chunk-level
- Uses PostgreSQL with hierarchical indexing
- Best for: Long documents with structure

### 5. Graph Search (LightRAG) ⭐
```python
mode="graph"  # Uses LightRAG!
```
- **Knowledge graph retrieval**
- Entity and relationship extraction
- Dual-level retrieval (local + global)
- **Source extraction**: Real chunk IDs from PostgreSQL for citations
- **Storage**: File-based in LightRAG working directory
- Best for: Complex reasoning, entity relationships

**How it works**:
1. LightRAG queries knowledge graph for context
2. System performs semantic search to find actual source chunks
3. Returns real chunk IDs and document references for citations
4. Response format consistent with other search modes

### 6. Graph Enhancement (HybridRAG) 🚀 NEW

Combine ANY search mode with knowledge graph enrichment using `enable_graph=True`.

```python
# Standard hybrid search
results = client.retrievals.retrieve("query", mode="hybrid")

# HybridRAG: hybrid + graph
results = client.retrievals.retrieve("query", mode="hybrid", enable_graph=True)
```

**What is HybridRAG?**
- Combines traditional retrieval (semantic/keyword/hybrid/hierarchical) with LightRAG
- Based on production systems (AWS, Neo4j, Databricks, Cedars-Sinai)
- Provides both relevant chunks AND relationship context
- Works with semantic, keyword, hybrid, or hierarchical modes

**How it works**:
1. Base search (e.g., hybrid) and LightRAG query run **in parallel**
2. Results are merged with deduplication
3. Graph-sourced chunks are marked with `metadata.graph_sourced: true`
4. Response includes `graph_context` field with relationship narrative
5. Latency: ~1.5-2x vs base (parallel execution, not additive)

**Performance**:
- **Accuracy**: 35-80% improvement for relationship-based queries (research-backed)
- **Latency**: 200-500ms (vs 100-300ms for base search)
- **Use case**: Complex queries needing both relevance AND relationships

**Example Use Cases**:
- ✅ "How does protein X interact with disease Y?" → needs relationships
- ✅ "What's the connection between climate change and economic policy?" → needs context links
- ✅ Research queries requiring multi-hop reasoning
- ❌ "What is machine learning?" → simple lookup (use base search)

**Architecture Flow**:
```
User Query
    ├── Base Search (hybrid/semantic/keyword/hierarchical)
    └── Graph Query (LightRAG)
         ↓
    Parallel Execution (asyncio.gather)
         ↓
    Merge Results + Deduplicate
         ↓
    Return: chunks + graph_context
```

## Data Flow

### Document Ingestion
1. User uploads document → API
2. Celery task extracts text
3. Text chunked (512 tokens)
4. **Parallel processing**:
   - Embeddings → PostgreSQL (for semantic/hybrid/hierarchical)
   - Full document → LightRAG (for graph extraction)
5. LightRAG builds knowledge graph:
   - Extracts entities
   - Identifies relationships
   - Creates graph embeddings
   - Stores in `/app/data/lightrag`

### Search Query
1. User sends query
2. API receives mode parameter
3. **Route based on mode**:
   - `semantic/keyword/hybrid/hierarchical` → PostgreSQL
   - `graph` → LightRAG + PostgreSQL (source extraction)
4. **For graph mode**:
   - LightRAG returns synthesized context from knowledge graph
   - System searches PostgreSQL to find actual source chunks
   - Returns both graph context and real chunk IDs
5. Results ranked and returned

## Storage Breakdown

### PostgreSQL (postgres_data volume)
- User accounts and API keys
- Collections and documents metadata
- **Vector embeddings** (1536 dimensions)
- Chunks with metadata
- Chat sessions and messages
- Size: ~10GB for 10k documents

### LightRAG (lightrag_data volume) ⭐
- **Knowledge graph files**
- Entity embeddings
- Relationship graph
- Incremental updates
- Size: ~2-5GB for 10k documents

### Redis (redis_data volume)
- Embedding cache
- Search cache
- Celery queue
- Size: ~1GB

### Uploads (./uploads)
- Original files (PDF, DOCX, MP4)
- Size: Varies by usage

## Why Both PostgreSQL AND LightRAG?

**Different retrieval paradigms**:

1. **PostgreSQL** = Vector/keyword search
   - Fast, scalable
   - Good for finding similar chunks
   - Works with embeddings

2. **LightRAG** = Graph-based reasoning
   - Understands entities and relationships
   - Better for "Who, What, When" questions
   - Knowledge graph traversal
   - More context-aware

**Example**:
- Query: "How is transformers architecture related to BERT?"
- **Hybrid mode** (PostgreSQL): Finds chunks mentioning both
- **Graph mode** (LightRAG): Understands the relationship graph:
  ```
  Transformers → invented_by → Vaswani et al.
  BERT → based_on → Transformers
  BERT → type_of → Encoder-only architecture
  ```

## Production Requirements

### Must Have (Core Architecture)
- ✅ PostgreSQL with pgvector
- ✅ LightRAG working directory (persistent volume) ⭐
- ✅ Redis (caching + queue)

### Optional (Enhancements)
- Prometheus (monitoring)
- Grafana (dashboards)
- Nginx (reverse proxy)

## Volume Persistence

**Critical volumes** that MUST persist:

1. `postgres_data` → Database with embeddings
2. `lightrag_data` → Knowledge graph ⭐ **CRITICAL**
3. `redis_data` → Cache (can be ephemeral)
4. `uploads` → Original files

⚠️ **If you lose `lightrag_data`, you'll need to rebuild the knowledge graph from scratch!**

## Configuration Priority

1. **PostgreSQL** - Always needed
2. **LightRAG** - Needed for graph mode ⭐
3. **Redis** - Needed for Celery + caching
4. **Nginx** - Optional (production reverse proxy)
5. **Monitoring** - Optional but recommended

## Document Processing Pipeline

### Parsers (14 total)

Mnemosyne supports parsing of various file formats:

| Parser | File Types | Description |
|--------|------------|-------------|
| Docling | PDF, DOCX, HTML | Primary document parser |
| PPT | PPTX, PPT | PowerPoint presentations |
| JSON | JSON, JSONL | Structured data |
| Email | EML | Email messages with attachments |
| Excel | XLSX, XLS | Spreadsheets |
| Image | PNG, JPG, GIF | Images with OCR/vision |
| Video | MP4, AVI, MOV | Video with transcription |
| Audio | MP3, WAV | Audio transcription |
| YouTube | URLs | YouTube video processing |
| Text | TXT, MD | Plain text files |
| Figure | Embedded | Figure extraction from documents |

### Processors (9 total)

Domain-specific processors enhance chunking and metadata:

| Processor | Purpose | Detection Keywords |
|-----------|---------|-------------------|
| Academic | Research papers | abstract, methodology, references |
| Legal | Legal documents | whereas, hereby, jurisdiction |
| QA | FAQ documents | question, answer, faq |
| Table | Structured tables | Auto-detected from content |
| Book | Books/chapters | chapter, section, volume |
| Email | Email threads | From:, To:, Subject: |
| Manual | Technical docs | guide, how-to, installation |
| Presentation | Slide decks | slide, presentation, deck |
| Resume | CVs/resumes | experience, skills, education |

### Vision Pipeline (Optional)

For advanced document analysis:

- **Layout Recognizer**: YOLOv10-based detection (10 layout types)
- **OCR Service**: PaddleOCR for text extraction
- **Vision Operators**: Image preprocessing utilities

---

## Summary

Your architecture is **hybrid multi-modal RAG**:
- PostgreSQL handles 4 search modes (semantic, keyword, hybrid, hierarchical)
- LightRAG handles 1 mode (graph) with knowledge graph
- Both work together for comprehensive RAG coverage
- 14 parsers support diverse file formats
- 9 domain processors provide specialized handling

This gives users flexibility to choose the best retrieval method for their query!
