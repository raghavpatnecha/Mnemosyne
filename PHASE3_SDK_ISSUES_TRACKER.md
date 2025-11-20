# Phase 3 SDK Issues Tracker

**Last Updated:** 2024  
**Status:** 🔴 4 Critical Issues | 🟡 0 Medium Issues | 🟢 0 Low Issues

---

## 🔴 Critical Issues

### Issue #1: Missing Endpoint - `GET /documents/{id}/url`

**Severity:** Critical  
**Status:** 🔴 Open  
**Priority:** P0  
**Estimated Effort:** 3 hours

**Description:**
Backend API provides `GET /documents/{id}/url` endpoint for retrieving pre-signed URLs to access/download documents, but neither SDK implements this.

**Backend Implementation:**
- File: `backend/api/documents.py:486-542`
- Returns: `{url, expires_in, filename, content_type}`
- Use case: Document download, S3 pre-signed URLs

**Affected SDKs:**
- ❌ Python SDK (`sdk/mnemosyne/resources/documents.py`)
- ❌ TypeScript SDK (`sdk-ts/src/resources/documents.ts`)

**Required Implementation:**

**Python SDK:**
```python
# File: sdk/mnemosyne/resources/documents.py

def get_url(
    self,
    document_id: UUID,
    expires_in: int = 3600
) -> Dict[str, Any]:
    """
    Get access URL for document file.
    
    Args:
        document_id: Document UUID
        expires_in: URL expiration time in seconds (default: 3600 = 1 hour)
    
    Returns:
        dict: {url, expires_in, filename, content_type}
    """
    params = {"expires_in": expires_in}
    response = self._client.request("GET", f"/documents/{document_id}/url", params=params)
    return response.json()

# Async version in AsyncDocumentsResource
async def get_url(self, document_id: UUID, expires_in: int = 3600) -> Dict[str, Any]:
    """Get access URL for document file (async)"""
    params = {"expires_in": expires_in}
    response = await self._client.request("GET", f"/documents/{document_id}/url", params=params)
    return response.json()
```

**TypeScript SDK:**
```typescript
// File: sdk-ts/src/types/documents.ts

export interface DocumentUrlResponse {
  url: string;
  expires_in: number;
  filename: string;
  content_type: string;
}

// File: sdk-ts/src/resources/documents.ts

async getUrl(
  documentId: string,
  expiresIn: number = 3600
): Promise<DocumentUrlResponse> {
  return this.client.request<DocumentUrlResponse>(
    'GET',
    `/documents/${documentId}/url`,
    { params: { expires_in: expiresIn } }
  );
}
```

**Testing:**
```python
# Python test
url_info = client.documents.get_url(doc_id, expires_in=7200)
assert "url" in url_info
assert url_info["expires_in"] == 7200
```

```typescript
// TypeScript test
const urlInfo = await client.documents.getUrl(docId, 7200);
expect(urlInfo.url).toBeDefined();
expect(urlInfo.expires_in).toBe(7200);
```

**Acceptance Criteria:**
- [ ] Python SDK implements `get_url()` and `async get_url()`
- [ ] TypeScript SDK implements `getUrl()`
- [ ] Unit tests added for both SDKs
- [ ] Integration tests verify actual URL generation
- [ ] Documentation updated in READMEs
- [ ] Example usage added to SDK guides

---

### Issue #2: Parameter Mismatch - `documents.list()` collection_id

**Severity:** Critical  
**Status:** 🔴 Open  
**Priority:** P0  
**Estimated Effort:** 1.5 hours

**Description:**
Backend API requires `collection_id` as a mandatory parameter for `GET /documents`, but SDKs treat it as optional. This causes misleading SDK signatures and potential runtime errors.

**Backend Implementation:**
```python
# backend/api/documents.py:197
async def list_documents(
    collection_id: UUID,  # ← REQUIRED, no Optional
    limit: int = 20,
    ...
):
```

**Current SDK Implementations:**

**Python SDK (WRONG):**
```python
# sdk/mnemosyne/resources/documents.py:81
def list(
    self,
    collection_id: Optional[UUID] = None,  # ❌ Should be required
    ...
) -> DocumentListResponse:
```

**TypeScript SDK (WRONG):**
```typescript
// sdk-ts/src/resources/documents.ts:96
async list(params?: {
  collection_id?: string;  // ❌ Should be required
  ...
}): Promise<DocumentListResponse>
```

**Impact:**
- Users may omit `collection_id` thinking it's optional
- Backend returns 422 validation error
- Examples work by accident (always pass collection_id)

**Required Fix:**

**Python SDK:**
```python
# File: sdk/mnemosyne/resources/documents.py

def list(
    self,
    collection_id: UUID,  # ✅ Required, no Optional
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[str] = None,
) -> DocumentListResponse:
    """
    List documents in a collection.
    
    Args:
        collection_id: Collection UUID (REQUIRED)
        ...
    """
    params = {
        "collection_id": str(collection_id),  # ✅ Always included
        "limit": limit,
        "offset": offset
    }
    if status_filter:
        params["status"] = status_filter
    
    response = self._client.request("GET", "/documents", params=params)
    return DocumentListResponse(**response.json())

# Async version
async def list(
    self,
    collection_id: UUID,  # ✅ Required
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[str] = None,
) -> DocumentListResponse:
    """List documents in a collection (async)"""
    params = {
        "collection_id": str(collection_id),
        "limit": limit,
        "offset": offset
    }
    if status_filter:
        params["status"] = status_filter
    
    response = await self._client.request("GET", "/documents", params=params)
    return DocumentListResponse(**response.json())
```

**TypeScript SDK:**
```typescript
// File: sdk-ts/src/resources/documents.ts

async list(params: {  // ✅ No ? on params
  collection_id: string;  // ✅ No ? on collection_id
  limit?: number;
  offset?: number;
  status_filter?: ProcessingStatus;
}): Promise<DocumentListResponse> {
  const queryParams: Record<string, string | number> = {
    collection_id: params.collection_id,  // ✅ Always included
    limit: params.limit || 20,
    offset: params.offset || 0,
  };

  if (params.status_filter) {
    queryParams.status = params.status_filter;
  }

  return this.client.request<DocumentListResponse>('GET', '/documents', {
    params: queryParams,
  });
}
```

**Update Examples:**

**Python Example:**
```python
# sdk/examples/ingestion_workflow.py:105
docs_list = client.documents.list(
    collection_id=collection.id,  # Now clearly required
    status_filter="completed",
)
```

**TypeScript Example:**
```typescript
// sdk-ts/examples/ingestion-workflow.ts:124
const docs = await client.documents.list({
  collection_id: collection.id,  // Now clearly required
  status_filter: 'completed',
});
```

**Breaking Change Notice:**
```markdown
## Breaking Changes in v1.3.0

### documents.list() now requires collection_id

**Before:**
```python
docs = client.documents.list()  # collection_id optional
```

**After:**
```python
docs = client.documents.list(collection_id=collection.id)  # Required
```

**Reason:** Backend API always required collection_id; SDK signature was misleading.
```

**Acceptance Criteria:**
- [ ] Python SDK: `collection_id` parameter is required (no Optional)
- [ ] TypeScript SDK: `collection_id` parameter is required (no ?)
- [ ] All examples updated to show required parameter
- [ ] Tests verify error when collection_id is omitted
- [ ] CHANGELOG includes breaking change notice
- [ ] Migration guide added to documentation

---

### Issue #3: Type Mismatch - TypeScript `RetrievalResponse.processing_time_ms`

**Severity:** Medium  
**Status:** 🔴 Open  
**Priority:** P1  
**Estimated Effort:** 15 minutes

**Description:**
TypeScript SDK type definition includes `processing_time_ms` field that backend never returns, causing type inconsistency.

**Backend Schema:**
```python
# backend/schemas/retrieval.py:54-67
class RetrievalResponse(BaseModel):
    results: List[ChunkResult]
    query: str
    mode: str
    total_results: int
    graph_enhanced: bool
    graph_context: Optional[str]
    # ❌ No processing_time_ms field
```

**TypeScript Type (WRONG):**
```typescript
// sdk-ts/src/types/retrievals.ts:50-58
export interface RetrievalResponse {
  query: string;
  mode: string;
  results: ChunkResult[];
  total_results: number;
  processing_time_ms: number;  // ❌ Field never returned by backend
  graph_enhanced: boolean;
  graph_context?: string;
}
```

**Python Type (CORRECT):**
```python
# sdk/mnemosyne/types/retrievals.py:49-63
class RetrievalResponse(BaseModel):
    query: str
    mode: str
    results: list[ChunkResult]
    total_results: int
    graph_enhanced: bool
    graph_context: Optional[str]
    # ✅ Correct - no processing_time_ms
```

**Required Fix:**
```typescript
// File: sdk-ts/src/types/retrievals.ts:50-58

export interface RetrievalResponse {
  query: string;
  mode: string;
  results: ChunkResult[];
  total_results: number;
  // ❌ REMOVE THIS LINE: processing_time_ms: number;
  graph_enhanced: boolean;
  graph_context?: string;
}
```

**Acceptance Criteria:**
- [ ] Remove `processing_time_ms` from TypeScript type definition
- [ ] Verify no code depends on this field
- [ ] Update any examples that reference this field
- [ ] Add test to verify response type matches backend

---

### Issue #4: Streaming Implementation - Raw JSON Strings

**Severity:** Medium  
**Status:** 🔴 Open  
**Priority:** P1  
**Estimated Effort:** 6 hours

**Description:**
Both SDKs return raw JSON strings from streaming chat instead of parsed objects or extracted deltas. Users must manually parse JSON on every iteration.

**Backend SSE Format:**
```
data: {"type": "delta", "delta": "Machine"}
data: {"type": "delta", "delta": " learning"}
data: {"type": "sources", "sources": [...]}
data: {"type": "done", "done": true, "session_id": "..."}
```

**Current SDK Behavior:**
```python
# Python
for chunk in client.chat.chat(message="test"):
    print(chunk)  # Prints: '{"type": "delta", "delta": "Machine"}'
    # User must: event = json.loads(chunk); print(event['delta'])
```

```typescript
// TypeScript
for await (const chunk of client.chat.chat({message: "test"})) {
    console.log(chunk);  // Logs: '{"type": "delta", "delta": "Machine"}'
    // User must: const event = JSON.parse(chunk); console.log(event.delta);
}
```

**Problems:**
1. Poor UX - manual JSON parsing required
2. No distinction between event types (delta, sources, done)
3. No easy way to access sources or session_id
4. Examples show incorrect usage (print raw chunks)

**Proposed Solution: Two-Phase Approach**

**Phase 1: Fix existing method (minimal change, maintain compatibility)**

```python
# File: sdk/mnemosyne/resources/chat.py

def chat(
    self,
    message: str,
    session_id: Optional[UUID] = None,
    collection_id: Optional[UUID] = None,
    top_k: int = 5,
    stream: bool = True,
) -> Iterator[str]:
    """Stream chat response (yields deltas only)"""
    if stream:
        headers = self._client._get_headers()
        headers["Accept"] = "text/event-stream"
        
        response = self._client._http_client.post(...)
        self._client._handle_error(response)
        
        for chunk in parse_sse_stream(response):
            # ✅ Parse JSON and extract delta
            try:
                event = json.loads(chunk)
                if event.get('type') == 'delta':
                    yield event['delta']
            except json.JSONDecodeError:
                # Fallback for backward compatibility
                yield chunk
```

**Phase 2: Add new typed streaming method**

```python
# File: sdk/mnemosyne/types/chat.py

from typing import Literal, Optional, List
from pydantic import BaseModel

class StreamEvent(BaseModel):
    """Typed streaming event"""
    type: Literal["delta", "sources", "done", "error"]
    
    # Delta event
    delta: Optional[str] = None
    
    # Sources event
    sources: Optional[List[Source]] = None
    
    # Done event
    done: Optional[bool] = None
    session_id: Optional[str] = None
    
    # Error event
    error: Optional[str] = None

# File: sdk/mnemosyne/resources/chat.py

def chat_stream(
    self,
    message: str,
    session_id: Optional[UUID] = None,
    collection_id: Optional[UUID] = None,
    top_k: int = 5,
) -> Iterator[StreamEvent]:
    """
    Stream chat response with typed events.
    
    Yields:
        StreamEvent: Typed event (delta, sources, done, error)
    
    Example:
        >>> for event in client.chat.chat_stream(message="test"):
        ...     if event.type == "delta":
        ...         print(event.delta, end="", flush=True)
        ...     elif event.type == "sources":
        ...         print(f"\\nSources: {len(event.sources)}")
        ...     elif event.type == "done":
        ...         print(f"\\nSession: {event.session_id}")
    """
    headers = self._client._get_headers()
    headers["Accept"] = "text/event-stream"
    
    response = self._client._http_client.post(...)
    self._client._handle_error(response)
    
    for chunk in parse_sse_stream(response):
        try:
            event_data = json.loads(chunk)
            yield StreamEvent(**event_data)
        except (json.JSONDecodeError, ValueError) as e:
            # Yield error event
            yield StreamEvent(type="error", error=str(e))
```

**TypeScript Implementation:**
```typescript
// File: sdk-ts/src/types/chat.ts

export interface StreamEvent {
  type: 'delta' | 'sources' | 'done' | 'error';
  delta?: string;
  sources?: Source[];
  done?: boolean;
  session_id?: string;
  error?: string;
}

// File: sdk-ts/src/resources/chat.ts

// Phase 1: Fix existing method
async *chat(params: {...}): AsyncGenerator<string, void, unknown> {
  if (params.stream !== false) {
    const response = await this.client.requestStream(...);
    
    for await (const chunk of parseSSEStream(response)) {
      try {
        const event = JSON.parse(chunk);
        if (event.type === 'delta') {
          yield event.delta;  // ✅ Extract delta
        }
      } catch {
        yield chunk;  // Fallback
      }
    }
  } else {
    ...
  }
}

// Phase 2: New typed method
async *chatStream(params: {
  message: string;
  session_id?: string;
  collection_id?: string;
  top_k?: number;
}): AsyncGenerator<StreamEvent, void, unknown> {
  const request: ChatRequest = {...};
  const response = await this.client.requestStream('POST', '/chat', {json: request});
  
  for await (const chunk of parseSSEStream(response)) {
    try {
      const event = JSON.parse(chunk) as StreamEvent;
      yield event;
    } catch (err) {
      yield {type: 'error', error: String(err)};
    }
  }
}
```

**Update Examples:**

```python
# Phase 1: Simple usage (backward compatible)
for chunk in client.chat.chat(message="test"):
    print(chunk, end="", flush=True)  # ✅ Now prints just "Machine learning"

# Phase 2: Advanced usage (with sources)
for event in client.chat.chat_stream(message="test"):
    if event.type == "delta":
        print(event.delta, end="", flush=True)
    elif event.type == "sources":
        print(f"\n\n📚 Sources ({len(event.sources)}):")
        for src in event.sources:
            print(f"  - {src.document['filename']} (score: {src.score:.2f})")
    elif event.type == "done":
        print(f"\n\n✓ Session: {event.session_id}")
```

**Deprecation Plan:**
1. Release 1.3.0: Add `chat_stream()` / `chatStream()` with typed events
2. Release 1.3.0: Fix `chat()` to parse JSON and extract deltas
3. Release 1.4.0: Add deprecation warning to old `chat()` method (if no usage)
4. Release 2.0.0: Consider removing old method (breaking change)

**Acceptance Criteria:**
- [ ] Phase 1: `chat()` method parses JSON and yields deltas only
- [ ] Phase 2: New `chat_stream()` / `chatStream()` method added
- [ ] Phase 2: StreamEvent types defined in both SDKs
- [ ] Examples updated to show both simple and advanced usage
- [ ] Documentation explains event types
- [ ] Tests cover all event types (delta, sources, done, error)
- [ ] Backward compatibility maintained

---

## Testing Checklist

### Issue #1: documents.get_url()
- [ ] Unit test: method exists and makes correct API call
- [ ] Unit test: parameters passed correctly (expires_in)
- [ ] Integration test: returns valid URL
- [ ] Integration test: URL actually works (can access document)
- [ ] Test: S3 pre-signed URLs (if storage backend is S3)
- [ ] Test: local file paths (if storage backend is local)

### Issue #2: documents.list() collection_id
- [ ] Unit test: collection_id is required parameter
- [ ] Unit test: TypeError/validation error when omitted
- [ ] Integration test: list with valid collection_id succeeds
- [ ] Integration test: list without collection_id fails
- [ ] Test: pagination with collection_id
- [ ] Test: status_filter with collection_id

### Issue #3: RetrievalResponse.processing_time_ms
- [ ] Unit test: TypeScript type matches backend response
- [ ] Integration test: parse response without processing_time_ms
- [ ] Test: ensure no code depends on removed field

### Issue #4: Streaming
- [ ] Unit test: parse_sse_stream extracts JSON correctly
- [ ] Unit test: StreamEvent type validates correctly
- [ ] Integration test: delta events yield correct text
- [ ] Integration test: sources event yields source list
- [ ] Integration test: done event yields session_id
- [ ] Integration test: error events handled gracefully
- [ ] Test: backward compatibility (old chat() method still works)

---

## Release Plan

### Version 1.3.0 (Breaking Changes)

**Release Date:** TBD  
**Type:** Minor (with breaking changes)

**Changes:**
1. ✅ Add `documents.get_url()` / `documents.getUrl()` (new feature)
2. 🔴 **BREAKING**: Make `documents.list()` collection_id required
3. ✅ Fix TypeScript `RetrievalResponse.processing_time_ms` type
4. ✅ Fix `chat()` to parse JSON and extract deltas
5. ✅ Add `chat_stream()` / `chatStream()` with typed events (new feature)

**Migration Guide:**
- Update all `documents.list()` calls to include collection_id
- No other breaking changes affect API usage

**Changelog:**
```markdown
## [1.3.0] - 2024-XX-XX

### Added
- New `documents.get_url()` method for retrieving document access URLs (#1)
- New `chat_stream()` method with typed events (delta, sources, done) (#4)
- StreamEvent type for structured streaming responses (#4)

### Changed
- **BREAKING**: `documents.list()` now requires `collection_id` parameter (#2)
- Improved `chat()` streaming to parse JSON and extract deltas automatically (#4)

### Fixed
- Removed non-existent `processing_time_ms` from TypeScript `RetrievalResponse` type (#3)

### Migration
- Update `documents.list()` calls to always include `collection_id`:
  ```python
  # Before
  docs = client.documents.list()
  
  # After
  docs = client.documents.list(collection_id=collection.id)
  ```
```

---

## Status Dashboard

| Issue # | Title | Severity | Priority | Status | Assignee | ETA |
|---------|-------|----------|----------|--------|----------|-----|
| #1 | Missing documents.get_url() | Critical | P0 | 🔴 Open | - | - |
| #2 | documents.list() collection_id | Critical | P0 | 🔴 Open | - | - |
| #3 | TypeScript processing_time_ms | Medium | P1 | 🔴 Open | - | - |
| #4 | Streaming JSON parsing | Medium | P1 | 🔴 Open | - | - |

**Total Issues:** 4  
**Open:** 4 🔴  
**In Progress:** 0 🟡  
**Resolved:** 0 ✅

**Next Actions:**
1. Create GitHub issues for each item
2. Assign to team members
3. Set target release date for v1.3.0
4. Begin implementation in order of priority

---

**Report End**
