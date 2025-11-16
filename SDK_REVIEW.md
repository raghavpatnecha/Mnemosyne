# SDK Implementation Plan - Gap Analysis

**Review Date:** November 17, 2025
**Reviewer:** Claude
**Document:** SDK_IMPLEMENTATION_PLAN.md

---

## Executive Summary

The SDK implementation plan is **~85% complete** with excellent coverage of architecture, examples, and workflow. However, there are some **missing implementation details** and **incomplete code sections** that need to be addressed before implementation begins.

**Status:** ✅ Ready for review → ⚠️ Needs minor additions

---

## Critical Gaps (Must Fix)

### 1. ❌ Section Numbering Error
**Issue:** Duplicate "## 3." sections
- Line 104: "## 3. Current API Analysis"
- Line 215: "## 3. SDK Architecture"

**Fix:** Renumber sections 3-17 correctly

### 2. ❌ Incomplete Documents Resource
**Location:** Section 5 (Resource Implementations)

**Missing methods:**
```python
class DocumentsResource:
    # ✓ create() - SHOWN
    # ✓ list() - SHOWN
    # ✓ get_status() - SHOWN
    # ✗ get() - MISSING
    # ✗ update() - MISSING
    # ✗ delete() - MISSING
```

**Current:** Says "# ... (other CRUD methods)" without implementation
**Needed:** Full implementation of get, update, delete methods

### 3. ❌ Incomplete Type Definitions
**Location:** Section 6 (Type System)

**Currently shown:**
- ✓ Collections types (complete)

**Missing:**
- ✗ Documents types (DocumentResponse, DocumentListResponse, DocumentStatusResponse)
- ✗ Retrievals types (RetrievalRequest, RetrievalResponse, ChunkResult)
- ✗ Chat types (ChatRequest, ChatSessionResponse, ChatMessageResponse)

### 4. ❌ Missing Package Structure Files

**Not shown:**
- `mnemosyne/__init__.py` - What gets exported?
- `mnemosyne/resources/__init__.py` - Export all resources?
- `mnemosyne/types/__init__.py` - Export all types?
- `mnemosyne/version.py` - Version management

**Example needed:**
```python
# mnemosyne/__init__.py
from .client import Client
from .async_client import AsyncClient
from .exceptions import MnemosyneError, AuthenticationError

__version__ = "0.1.0"
__all__ = ["Client", "AsyncClient", "MnemosyneError", "AuthenticationError"]
```

### 5. ❌ Incomplete pyproject.toml
**Location:** Section 11 (Dependencies)

**Current:** Lists dependencies but no complete config
**Needed:** Full Poetry configuration with:
- Package metadata (name, version, description, authors)
- Python version constraint
- All dependencies with versions
- Dev dependencies
- Build system
- Tool configurations (black, mypy, pytest)

---

## Important Gaps (Should Fix)

### 6. ⚠️ Missing Retry Logic Implementation
**Location:** Section 4 (Core Client Design)

**Mentioned but not implemented:**
- BaseClient has `max_retries` parameter
- No actual retry logic shown
- No exponential backoff implementation
- No retry for specific status codes (429, 5xx)

**Needed:**
```python
def _request_with_retry(self, method, path, **kwargs):
    """Make request with exponential backoff retry"""
    for attempt in range(self.max_retries):
        try:
            response = self._http_client.request(method, path, **kwargs)
            if response.status_code < 500:
                return response
            # Retry on 5xx errors
        except httpx.RequestError:
            if attempt == self.max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
    return response
```

### 7. ⚠️ Missing Auth Resource
**Issue:** No user registration in SDK

The API has `POST /auth/register` but SDK doesn't expose it.

**Decision needed:**
- Should SDK include `client.auth.register()`?
- Or is this a one-time setup users do manually?
- Document the decision either way

### 8. ⚠️ Async DocumentsResource Not Shown
**Location:** Section 5

**Current:** DocumentsResource shown, but AsyncDocumentsResource not shown
**Issue:** Async file upload is tricky and needs special handling

**Needed:**
```python
class AsyncDocumentsResource:
    async def create(self, collection_id, file, metadata=None):
        # Handle async file reads
        # Use httpx async client
        pass
```

### 9. ⚠️ Missing Chat Resource Implementation
**Location:** Section 5

**Current:** Only signatures shown:
```python
class ChatResource:
    def list_sessions(self, limit=20, offset=0):
        """List chat sessions"""
        # ... implementation missing
```

**Needed:** Full implementation of:
- `list_sessions()`
- `get_session_messages(session_id)`
- `delete_session(session_id)`
- Async versions for AsyncChatResource

### 10. ⚠️ SSE Streaming Error Handling
**Location:** Section 7 (Streaming Support)

**Current:** Basic parse_sse_stream() shown
**Missing:**
- Error event handling
- Connection timeouts
- Reconnection logic
- Stream interruption handling

---

## Nice-to-Have Gaps (Optional)

### 11. ℹ️ No Configuration Management
**Issue:** No environment variable support shown

**Suggested addition:**
```python
# mnemosyne/config.py
import os

class Config:
    @staticmethod
    def get_api_key():
        return os.getenv("MNEMOSYNE_API_KEY")

    @staticmethod
    def get_base_url():
        return os.getenv("MNEMOSYNE_BASE_URL", "http://localhost:8000")

# Usage
client = Client(api_key=Config.get_api_key())
```

### 12. ℹ️ No Pagination Helper
**Issue:** Users must manually paginate results

**Future enhancement mentioned in v1.1**, but could add example:
```python
def list_all_collections(client):
    """Helper to fetch all collections across pages"""
    offset = 0
    while True:
        response = client.collections.list(limit=100, offset=offset)
        yield from response.data
        if not response.pagination["has_more"]:
            break
        offset += 100
```

### 13. ℹ️ No Progress Callbacks for Upload
**Issue:** Large file uploads have no progress indication

**Future enhancement mentioned in v1.1**, document this explicitly.

### 14. ℹ️ Missing README.md Content
**Location:** Section 13 (Documentation Plan)

**Current:** Says "Installation instructions, Quick start guide..."
**Needed:** Actual README template with:
- Installation commands
- Quick start code
- Links to examples
- API reference
- Contributing guide

### 15. ℹ️ No License Decision
**Location:** Project structure shows "LICENSE - MIT License"

**Issue:** No actual license text shown
**Needed:** Confirm MIT license and add LICENSE file content

---

## Code Quality Issues

### 16. 🔧 Missing Import Statements
**Issue:** Code examples missing imports

**Example - Documents Resource:**
```python
# Current (line 488):
from pathlib import Path
from typing import Optional, Dict, Union, BinaryIO
from uuid import UUID
from ..types.documents import DocumentResponse, DocumentListResponse, DocumentStatusResponse

# Missing:
import json  # Used in line 521
```

### 17. 🔧 Type Hint Inconsistencies
**Issue:** Some methods use `Dict` others use `dict`

**Recommendation:** Use lowercase `dict`, `list` for Python 3.9+ (Pydantic v2 compatible)

### 18. 🔧 Error Handling in BaseClient
**Location:** Section 4, `_handle_error()` method

**Current:** Basic error mapping
**Missing:**
- Parse error response body
- Extract error message from API
- Handle different error formats
- Log errors properly

---

## Documentation Gaps

### 19. 📝 No Docstring Examples
**Issue:** Docstrings mentioned but not shown

**Needed:** Example docstring with:
- Description
- Args with types
- Returns with type
- Raises
- Example usage

```python
def create(
    self,
    name: str,
    description: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> CollectionResponse:
    """
    Create a new collection.

    Args:
        name: Collection name (1-255 characters)
        description: Optional description
        metadata: Optional metadata dictionary

    Returns:
        CollectionResponse: Created collection with ID and timestamps

    Raises:
        AuthenticationError: Invalid API key
        ValidationError: Invalid name or metadata
        APIError: Server error

    Example:
        >>> client = Client(api_key="mn_...")
        >>> collection = client.collections.create(
        ...     name="Research Papers",
        ...     metadata={"domain": "AI"}
        ... )
        >>> print(collection.id)
        UUID('...')
    """
```

### 20. 📝 Missing Error Handling Examples
**Issue:** No examples showing how to catch and handle errors

**Needed:**
```python
from mnemosyne import Client, AuthenticationError, RateLimitError

try:
    client = Client(api_key="invalid_key")
    collection = client.collections.create(name="Test")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limit exceeded, wait before retry")
```

---

## Testing Gaps

### 21. 🧪 No Concrete Test Examples
**Location:** Section 12 (Testing Strategy)

**Current:** Says "Test each resource method" but no examples
**Needed:** Actual test code:

```python
# tests/unit/test_collections.py
import pytest
from pytest_httpx import HTTPXMock
from mnemosyne import Client

def test_create_collection(httpx_mock: HTTPXMock):
    """Test collection creation"""
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:8000/collections",
        json={
            "id": "uuid-here",
            "name": "Test",
            "user_id": "user-uuid",
            "document_count": 0,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": None
        }
    )

    client = Client(api_key="test_key")
    collection = client.collections.create(name="Test")

    assert collection.name == "Test"
    assert collection.document_count == 0
```

### 22. 🧪 No Integration Test Strategy
**Issue:** Integration tests mentioned but no approach defined

**Needed:**
- How to start local Mnemosyne instance for testing
- Test data setup (seed documents)
- Cleanup strategy
- CI/CD integration

---

## Architecture Questions

### 23. ❓ YouTube URL Handling Unclear
**Issue:** video_ingestion.py example shows YouTube URL in `file` parameter

**Question:** How does SDK distinguish between:
- File path: `"papers/doc.pdf"`
- YouTube URL: `"https://youtube.com/watch?v=..."`

**Needed:** Document the detection logic:
```python
def create(self, collection_id, file, metadata=None):
    if isinstance(file, str) and file.startswith("http"):
        # YouTube URL - send as form data, not file upload
        data = {"url": file, "collection_id": str(collection_id)}
        response = self._client.request("POST", "/documents", json=data)
    else:
        # File upload - use multipart/form-data
        files = {"file": open(file, "rb")}
        # ...
```

### 24. ❓ Context Manager Usage
**Issue:** Examples show `client.close()` but Client has `__enter__`/`__exit__`

**Inconsistency:**
- Section 4 shows context manager protocol
- Examples use manual `.close()`

**Recommendation:** Be consistent in examples:
```python
# Preferred (context manager)
with Client(api_key="...") as client:
    collection = client.collections.create(name="Test")

# Or
client = Client(api_key="...")
try:
    collection = client.collections.create(name="Test")
finally:
    client.close()
```

### 25. ❓ Version Compatibility
**Issue:** No Python version requirements mentioned clearly

**Needed in pyproject.toml:**
```toml
[tool.poetry.dependencies]
python = "^3.9"  # Minimum version
```

**Reason:** Using `dict`, `list` generics (3.9+), and other modern features

---

## Summary by Priority

### 🔴 Critical (Must Fix Before Implementation)
1. Fix section numbering
2. Complete Documents resource (get, update, delete)
3. Add all type definitions (Documents, Retrievals, Chat)
4. Add package __init__.py files
5. Complete pyproject.toml

### 🟡 Important (Should Fix Soon)
6. Implement retry logic
7. Decide on auth resource inclusion
8. Add AsyncDocumentsResource
9. Complete Chat resource implementation
10. Enhance SSE error handling

### 🟢 Nice-to-Have (Can Defer)
11-15. Configuration, pagination helpers, progress callbacks, README template, license

### 🔧 Quality (Fix During Implementation)
16-18. Imports, type hints, error handling details

### 📝 Documentation (Enhance Over Time)
19-20. Docstring examples, error handling examples

### 🧪 Testing (Part of Implementation)
21-22. Test examples, integration strategy

### ❓ Architecture (Clarify During Review)
23-25. YouTube URL handling, context manager usage, version compatibility

---

## Recommendations

### Immediate Actions (Before Implementation)
1. ✅ Fix section numbering
2. ✅ Complete all resource implementations (Documents get/update/delete, Chat methods)
3. ✅ Add all type definitions
4. ✅ Create __init__.py files
5. ✅ Complete pyproject.toml

### Week 1 Actions (During Core Implementation)
6. ✅ Implement retry logic with exponential backoff
7. ✅ Add AsyncDocumentsResource
8. ✅ Enhance error handling in BaseClient
9. ✅ Add missing imports
10. ✅ Standardize type hints

### Week 2-3 Actions (During Examples/Docs)
11. ✅ Create README template
12. ✅ Add comprehensive docstrings
13. ✅ Add error handling examples
14. ✅ Document YouTube URL detection
15. ✅ Clarify context manager usage

### Week 4 Actions (Before Publishing)
16. ✅ Add LICENSE file
17. ✅ Create test examples
18. ✅ Setup CI/CD
19. ✅ Version compatibility testing
20. ✅ Final review and polish

---

## Conclusion

The SDK implementation plan is **well-structured and comprehensive** with excellent coverage of:
- ✅ Architecture design (dual clients, resource pattern)
- ✅ Full workflow examples (ingestion → retrieval)
- ✅ All major features (5 search modes, streaming, LangChain)
- ✅ Clear timeline and success criteria

**However**, it needs **~15% more detail** in:
- Implementation completeness (Documents, Chat resources)
- Type definitions (all schemas)
- Package structure (__init__ files, pyproject.toml)
- Error handling and retries

**Recommendation:** Address **Critical** and **Important** gaps (items 1-10) before starting implementation. The plan will then be **95% complete** and ready for execution.

**Estimated effort to fix:** 3-4 hours
**Current completeness:** 85%
**Target completeness:** 95%+ (100% is unrealistic for a plan)

---

## Next Steps

1. Review this gap analysis
2. Decide which gaps to address now vs during implementation
3. Update SDK_IMPLEMENTATION_PLAN.md with critical fixes
4. Get stakeholder approval
5. Begin Phase 1 implementation

**Status:** 🟡 Plan ready pending minor revisions
