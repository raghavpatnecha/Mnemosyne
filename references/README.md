# Reference Implementations

This directory contains reference implementations for Mnemosyne development.

## Required Repositories

### 1. SurfSense (NotebookLM Clone)
**Repository:** https://github.com/DAMG7245/surf-sense
**Purpose:** Reference for production-ready RAG architecture patterns

**To clone:**
```bash
cd /home/user/Mnemosyne/references
git clone https://github.com/DAMG7245/surf-sense.git surfsense
```

**Key files to study:**
```
surfsense_backend/
├── app/
│   ├── db.py                          # All database models (learn structure)
│   ├── routes/
│   │   ├── documents_routes.py        # Document upload patterns
│   │   ├── chats_routes.py            # Chat API patterns
│   │   └── google_gmail_add_connector_route.py  # Connector patterns
│   ├── services/
│   │   ├── llm_service.py             # Multi-model LLM service
│   │   ├── reranker_service.py        # Multiple rerankers (Cohere, Pinecone, Flashrank)
│   │   ├── docling_service.py         # Advanced parsing
│   │   └── connector_service.py       # Multi-source connectors
│   ├── retriver/
│   │   ├── chunks_hybrid_search.py    # Hybrid search implementation
│   │   └── documents_hybrid_search.py # Two-tier retrieval
│   └── tasks/
│       ├── celery_tasks/
│       │   ├── document_tasks.py      # Document processing tasks
│       │   └── podcast_tasks.py       # Podcast generation
│       ├── document_processors/
│       │   ├── file_processors.py     # 50+ format parsers
│       │   ├── url_crawler.py         # Web scraping
│       │   └── youtube_processor.py   # Video transcription
│       └── connector_indexers/
│           └── (various connectors)
```

### 2. RAG-Anything (Multimodal RAG)
**Repository:** https://github.com/ictnlp/RAG-Anything
**Purpose:** Multimodal document understanding (images, tables, equations)

**To clone:**
```bash
cd /home/user/Mnemosyne/references
git clone https://github.com/ictnlp/RAG-Anything.git rag-anything
```

**Key files to study:**
```
rag-anything/
├── lightrag/                   # LightRAG integration
│   ├── kg_rag.py              # Knowledge graph RAG
│   ├── chunk_module.py        # Advanced chunking
│   └── insert_module.py       # Document insertion
├── multimodal/
│   ├── vision_model.py        # VLM integration
│   ├── image_parser.py        # Image understanding
│   └── table_parser.py        # Table extraction
└── pipelines/
    ├── text_pipeline.py       # Text processing
    └── multimodal_pipeline.py # Multimodal processing
```

## Why These References?

### From Audit Findings
Based on `IMPLEMENTATION_AUDIT.md`, we need:

1. **50+ File Format Support** → SurfSense `file_processors.py`
2. **Multi-Source Connectors** → SurfSense connector patterns
3. **Hierarchical Indices** → SurfSense two-tier retrieval
4. **Multiple Rerankers** → SurfSense reranker service
5. **LiteLLM Integration** → SurfSense LLM service
6. **Multimodal Support** → RAG-Anything pipelines

## Usage Pattern

### Study Before Implementation
1. Clone both repositories
2. Read the specific files listed above
3. Understand the patterns (don't copy-paste)
4. Adapt patterns to Mnemosyne architecture
5. Maintain CLAUDE.md compliance (no emojis, <300 lines, etc.)

### Integration Strategy
- **Don't fork:** We maintain our own clean codebase
- **Learn patterns:** Study their architecture decisions
- **Adapt, don't copy:** Fit patterns into Mnemosyne's structure
- **Keep it modular:** Maintain our service-oriented architecture

## Next Steps

See `PHASE_2_ROADMAP.md` for the implementation plan using these references.
