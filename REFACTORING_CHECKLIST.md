# Refactoring Checklist - File Size Compliance

**Goal**: Bring all files under 300-line limit per CLAUDE.md guidelines  
**Timeline**: 3-4 days  
**Priority**: Critical (CLAUDE.md compliance)

---

## 📋 Files Requiring Refactoring

### 🔴 Critical (>350 lines)

- [ ] **backend/api/documents.py** (478 lines → target: ~250)
  - Extract: `document_utils.py`
  - Functions to move:
    - [ ] `build_document_response()` - used in 4 places
    - [ ] `verify_collection_ownership()` - common pattern
    - [ ] `calculate_content_hash()` - hashing logic
    - [ ] `parse_upload_metadata()` - JSON parsing
  - **Estimated reduction**: 228 lines (includes deduplication)
  - **Time**: 3-4 hours

- [ ] **backend/api/retrievals.py** (379 lines → target: ~230)
  - Extract: `retrieval_utils.py`
  - Functions to move:
    - [ ] `_build_chunk_results()` - already isolated
    - [ ] `_enrich_with_graph_context()` - already isolated
    - [ ] `build_cache_params()` - extract from main function
    - [ ] `validate_graph_request()` - extract validation
  - **Estimated reduction**: 149 lines
  - **Time**: 2-3 hours

- [ ] **backend/storage/s3.py** (369 lines → target: ~250)
  - Extract: `s3_utils.py`
  - Functions to move:
    - [ ] `generate_s3_key()` - combine _get_document_key + _get_extracted_content_key
    - [ ] `batch_delete_objects()` - extract batch deletion logic
    - [ ] `verify_user_ownership()` - extract path verification
    - [ ] `download_to_temp()` - extract get_local_path logic
  - **Estimated reduction**: 119 lines
  - **Time**: 2-3 hours

- [ ] **backend/services/lightrag_service.py** (369 lines → target: ~250)
  - Extract: `lightrag_utils.py`
  - Functions to move:
    - [ ] `get_working_dir()` - directory management
    - [ ] `initialize_instance()` - instance creation logic
    - [ ] `cleanup_directory()` - directory cleanup logic
    - [ ] `finalize_instance()` - instance shutdown logic
  - **Estimated reduction**: 119 lines
  - **Time**: 2-3 hours

### 🟡 Warning (300-350 lines)

- [ ] **backend/services/cache_service.py** (326 lines → target: ~250)
  - Extract: `cache_utils.py`
  - Functions to move:
    - [ ] `generate_cache_key()` - combine _make_embedding_key + _make_search_key
    - [ ] `hash_text()` - move _hash function
    - [ ] `serialize_for_cache()` - extract serialization logic
    - [ ] `deserialize_from_cache()` - extract deserialization logic
  - **Estimated reduction**: 76 lines
  - **Time**: 1-2 hours

- [ ] **backend/api/collections.py** (304 lines → target: ~250)
  - Extract: `collection_utils.py`
  - Functions to move:
    - [ ] `build_collection_response()` - used in 4 places
    - [ ] `verify_collection_ownership()` - common pattern
    - [ ] `get_collection_stats()` - document counting logic
  - **Estimated reduction**: 54 lines (includes deduplication)
  - **Time**: 1-2 hours

---

## 🎯 Refactoring Workflow

For each file:

### Step 1: Create Utility Module
```bash
# Example for documents.py
touch backend/api/utils/document_utils.py
```

### Step 2: Move Helper Functions
- Copy functions to utility module
- Add proper imports
- Add comprehensive docstrings
- Add type hints

### Step 3: Update Original File
- Remove moved functions
- Add import for utility module
- Update function calls
- Verify no circular imports

### Step 4: Run Tests
```bash
pytest tests/unit/test_*.py -v
pytest tests/integration/test_*.py -v
```

### Step 5: Verify Line Count
```bash
wc -l backend/api/documents.py
wc -l backend/api/utils/document_utils.py
```

### Step 6: Quality Checks
```bash
# Type checking (if configured)
mypy backend/api/documents.py

# Linting
pylint backend/api/documents.py

# Formatting
black backend/api/documents.py --check
```

### Step 7: Git Commit
```bash
git add backend/api/documents.py backend/api/utils/document_utils.py
git commit -m "refactor(api): extract document utilities to reduce file size

- Moved build_document_response() to document_utils.py
- Moved verify_collection_ownership() to document_utils.py
- Moved calculate_content_hash() to document_utils.py
- Moved parse_upload_metadata() to document_utils.py
- Reduces documents.py from 478 to 250 lines
- Eliminates 4 instances of duplicated response building
- Complies with CLAUDE.md 300-line limit"
```

---

## 📝 Detailed Refactoring Plans

### 1. backend/api/documents.py → document_utils.py

#### Functions to Extract

```python
# backend/api/utils/document_utils.py

from typing import Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import hashlib
import json

from backend.models.document import Document
from backend.models.collection import Collection
from backend.schemas.document import DocumentResponse
from backend.core.exceptions import http_400_bad_request, http_404_not_found


def build_document_response(document: Document) -> DocumentResponse:
    """
    Build DocumentResponse from Document model
    
    Centralized function to avoid code duplication across endpoints.
    
    Args:
        document: Document model instance
    
    Returns:
        DocumentResponse schema instance
    """
    return DocumentResponse(
        id=document.id,
        collection_id=document.collection_id,
        user_id=document.user_id,
        title=document.title,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        content_hash=document.content_hash,
        unique_identifier_hash=document.unique_identifier_hash,
        status=document.status,
        metadata=document.metadata_,
        processing_info=document.processing_info,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


def verify_collection_ownership(
    collection_id: UUID,
    user_id: UUID,
    db: Session
) -> Collection:
    """
    Verify collection exists and belongs to user
    
    Args:
        collection_id: Collection UUID to verify
        user_id: User UUID to verify ownership
        db: Database session
    
    Returns:
        Collection if found and owned by user
    
    Raises:
        HTTPException: 404 if collection not found or not owned by user
    """
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == user_id
    ).first()
    
    if not collection:
        raise http_404_not_found("Collection not found")
    
    return collection


def calculate_content_hash(content: bytes) -> str:
    """
    Calculate SHA-256 hash for content deduplication
    
    Args:
        content: File content bytes
    
    Returns:
        Hexadecimal hash string (64 chars)
    """
    return hashlib.sha256(content).hexdigest()


def parse_upload_metadata(metadata: str) -> Dict[str, Any]:
    """
    Parse and validate JSON metadata from upload
    
    Args:
        metadata: JSON string from form data
    
    Returns:
        Parsed metadata dictionary
    
    Raises:
        HTTPException: 400 if JSON is invalid
    """
    if not metadata:
        return {}
    
    try:
        return json.loads(metadata)
    except json.JSONDecodeError as e:
        raise http_400_bad_request(f"Invalid JSON metadata: {e}")
```

#### Update documents.py

```python
# Replace 4 instances of manual DocumentResponse building with:
from backend.api.utils.document_utils import (
    build_document_response,
    verify_collection_ownership,
    calculate_content_hash,
    parse_upload_metadata
)

# In endpoints:
@router.post("")
async def create_document(...):
    collection = verify_collection_ownership(collection_id, current_user.id, db)
    content = await file.read()
    content_hash = calculate_content_hash(content)
    metadata_dict = parse_upload_metadata(metadata)
    
    # ... rest of logic ...
    
    return build_document_response(document)
```

**Before**: 478 lines  
**After**: ~250 lines (documents.py) + ~80 lines (document_utils.py)  
**Net**: -148 lines (duplication eliminated)

---

### 2. backend/api/retrievals.py → retrieval_utils.py

#### Functions to Extract

```python
# backend/api/utils/retrieval_utils.py

from typing import List, Dict, Any, Tuple
import logging

from backend.schemas.retrieval import ChunkResult, DocumentInfo

logger = logging.getLogger(__name__)


def build_chunk_results(results: List[Dict[str, Any]]) -> List[ChunkResult]:
    """
    Build ChunkResult objects from search results
    
    Args:
        results: List of search result dictionaries
    
    Returns:
        List of ChunkResult schema instances
    """
    return [
        ChunkResult(
            chunk_id=r['chunk_id'],
            content=r['content'],
            chunk_index=r['chunk_index'],
            score=r['score'],
            metadata=r['metadata'],
            chunk_metadata=r['chunk_metadata'],
            document=DocumentInfo(**r['document']),
            collection_id=r['collection_id']
        )
        for r in results
    ]


def enrich_with_graph_context(
    base_results: List[Dict[str, Any]],
    graph_result: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Enrich base search results with knowledge graph context
    
    Implements HybridRAG by combining:
    - Base retrieval (semantic/keyword/hybrid/hierarchical)
    - Graph context (relationships, entities, multi-hop reasoning)
    
    Args:
        base_results: Results from base search
        graph_result: Result from LightRAG query
    
    Returns:
        Tuple of (enriched_results, graph_context_string)
    """
    graph_context = graph_result.get('answer', '')
    graph_chunks = graph_result.get('chunks', [])
    
    base_chunk_ids = {r['chunk_id'] for r in base_results}
    enriched_results = base_results.copy()
    
    for graph_chunk in graph_chunks:
        if graph_chunk['chunk_id'] not in base_chunk_ids:
            graph_chunk_copy = graph_chunk.copy()
            graph_chunk_copy['score'] = min(graph_chunk.get('score', 0.5), 0.7)
            graph_chunk_copy['metadata'] = graph_chunk.get('metadata', {}).copy()
            graph_chunk_copy['metadata']['graph_sourced'] = True
            enriched_results.append(graph_chunk_copy)
            base_chunk_ids.add(graph_chunk['chunk_id'])
    
    logger.info(
        f"Graph enrichment: {len(base_results)} base → "
        f"{len(enriched_results)} enriched"
    )
    
    return enriched_results, graph_context


def build_cache_params(request, current_user) -> Dict[str, Any]:
    """
    Build cache parameter dictionary for search results
    
    Args:
        request: RetrievalRequest instance
        current_user: User instance
    
    Returns:
        Cache parameters dictionary
    """
    return {
        "mode": request.mode.value,
        "top_k": request.top_k,
        "collection_id": str(request.collection_id) if request.collection_id else None,
        "rerank": request.rerank,
        "enable_graph": request.enable_graph,
        "metadata_filter": request.metadata_filter,
        "user_id": str(current_user.id)
    }


def validate_graph_enhancement_request(request, settings) -> None:
    """
    Validate graph enhancement configuration
    
    Args:
        request: RetrievalRequest instance
        settings: Application settings
    
    Raises:
        HTTPException: If LightRAG is not enabled
    """
    from backend.core.exceptions import http_400_bad_request
    
    if request.enable_graph and not settings.LIGHTRAG_ENABLED:
        raise http_400_bad_request(
            "Graph enhancement requested but LightRAG is not enabled. "
            "Set LIGHTRAG_ENABLED=true in configuration."
        )
```

**Before**: 379 lines  
**After**: ~230 lines (retrievals.py) + ~100 lines (retrieval_utils.py)  
**Net**: -49 lines

---

## ✅ Testing Checklist

For each refactored file:

- [ ] All existing tests pass
- [ ] No new pylint warnings
- [ ] No new mypy errors (if configured)
- [ ] File size under 300 lines
- [ ] No circular imports
- [ ] Type hints complete
- [ ] Docstrings present
- [ ] Logging preserved
- [ ] Error handling intact
- [ ] Security checks maintained

---

## 🚀 Progress Tracking

### Day 1
- [ ] Morning: documents.py refactoring
- [ ] Afternoon: retrievals.py refactoring
- [ ] EOD: Run full test suite

### Day 2
- [ ] Morning: s3.py refactoring
- [ ] Afternoon: lightrag_service.py refactoring
- [ ] EOD: Run full test suite

### Day 3
- [ ] Morning: cache_service.py refactoring
- [ ] Afternoon: collections.py refactoring
- [ ] EOD: Full integration testing

### Day 4 (Buffer)
- [ ] Fix any issues from testing
- [ ] Code review
- [ ] Documentation updates
- [ ] Final quality checks

---

## 📊 Metrics

### Before Refactoring
- Files over 300 lines: 6
- Average file size: 351 lines
- Duplicated code: ~200 lines
- CLAUDE.md compliance: 85%

### After Refactoring (Target)
- Files over 300 lines: 0
- Average file size: 225 lines
- Duplicated code: ~0 lines
- CLAUDE.md compliance: 95%

---

## 🎉 Success Criteria

- [ ] All 6 files under 300 lines
- [ ] All tests passing
- [ ] No new linting errors
- [ ] No performance regression
- [ ] Code duplication eliminated
- [ ] Documentation updated
- [ ] Commit messages clear and descriptive

---

## 💡 Tips

1. **One file at a time**: Don't try to refactor everything at once
2. **Test frequently**: Run tests after each function extraction
3. **Commit often**: Small, focused commits are easier to review and revert
4. **Check imports**: Watch for circular dependencies
5. **Preserve behavior**: Don't change logic, only structure
6. **Update docs**: Keep docstrings and comments in sync
7. **Ask for review**: Get another pair of eyes before merging

---

## 📞 Questions?

See [CODE_REVIEW.md](./CODE_REVIEW.md) for full context and analysis.
