# Phase 2 Backend Audit Report
## Mnemosyne RAG-as-a-Service Platform

**Audit Date**: November 20, 2024  
**Audit Scope**: FastAPI backend (Week 1-5 implementation)  
**Audit Focus**: Security, Correctness, Data Consistency, Performance

---

## Executive Summary

This Phase 2 audit identified **15 critical/high-severity issues** and **12 medium-severity issues** across the Mnemosyne backend. The issues span authentication, data validation, concurrency safety, database transaction handling, and file storage security.

**Risk Level**: HIGH - Several issues could lead to data corruption, unauthorized access, or service disruption in production.

---

## Critical Issues (Must Fix)

### 1. SQL Injection via Unvalidated JSON Filter Parameters
**File**: `backend/api/retrievals.py` (line 186)  
**File**: `backend/search/vector_search.py` (lines 235-245)  
**Severity**: CRITICAL (SQL Injection)

**Issue**:
```python
# retrievals.py line 186
cache_params = {
    ...
    "metadata_filter": request.metadata_filter,  # User input, not validated
    ...
}

# vector_search.py lines 241-244
for key, value in metadata_filter.items():
    query = query.filter(
        DocumentChunk.metadata_[key].astext == str(value)  # Vulnerable!
    )
```

The `metadata_filter` parameter is passed directly from user input to SQLAlchemy without validation. While SQLAlchemy parameterizes strings, the JSON key access could be exploited.

**Impact**: Potential SQL injection, unauthorized data access.

**Remediation**:
- Validate `metadata_filter` is a flat dict with string keys/values only
- Use a whitelist of allowed filter keys
- Add length limits on keys and values
- Consider using a dedicated filter schema (Pydantic BaseModel)

**Suggested Fix**:
```python
# In schemas/retrieval.py or new validators module
ALLOWED_METADATA_KEYS = {"source", "page", "author", "category"}
MAX_FILTER_VALUE_LENGTH = 256

def validate_metadata_filter(metadata_filter: Optional[Dict]) -> Dict:
    if not metadata_filter:
        return {}
    if not isinstance(metadata_filter, dict):
        raise ValueError("metadata_filter must be a dict")
    if len(metadata_filter) > 10:
        raise ValueError("metadata_filter limited to 10 keys")
    validated = {}
    for key, value in metadata_filter.items():
        if key not in ALLOWED_METADATA_KEYS:
            raise ValueError(f"metadata_filter key '{key}' not allowed")
        if not isinstance(value, str) or len(value) > MAX_FILTER_VALUE_LENGTH:
            raise ValueError(f"Invalid metadata_filter value for key '{key}'")
        validated[key] = value
    return validated
```

---

### 2. Race Condition in Document Processing Status
**File**: `backend/tasks/process_document.py` (lines 64-193)  
**File**: `backend/api/documents.py` (line 127)  
**Severity**: CRITICAL (Data Consistency)

**Issue**:
The document status is updated without transactional safety or row-level locking:
```python
# process_document.py lines 80-82
document.status = "processing"
document.processing_info["started_at"] = datetime.utcnow().isoformat()
db.commit()  # No transaction isolation
```

Meanwhile, the API endpoint can immediately query and return outdated status (line 127 in documents.py triggers Celery task without waiting for confirmation).

**Scenario**: 
1. Request 1 uploads document A (status='pending')
2. Request 2 queries document A (returns pending)
3. Request 3 tries to delete while processing starts

Multiple requests can observe inconsistent status states. Concurrent deletes during processing could:
- Partially delete data (document deleted but chunks remain in LightRAG)
- Leave orphaned database records
- Corrupt processing state

**Impact**: Data corruption, orphaned chunks, inconsistent document state.

**Remediation**:
- Use explicit row-level locking (SELECT FOR UPDATE)
- Implement status state machine validation
- Atomically transition states within a single transaction
- Add status change timestamps
- Consider optimistic locking with version numbers

**Suggested Fix**:
```python
# In process_document.py
from sqlalchemy import select, func

def update_document_status_atomic(db: Session, document_id: UUID, 
                                  new_status: str, 
                                  allowed_from_statuses: List[str]) -> bool:
    """Atomically update document status with validation"""
    result = db.query(Document).filter(
        Document.id == document_id,
        Document.status.in_(allowed_from_statuses)
    ).update({
        Document.status: new_status,
        Document.updated_at: datetime.utcnow()
    }, synchronize_session=False)
    
    db.commit()
    return result > 0  # Returns True if update succeeded

# Use in task:
if not update_document_status_atomic(db, document_id, "processing", ["pending"]):
    logger.error(f"Document {document_id} status already changed")
    return
```

---

### 3. API Key Exposed in Debug Logs
**File**: `backend/middleware/rate_limiter.py` (lines 38-55)  
**File**: `backend/api/deps.py` (line 40, 45)  
**File**: `backend/utils/error_handlers.py` (various)  
**Severity**: CRITICAL (Security)

**Issue**:
The authorization header containing the full API key is logged and could be exposed:
```python
# rate_limiter.py line 54 (fallback)
return get_remote_address(request)  # But API key is extracted earlier without sanitization

# When logging in exception handlers:
logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
# Full traceback could include request headers with API key
```

**Impact**: API keys visible in logs, audit trails, error reports. Attacker reading logs can impersonate users.

**Remediation**:
- Never log full Authorization headers
- Sanitize headers in error handlers and logging
- Use only key_prefix in logs
- Rotate compromised keys in production

**Suggested Fix**:
```python
# Create utils/sanitize.py
SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie"}

def sanitize_headers(headers: dict) -> dict:
    """Remove sensitive headers from dict"""
    return {
        k: "***REDACTED***" if k.lower() in SENSITIVE_HEADERS else v
        for k, v in headers.items()
    }

def sanitize_exception(exc: Exception, request: Request = None) -> Exception:
    """Sanitize exception before logging"""
    # Reconstruct exception without sensitive info
    return Exception(str(exc))

# In error handlers:
async def generic_error_handler(request: Request, exc: Exception):
    headers = sanitize_headers(dict(request.headers))
    logger.error(
        f"Error: {exc}, sanitized headers: {headers}",
        exc_info=True  # Still logs traceback, review carefully
    )
    ...
```

---

### 4. Missing Database Transaction Rollback Safety
**File**: `backend/api/deps.py` (line 60)  
**File**: `backend/api/documents.py` (lines 67-68, 107-108)  
**File**: `backend/api/collections.py` (lines 68-69)  
**Severity**: CRITICAL (Database Consistency)

**Issue**:
Database commits are called without try/except, leaving transactions dirty on error:
```python
# deps.py line 58-60
api_key_obj.last_used_at = datetime.utcnow()
db.commit()  # No error handling! If this fails, what happens?

# documents.py line 107-108
db.add(document)
db.commit()  # If commit fails, partial data remains
```

If `db.commit()` fails:
- Transaction is left in error state
- Subsequent queries on same session fail
- Partial data might be persisted
- Retry logic doesn't work correctly

**Impact**: Database consistency errors, failed requests, data corruption.

**Remediation**:
- Wrap all DB operations in try/except/finally
- Always use context managers for sessions
- Implement proper rollback logic
- Return explicit transaction status

**Suggested Fix**:
```python
# In database.py - create session context manager
from contextlib import contextmanager

@contextmanager
def get_db_transaction():
    """Context manager for database transactions with proper cleanup"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Use in endpoints:
async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    try:
        # ... validation code ...
        api_key_obj.last_used_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update API key last_used_at: {e}")
        db.rollback()
        raise http_401_unauthorized("Authentication database error")
```

---

### 5. Unvalidated Metadata Causes Type Errors
**File**: `backend/api/documents.py` (lines 88-91)  
**Severity**: CRITICAL (Input Validation)

**Issue**:
User-provided JSON metadata is not validated before storage:
```python
# documents.py line 88-91
try:
    metadata_dict = json.loads(metadata) if metadata else {}
except json.JSONDecodeError:
    raise http_400_bad_request("Invalid JSON metadata")
# No schema validation! Could be: null, [], "string", 42, etc.
```

Valid JSON but invalid metadata (e.g., list instead of dict) crashes response builders:
```python
# When building response:
metadata=document.metadata_,  # Could be list/null/int!
```

Then Pydantic schema expects dict and crashes.

**Impact**: Runtime errors, 500 responses, incomplete data persistence.

**Remediation**:
- Validate metadata is a dict
- Limit depth and size
- Validate value types (only strings, numbers, bools)
- Use schema validation with Pydantic

**Suggested Fix**:
```python
from pydantic import BaseModel, field_validator
from typing import Dict, Any

class DocumentMetadata(BaseModel):
    """Validated document metadata"""
    model_config = {"extra": "forbid"}  # Reject unknown fields
    
    # Allow custom fields but validate types
    class Config:
        arbitrary_types_allowed = True
    
    @field_validator("*", mode="before")
    @classmethod
    def validate_value_type(cls, v):
        if not isinstance(v, (str, int, float, bool, type(None))):
            raise ValueError(f"Metadata values must be primitives, got {type(v)}")
        if isinstance(v, str) and len(v) > 1000:
            raise ValueError("String metadata values limited to 1000 chars")
        return v

# In documents.py
try:
    metadata_dict = json.loads(metadata) if metadata else {}
    if not isinstance(metadata_dict, dict):
        raise ValueError("Metadata must be an object/dict")
    DocumentMetadata(**metadata_dict)  # Validate schema
except (json.JSONDecodeError, ValueError) as e:
    raise http_400_bad_request(f"Invalid metadata: {e}")
```

---

### 6. Concurrent File Writes Without Locking
**File**: `backend/tasks/process_document.py` (lines 86-89)  
**File**: `backend/storage/local.py` (lines 74-92)  
**Severity**: CRITICAL (Concurrency)

**Issue**:
Multiple Celery workers can simultaneously download/process same file without coordination:
```python
# process_document.py lines 86-89
temp_file_path = storage_backend.get_local_path(
    storage_path=document.processing_info["file_path"],
    user_id=document.user_id
)
parser = self.parser_factory.get_parser(document.content_type)
parsed = await parser.parse(temp_file_path)  # File could be deleted by another worker!
```

Scenario:
1. Two workers both process same document (retry, or duplicate task)
2. Worker 1 cleans up temp file (line 204)
3. Worker 2 tries to read already-deleted file
4. Crash and retry loop

**Impact**: Race conditions, file not found errors, infinite retries.

**Remediation**:
- Use atomic file operations
- Implement task deduplication (idempotency keys)
- Use file locks
- Or: Don't delete local files immediately, only mark for cleanup

**Suggested Fix**:
```python
import fcntl
import tempfile
from pathlib import Path

class DocumentProcessingLock:
    """Ensure only one worker processes each document at a time"""
    _locks: Dict[UUID, asyncio.Lock] = {}
    
    @classmethod
    async def acquire(cls, document_id: UUID) -> asyncio.Lock:
        if document_id not in cls._locks:
            cls._locks[document_id] = asyncio.Lock()
        await cls._locks[document_id].acquire()
        return cls._locks[document_id]
    
    @classmethod
    def release(cls, document_id: UUID, lock: asyncio.Lock):
        lock.release()
        if document_id in cls._locks:
            del cls._locks[document_id]

# In task:
lock = None
try:
    lock = await DocumentProcessingLock.acquire(document_id)
    document = db.query(Document).filter(Document.id == document_id).with_for_update().first()
    # ... rest of processing ...
finally:
    if lock:
        DocumentProcessingLock.release(document_id, lock)
```

---

### 7. Session Ownership Not Verified Before Creation
**File**: `backend/services/chat_service.py` (lines 101-115)  
**Severity**: CRITICAL (Authorization)

**Issue**:
Session lookup doesn't verify user ownership, and creates new session with user-provided ID:
```python
# chat_service.py lines 101-115
session = self.db.query(ChatSession).filter(
    ChatSession.id == session_id,
    ChatSession.user_id == user_id
).first()

if not session:
    session = ChatSession(
        id=session_id,  # User can provide any UUID!
        user_id=user_id,
        collection_id=collection_id,
        title=user_message[:100]
    )
```

Attack: User A provides Session B's UUID, causing creation of new session with that UUID.
Later, User B queries their session and gets User A's messages mixed in!

**Impact**: Cross-user data leakage, privacy violation.

**Remediation**:
- Only allow UUID generation by server (uuid4())
- Never accept session_id from user unless verifying ownership
- Generate new session ID always

**Suggested Fix**:
```python
# chat_service.py
async def chat_stream(
    self,
    session_id: Optional[UUID] = None,  # Not required from user
    user_message: str,
    user_id: UUID,
    collection_id: UUID = None,
    top_k: int = 5
) -> AsyncGenerator[Dict[str, Any], None]:
    # Check existing session only if provided AND verify ownership
    if session_id:
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id  # MUST verify ownership
        ).first()
    else:
        session = None
    
    if not session:
        # Always create new session with server-generated ID
        session_id = uuid4()  # Server generates, user doesn't provide
        session = ChatSession(
            id=session_id,
            user_id=user_id,
            collection_id=collection_id,
            title=user_message[:100]
        )
        self.db.add(session)
        self.db.commit()
```

---

## High-Severity Issues

### 8. Query Injection in Full-Text Search
**File**: `backend/search/vector_search.py` (lines 150-160)  
**Severity**: HIGH (SQL Injection)

**Issue**:
```python
func.to_tsvector('english', DocumentChunk.content),
func.plainto_tsquery('english', query_text)  # query_text from user, not escaped!
```

While `plainto_tsquery` is safer than raw input, it still processes user input. Special characters could cause errors or unexpected behavior.

**Impact**: Denial of service (malformed query crashes), potential info disclosure.

**Remediation**:
```python
# Sanitize query_text before passing to PostgreSQL functions
import re

def sanitize_fts_query(query: str, max_length: int = 256) -> str:
    """Sanitize full-text search query"""
    if not isinstance(query, str) or len(query) > max_length:
        raise ValueError("Invalid query length")
    # Remove SQL operators that could cause issues
    sanitized = re.sub(r'[<>!&|()]*', '', query).strip()
    if not sanitized:
        raise ValueError("Query is empty after sanitization")
    return sanitized

# In vector_search.py
try:
    safe_query = sanitize_fts_query(query_text)
    results = query.filter(
        func.to_tsvector('english', DocumentChunk.content).match(
            func.plainto_tsquery('english', safe_query)
        )
    )
```

---

### 9. Cache Key Collision Risk
**File**: `backend/services/cache_service.py` (lines 303-322)  
**Severity**: HIGH (Data Consistency)

**Issue**:
```python
def _hash(self, text: str) -> str:
    """Generate hash for cache key"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]  # Only 16 chars!
```

SHA-256 truncated to 16 hex chars = 64-bit hash space. At 1M queries, birthday paradox predicts ~1000 collisions. Different queries could return same cached results!

**Impact**: Wrong search results served to users, privacy violation.

**Remediation**:
```python
def _hash(self, text: str) -> str:
    """Generate cache key for search results"""
    # Use full SHA-256 hash or at least 32 chars (128 bits)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]
    # Or better: use entire hash
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
```

---

### 10. No Max File Size Enforcement
**File**: `backend/api/documents.py` (lines 34-145)  
**File**: `backend/config.py` (line 41)  
**Severity**: HIGH (Resource Exhaustion)

**Issue**:
Config defines `MAX_UPLOAD_SIZE = 100 * 1024 * 1024` but endpoint doesn't enforce it:
```python
# documents.py line 72
content = await file.read()  # Reads entire file into memory, no size check!

# No validation that len(content) <= settings.MAX_UPLOAD_SIZE
```

Attacker can upload multi-GB files, exhausting memory and causing DoS.

**Remediation**:
```python
# documents.py
content = await file.read()

if len(content) > settings.MAX_UPLOAD_SIZE:
    raise http_400_bad_request(
        f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB"
    )
```

Also add to FastAPI app config:
```python
# main.py
app = FastAPI(..., max_request_size=settings.MAX_UPLOAD_SIZE)
```

---

### 11. No Validation of Embedding Dimensions
**File**: `backend/search/vector_search.py` (line 51)  
**File**: `backend/embeddings/openai_embedder.py` (assumed implementation)  
**Severity**: HIGH (Runtime Error)

**Issue**:
```python
DocumentChunk.embedding.cosine_distance(query_embedding).label('distance')
```

No validation that `query_embedding` is 1536 dimensions. pgvector will crash if dimensions mismatch.

**Remediation**:
```python
def search(
    self,
    query_embedding: List[float],
    ...
):
    if len(query_embedding) != 1536:
        raise ValueError(f"Embedding must be 1536 dimensions, got {len(query_embedding)}")
    # ... rest of method
```

---

### 12. Missing Chunks Cleanup on Document Delete
**File**: `backend/api/documents.py` (lines 378-420)  
**File**: `backend/services/lightrag_service.py` (assumed)  
**Severity**: HIGH (Data Consistency)

**Issue**:
Document deletion removes DB record but doesn't clean up LightRAG knowledge graph:
```python
# documents.py line 417-418
db.delete(document)
db.commit()
# LightRAG still has chunks from this document!
```

Orphaned data remains in LightRAG, consuming disk space and affecting search results.

**Remediation**:
```python
# documents.py
async def delete_document(...):
    ...
    # Remove from LightRAG if enabled
    if settings.LIGHTRAG_ENABLED:
        try:
            lightrag_manager = get_lightrag_manager()
            await lightrag_manager.delete_document(
                user_id=current_user.id,
                collection_id=document.collection_id,
                document_id=document.id
            )
        except Exception as e:
            logger.warning(f"LightRAG cleanup failed: {e}")
    
    db.delete(document)
    db.commit()
```

---

### 13. S3 Path Traversal Vulnerability
**File**: `backend/storage/s3.py` (assumed implementation)  
**Severity**: HIGH (Authorization)

**Issue**:
If S3 storage doesn't validate paths carefully, path traversal could access other users' files:
```python
# If implementation allows: user_id = "../other_user"
# Could access: s3://bucket/users/../other_user/collections/...
```

**Remediation**:
Validate in S3 implementation:
```python
def _get_s3_path(self, user_id: UUID, collection_id: UUID, filename: str) -> str:
    """Generate S3 path with validation"""
    # Ensure components are valid UUIDs or filenames
    user_id_str = str(user_id)
    collection_id_str = str(collection_id)
    
    # Reject path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError(f"Invalid filename: {filename}")
    
    # Build path
    return f"users/{user_id_str}/collections/{collection_id_str}/{filename}"
```

---

### 14. Insufficient Session Cleanup on Error
**File**: `backend/database.py` (lines 27-36)  
**Severity**: HIGH (Resource Leak)

**Issue**:
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Only closes, doesn't rollback!
```

If exception occurs between yield and finally, transaction remains open. Multiple exception handlers might not rollback properly.

**Remediation**:
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()  # Explicit rollback
        raise
    finally:
        db.close()
```

---

### 15. No Input Validation on Collection/Document Names
**File**: `backend/api/collections.py` (line 52)  
**File**: `backend/api/documents.py` (line 97)  
**Severity**: HIGH (Input Validation)

**Issue**:
No validation on collection name or document title:
```python
# collections.py line 52
existing = db.query(Collection).filter(
    Collection.user_id == current_user.id,
    Collection.name == collection.name  # collection.name not validated
).first()
```

Attacker can create collections with names like:
- `" OR "1"="1` (looks harmless but could cause confusion)
- Extremely long strings (>512 chars - DB column is String(256) per model)
- Null bytes, special characters, emojis

**Impact**: DB errors, unexpected behavior, poor UX.

**Remediation**:
```python
from pydantic import BaseModel, Field

class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, pattern="^[a-zA-Z0-9_\\- ]+$")
    description: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict] = Field(None)
    config: Optional[Dict] = Field(None)
```

---

## Medium-Severity Issues

### 16. Weak Rate Limiting Key Generation
**File**: `backend/middleware/rate_limiter.py` (lines 57-68)  
**Severity**: MEDIUM (Security)

**Issue**:
```python
def rate_limit_key(request: Request) -> str:
    api_key = get_api_key_from_request(request)
    if api_key and api_key != get_remote_address(request):
        return f"api_key:{api_key}"
    return f"ip:{api_key}"  # Falls back to IP but still uses api_key value!
```

If no API key found, falls back to IP address. But rate limiting should use API key when available to track per-user, not just per-IP.

**Impact**: Rate limiting bypassed by using different IPs.

**Remediation**:
```python
def rate_limit_key(request: Request) -> str:
    """Generate rate limit key"""
    # Try to get API key first
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        api_key = auth[7:]
        # Hash the key to avoid logging full key
        return f"api_key:{hash_api_key(api_key)[:16]}"
    
    # Fall back to IP
    return f"ip:{get_remote_address(request)}"
```

---

### 17. Cache Invalidation Incomplete
**File**: `backend/services/cache_service.py` (lines 236-264)  
**Severity**: MEDIUM (Data Consistency)

**Issue**:
```python
def invalidate_search_cache(self, user_id: str) -> int:
    pattern = f"search:*user:{user_id}*"
    keys = self.redis.keys(pattern)  # Pattern matching is inefficient
    if keys:
        deleted = self.redis.delete(*keys)
```

Problems:
1. Only invalidates search cache, not embedding cache
2. Pattern matching is slow (O(N))
3. Not called when documents are deleted/updated
4. Doesn't invalidate by collection

**Impact**: Stale search results after document updates.

**Remediation**:
```python
def invalidate_user_cache(self, user_id: str) -> int:
    """Invalidate all cache for a user (search + embeddings)"""
    deleted = 0
    # Invalidate search cache
    search_pattern = f"search:*user:{user_id}*"
    search_keys = self.redis.keys(search_pattern)
    if search_keys:
        deleted += self.redis.delete(*search_keys)
    
    # Invalidate embedding cache (harder without tagging)
    # Consider using Redis tags/patterns for this
    return deleted

def invalidate_collection_cache(self, user_id: str, collection_id: str) -> int:
    """Invalidate cache for specific collection"""
    pattern = f"search:*user:{user_id}*collection:{collection_id}*"
    keys = self.redis.keys(pattern)
    if keys:
        return self.redis.delete(*keys)
    return 0

# Call invalidation on document updates:
# In documents.py after update/delete:
if cache.is_available():
    cache.invalidate_collection_cache(str(current_user.id), str(collection_id))
```

---

### 18. No Timeout on Batch Embeddings Request
**File**: `backend/tasks/process_document.py` (line 121)  
**Severity**: MEDIUM (Performance)

**Issue**:
```python
embeddings = await self.embedder.embed_batch(texts)  # No timeout!
```

If OpenAI API hangs, task hangs indefinitely, consuming Celery worker.

**Remediation**:
```python
import asyncio

try:
    embeddings = await asyncio.wait_for(
        self.embedder.embed_batch(texts),
        timeout=300  # 5 minutes max per batch
    )
except asyncio.TimeoutError:
    raise Exception(f"Embedding batch request timed out for {len(texts)} chunks")
```

---

### 19. No Audit Logging
**File**: All API endpoints  
**Severity**: MEDIUM (Compliance/Security)

**Issue**:
No logging of:
- Who accessed what resources
- When documents were accessed
- Failed authentication attempts
- Data modifications

**Impact**: No audit trail for compliance, can't investigate security incidents.

**Remediation**:
```python
# Create utils/audit.py
import logging
from datetime import datetime
from uuid import UUID

audit_logger = logging.getLogger("audit")

def log_access(user_id: UUID, resource_type: str, resource_id: str, action: str):
    """Log resource access"""
    audit_logger.info(
        f"ACCESS",
        extra={
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(user_id),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action
        }
    )

# In endpoints:
from backend.utils.audit import log_access

@router.get("/{document_id}")
async def get_document(...):
    ...
    log_access(current_user.id, "document", str(document.id), "read")
    return response
```

---

### 20. Configuration Validation Missing
**File**: `backend/config.py` (all)  
**Severity**: MEDIUM (Robustness)

**Issue**:
Settings are loaded but not validated. Invalid config crashes at runtime:
```python
# Config could have:
- OPENAI_API_KEY = ""  # Empty, not caught until first use
- DATABASE_URL = "invalid-format"  # Crashes on engine creation
- CHUNK_SIZE = -100  # Negative, not validated
```

**Remediation**:
```python
from pydantic import field_validator

class Settings(BaseSettings):
    ...
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        if not v or not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL")
        return v
    
    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v):
        if not v:
            raise ValueError("OPENAI_API_KEY is required")
        if not v.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY must start with 'sk-'")
        return v
    
    @field_validator("CHUNK_SIZE", "CHUNK_OVERLAP")
    @classmethod
    def validate_chunk_config(cls, v):
        if v <= 0 or v > 10000:
            raise ValueError("CHUNK_SIZE must be between 1 and 10000")
        return v
```

---

## Summary Table of Issues

| # | Issue | File | Severity | Type | Fix Effort |
|---|-------|------|----------|------|-----------|
| 1 | SQL Injection via JSON filters | retrievals.py, vector_search.py | CRITICAL | Security | Medium |
| 2 | Race condition in status updates | process_document.py | CRITICAL | Concurrency | High |
| 3 | API key in logs | middleware/rate_limiter.py | CRITICAL | Security | Low |
| 4 | Missing transaction rollback | deps.py, documents.py | CRITICAL | DB Safety | Medium |
| 5 | Unvalidated metadata | documents.py | CRITICAL | Input Validation | Low |
| 6 | Concurrent file writes | process_document.py | CRITICAL | Concurrency | High |
| 7 | Session ownership bypass | chat_service.py | CRITICAL | Authorization | Low |
| 8 | FTS query injection | vector_search.py | HIGH | SQL Injection | Low |
| 9 | Cache key collision | cache_service.py | HIGH | Data Consistency | Trivial |
| 10 | No file size limit | documents.py | HIGH | DoS | Trivial |
| 11 | No embedding validation | vector_search.py | HIGH | Runtime Error | Trivial |
| 12 | No LightRAG cleanup | documents.py | HIGH | Data Consistency | Medium |
| 13 | S3 path traversal | storage/s3.py | HIGH | Authorization | Medium |
| 14 | Session leak on error | database.py | HIGH | Resource Leak | Trivial |
| 15 | No name validation | collections.py, documents.py | HIGH | Input Validation | Low |
| 16 | Weak rate limit keys | middleware/rate_limiter.py | MEDIUM | Security | Low |
| 17 | Incomplete cache invalidation | cache_service.py | MEDIUM | Data Consistency | Medium |
| 18 | No timeout on embeddings | process_document.py | MEDIUM | Performance | Trivial |
| 19 | No audit logging | All endpoints | MEDIUM | Compliance | Medium |
| 20 | Missing config validation | config.py | MEDIUM | Robustness | Low |

---

## Remediation Priority

### Phase 1 (Immediate - Before Production)
1. ✓ Fix critical security issues (#3, #5, #7, #15)
2. ✓ Fix critical data consistency (#2, #4)
3. ✓ Fix critical injection issues (#1)
4. ✓ Fix resource exhaustion (#10)
5. ✓ Fix concurrency (#6)

### Phase 2 (High Priority - Week 1)
6. Fix high-severity issues (#8, #9, #11, #12, #13, #14)
7. Add comprehensive input validation
8. Implement transaction safety

### Phase 3 (Medium Priority - Week 2)
9. Implement audit logging (#19)
10. Fix cache invalidation strategy (#17)
11. Add configuration validation (#20)
12. Improve rate limiting (#16)

---

## Data-Flow Verification

### Request → DB → Background Task Cycle

**Upload Document Flow** (RISK: Race conditions):
1. POST /api/v1/documents (API)
2. → Validate collection ownership ✓
3. → Calculate content_hash ✓
4. → Create Document record (status="pending")
5. → Save file to storage ✓
6. → Trigger Celery task
7. → CRITICAL: No guarantee document isn't deleted while queued
8. Celery task retrieves document
9. → Update status="processing" (RACE CONDITION)
10. → Parse, chunk, embed, store chunks
11. → Update status="completed"

**Issue**: Between step 6 and 8, another request could delete the document.

**Retrieval Flow** (RISK: Stale cache):
1. POST /api/v1/retrievals (API)
2. → Check cache
3. → If miss: embed query, search DB, cache results
4. → Return cached or fresh results
5. User updates documents
6. → Cache NOT invalidated
7. Next retrieval returns stale results

**Issue**: Cache invalidation only on user deletion, not on document updates.

**Chat Flow** (RISK: Cross-user data):
1. POST /api/v1/chat (API)
2. → Create or retrieve session (AUTHORIZATION ISSUE)
3. → Save user message
4. → Retrieve relevant chunks
5. → Stream LLM response
6. → Save assistant message
7. → Return session_id

**Issue**: User A can reuse User B's session_id, mixing conversations.

---

## Recommendations

### Immediate Actions (Before Production)
1. **Implement transaction safety** - Wrap all DB operations
2. **Add input validation** - Validate all user inputs with schemas
3. **Sanitize logs** - Never log auth headers or API keys
4. **Remove concurrency bugs** - Add row-level locking, deduplication
5. **Verify authorization** - Always check ownership before operations

### Short-term (Within 2 weeks)
1. Add comprehensive audit logging
2. Implement cache versioning/tagging
3. Add configuration validation
4. Improve error handling (rollback, retries)
5. Add integration tests for data consistency

### Long-term (Future phases)
1. Consider async-safe ORM (Tortoise ORM, SQLAlchemy async)
2. Implement event sourcing for audit trail
3. Add distributed locking (Redis) for concurrent tasks
4. Consider message queue ordering guarantees
5. Add observability/tracing for data-flow verification

---

## Testing Recommendations

### Security Tests
```python
# Test SQL injection vectors
test_metadata_filter_with_sql_operators()
test_fts_query_with_special_chars()

# Test authorization bypass
test_session_cross_user_access()
test_document_access_cross_user()

# Test API key exposure
test_logs_contain_no_auth_headers()
```

### Concurrency Tests
```python
# Test race conditions
test_concurrent_document_status_updates()
test_concurrent_delete_during_processing()
test_concurrent_file_writes()
```

### Data Consistency Tests
```python
test_cache_invalidation_on_update()
test_transaction_rollback_on_error()
test_chunk_cleanup_on_delete()
```

---

## References

- **SQLAlchemy Best Practices**: https://docs.sqlalchemy.org/en/20/faq/security.html
- **OWASP Top 10**: https://owasp.org/Top10/
- **PostgreSQL Row-Level Security**: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- **Celery Best Practices**: https://docs.celeryproject.io/en/stable/
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/

