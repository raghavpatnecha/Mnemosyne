# Multi-Tenancy and User Separation

## Overview

Mnemosyne implements **strict multi-tenancy** with complete user data isolation at every layer of the system. Each user's data—collections, documents, embeddings, and chat history—is completely isolated from all other users.

This document explains how user separation works across the database, API, storage, and LightRAG layers.

---

## Architecture Principles

### 1. User Ownership Model

Every resource in Mnemosyne is owned by a specific user:

```
User (root entity)
├── API Keys (authentication)
├── Collections
│   ├── Documents
│   │   ├── Document Chunks (with embeddings)
│   │   └── Original Files (S3/storage)
│   └── LightRAG Working Directory
└── Chat Sessions
    └── Chat Messages
```

### 2. Isolation Layers

**Four-layer isolation:**

1. **Database Layer**: Foreign key constraints with `user_id`
2. **API Layer**: Automatic filtering by authenticated user
3. **Storage Layer**: User-scoped S3 paths or filesystem directories
4. **Knowledge Graph Layer**: Per-user LightRAG working directories

---

## Database-Level Isolation

### Schema Design

All core tables have a `user_id` foreign key:

```sql
-- Users table (root)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Collections table
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)  -- User can't have duplicate collection names
);

-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    filename VARCHAR(500),
    file_type VARCHAR(50),
    file_size BIGINT,
    storage_path TEXT,
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document chunks table (with embeddings)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- pgvector extension
    chunk_index INTEGER NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chat sessions table
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES collections(id) ON DELETE SET NULL,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chat messages table
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Cascading Deletes

When a user is deleted, **all** their data is automatically removed:

```
DELETE FROM users WHERE id = 'user-123'
  ↓ CASCADE DELETE
  ├── collections (all user collections)
  │   ├── documents (all collection documents)
  │   │   └── document_chunks (all chunks + embeddings)
  ├── chat_sessions (all chat sessions)
  │   └── chat_messages (all messages)
  └── api_keys (all API keys)
```

### Query-Level Filtering

Every database query automatically filters by `user_id`:

```python
# backend/api/collections.py
@router.get("/collections")
async def list_collections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Automatically filtered by user_id
    collections = db.query(Collection).filter(
        Collection.user_id == current_user.id
    ).all()
    return {"collections": collections}

# backend/api/documents.py
@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ownership check
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id  # CRITICAL: ensures user owns this
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document
```

---

## API-Level Isolation

### Authentication Flow

Every API request requires authentication:

```
1. Client sends request with header:
   Authorization: Bearer mn_abc123xyz...

2. FastAPI middleware extracts API key

3. Hash the key and lookup in database:
   SELECT user_id FROM api_keys WHERE key_hash = sha256('mn_abc123xyz...')

4. If valid, inject current_user into request context

5. All subsequent queries filter by current_user.id
```

### Dependency Injection

The `get_current_user` dependency ensures isolation:

```python
# backend/core/security.py
async def get_current_user(
    api_key: str = Depends(get_api_key_header),
    db: Session = Depends(get_db)
) -> User:
    # Hash the provided API key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Look up the API key
    api_key_obj = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()

    if not api_key_obj:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Return the user who owns this API key
    return api_key_obj.user
```

### Automatic Filtering Example

```python
# backend/api/retrievals.py
@router.post("/retrieve")
async def retrieve_chunks(
    request: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # If collection_id provided, verify ownership
    if request.collection_id:
        collection = db.query(Collection).filter(
            Collection.id == request.collection_id,
            Collection.user_id == current_user.id  # Ownership check
        ).first()

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

    # Search only within user's chunks
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.user_id == current_user.id,  # User isolation
        DocumentChunk.collection_id == request.collection_id
    ).all()

    return perform_search(chunks, request.query)
```

---

## Storage-Level Isolation

### S3 Storage Architecture (Production)

**Recommended for production deployments:**

```
s3://mnemosyne-documents/
├── users/
│   ├── {user_id_1}/
│   │   ├── collections/
│   │   │   ├── {collection_id_1}/
│   │   │   │   ├── documents/
│   │   │   │   │   ├── {doc_id_1}/
│   │   │   │   │   │   ├── original.pdf
│   │   │   │   │   │   ├── images/
│   │   │   │   │   │   │   ├── page_1_image_1.png
│   │   │   │   │   │   │   └── page_2_chart_1.jpg
│   │   │   │   │   │   └── metadata.json
│   │   │   │   │   └── {doc_id_2}/
│   │   │   │   │       └── original.docx
│   │   │   │   └── lightrag/
│   │   │   │       ├── entities.json
│   │   │   │       ├── relationships.json
│   │   │   │       └── graph_embeddings.npy
│   │   │   └── {collection_id_2}/
│   │   │       └── ...
│   │   └── chat_exports/
│   │       ├── session_{session_id_1}.json
│   │       └── session_{session_id_2}.json
│   └── {user_id_2}/
│       └── ...
```

### Storage Path Construction

```python
# backend/services/storage.py
class S3StorageBackend:
    def __init__(self, bucket_name: str):
        self.s3_client = boto3.client('s3')
        self.bucket = bucket_name

    def get_document_path(
        self,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        filename: str
    ) -> str:
        """Generate user-scoped S3 path."""
        return (
            f"users/{user_id}/"
            f"collections/{collection_id}/"
            f"documents/{document_id}/"
            f"{filename}"
        )

    def get_lightrag_path(
        self,
        user_id: UUID,
        collection_id: UUID
    ) -> str:
        """Generate per-collection LightRAG working directory."""
        return (
            f"users/{user_id}/"
            f"collections/{collection_id}/"
            f"lightrag/"
        )

    async def upload_document(
        self,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        file_content: bytes,
        filename: str
    ):
        """Upload with user isolation."""
        s3_path = self.get_document_path(
            user_id, collection_id, document_id, filename
        )

        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=s3_path,
            Body=file_content,
            Metadata={
                'user_id': str(user_id),
                'collection_id': str(collection_id),
                'document_id': str(document_id)
            }
        )

        return f"s3://{self.bucket}/{s3_path}"
```

### S3 Bucket Policy

Enforce user isolation at the S3 level:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:role/MnemosyneBackendRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::mnemosyne-documents/users/*",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "users/${aws:userid}/*"
          ]
        }
      }
    }
  ]
}
```

### File System Storage (Development)

**For local development only:**

```
./uploads/
├── users/
│   ├── {user_id_1}/
│   │   ├── collections/
│   │   │   └── {collection_id_1}/
│   │   │       └── documents/
│   │   │           └── {doc_id_1}/
│   │   │               └── file.pdf
│   └── {user_id_2}/
│       └── ...
```

---

## LightRAG Isolation

### Per-Collection Working Directories

Each collection gets its own LightRAG knowledge graph:

```python
# backend/services/lightrag_service.py
class LightRAGService:
    def get_working_dir(
        self,
        user_id: UUID,
        collection_id: UUID
    ) -> str:
        """Get user-scoped LightRAG directory."""
        if settings.USE_S3:
            # S3 backend
            return storage_backend.get_lightrag_path(user_id, collection_id)
        else:
            # File system backend
            base_path = settings.LIGHTRAG_DATA_PATH  # /app/data/lightrag
            return f"{base_path}/users/{user_id}/collections/{collection_id}"

    async def get_or_create_lightrag(
        self,
        user_id: UUID,
        collection_id: UUID
    ) -> LightRAG:
        """Create isolated LightRAG instance per collection."""
        working_dir = self.get_working_dir(user_id, collection_id)

        # Ensure directory exists
        os.makedirs(working_dir, exist_ok=True)

        # Create LightRAG instance with isolated storage
        return LightRAG(
            working_dir=working_dir,
            llm_model_func=litellm_model_complete,
            embedding_func=litellm_embedding
        )
```

### Graph Data Isolation

Each user's LightRAG data is completely separate:

```
/app/data/lightrag/
├── users/
│   ├── user-123/
│   │   ├── collections/
│   │   │   ├── collection-abc/
│   │   │   │   ├── vdb_entities.json       # Entity vectors
│   │   │   │   ├── vdb_relationships.json  # Relationship vectors
│   │   │   │   ├── graph_chunk_entity_relation.graphml
│   │   │   │   └── kv_store_full_docs.json
│   │   │   └── collection-xyz/
│   │   │       └── ... (separate graph)
│   └── user-456/
│       └── collections/
│           └── collection-def/
│               └── ... (isolated from user-123)
```

---

## Security Guarantees

### 1. No Cross-User Data Leakage

**Database queries:**
```python
# ✅ CORRECT: Automatic user filtering
documents = db.query(Document).filter(
    Document.user_id == current_user.id
).all()

# ❌ WRONG: Missing user filter (would expose all users' data)
documents = db.query(Document).all()  # NEVER DO THIS
```

**Vector search:**
```python
# ✅ CORRECT: User-scoped vector search
chunks = db.query(DocumentChunk).filter(
    DocumentChunk.user_id == current_user.id,
    DocumentChunk.collection_id == collection_id
).all()

embeddings = [chunk.embedding for chunk in chunks]
results = cosine_similarity(query_embedding, embeddings)
```

### 2. Ownership Verification

Every resource access requires ownership check:

```python
# backend/api/documents.py
@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Step 1: Fetch document
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Step 2: Verify ownership
    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this document"
        )

    # Step 3: Delete (safe now)
    db.delete(document)
    db.commit()

    return {"message": "Document deleted"}
```

### 3. API Key Scoping

Each API key belongs to exactly one user:

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);
```

**Key cannot be shared across users** - each key is cryptographically tied to one user.

---

## Code Examples

### Example 1: Creating a Document with Isolation

```python
# backend/api/documents.py
@router.post("/documents")
async def create_document(
    file: UploadFile,
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Step 1: Verify user owns the collection
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id  # Ownership check
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Step 2: Create document with user_id
    document = Document(
        id=uuid.uuid4(),
        collection_id=collection_id,
        user_id=current_user.id,  # Set owner
        title=file.filename,
        filename=file.filename,
        processing_status="pending"
    )
    db.add(document)
    db.commit()

    # Step 3: Upload file to user-scoped storage
    file_content = await file.read()
    storage_path = await storage_backend.upload_document(
        user_id=current_user.id,
        collection_id=collection_id,
        document_id=document.id,
        file_content=file_content,
        filename=file.filename
    )

    # Step 4: Queue processing task with user context
    from backend.tasks.document_processing import process_document_task
    process_document_task.delay(
        document_id=str(document.id),
        user_id=str(current_user.id),  # Pass user context
        storage_path=storage_path
    )

    return {"document": document}
```

### Example 2: Search with User Isolation

```python
# backend/api/retrievals.py
@router.post("/retrieve")
async def retrieve_chunks(
    request: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Step 1: Build base query with user filter
    query = db.query(DocumentChunk).filter(
        DocumentChunk.user_id == current_user.id  # User isolation
    )

    # Step 2: Add collection filter if specified
    if request.collection_id:
        collection = db.query(Collection).filter(
            Collection.id == request.collection_id,
            Collection.user_id == current_user.id  # Ownership check
        ).first()

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        query = query.filter(
            DocumentChunk.collection_id == request.collection_id
        )

    # Step 3: Get user's chunks only
    chunks = query.all()

    # Step 4: Perform search (only on user's data)
    results = search_service.search(
        query=request.query,
        chunks=chunks,
        mode=request.mode
    )

    return {"results": results}
```

### Example 3: Chat with Isolated Context

```python
# backend/api/chat.py
@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Step 1: Verify session ownership
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id  # Ownership check
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Create new session for user
        session = ChatSession(
            id=uuid.uuid4(),
            user_id=current_user.id,
            collection_id=request.collection_id
        )
        db.add(session)
        db.commit()

    # Step 2: Retrieve context (user-scoped)
    context_chunks = db.query(DocumentChunk).filter(
        DocumentChunk.user_id == current_user.id,
        DocumentChunk.collection_id == request.collection_id
    ).all()

    # Step 3: Generate response with isolated context
    response = await llm_service.chat(
        message=request.message,
        context=context_chunks,
        user_id=current_user.id
    )

    # Step 4: Save message to user's session
    user_message = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        role="user",
        content=request.message
    )
    assistant_message = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        role="assistant",
        content=response
    )
    db.add_all([user_message, assistant_message])
    db.commit()

    return {"response": response}
```

---

## Testing Multi-Tenancy

### Test Scenario 1: User Cannot Access Other User's Collections

```python
# tests/test_multi_tenancy.py
async def test_user_isolation():
    # Create two users
    user1 = create_user(email="user1@test.com")
    user2 = create_user(email="user2@test.com")

    # User1 creates a collection
    collection1 = create_collection(user_id=user1.id, name="User1 Collection")

    # User2 tries to access User1's collection
    response = await client.get(
        f"/api/collections/{collection1.id}",
        headers={"Authorization": f"Bearer {user2.api_key}"}
    )

    # Should return 404 (not 403, to avoid leaking existence)
    assert response.status_code == 404
    assert response.json()["detail"] == "Collection not found"
```

### Test Scenario 2: Search Results Are User-Scoped

```python
async def test_search_isolation():
    # User1 uploads "Document A"
    doc_a = upload_document(user_id=user1.id, content="Secret user1 data")

    # User2 uploads "Document B"
    doc_b = upload_document(user_id=user2.id, content="Secret user2 data")

    # User2 searches for "secret"
    response = await client.post(
        "/api/retrieve",
        json={"query": "secret"},
        headers={"Authorization": f"Bearer {user2.api_key}"}
    )

    results = response.json()["results"]

    # User2 should only see their own document
    assert len(results) == 1
    assert "user2 data" in results[0]["content"]
    assert "user1 data" not in results[0]["content"]
```

### Test Scenario 3: LightRAG Graph Isolation

```python
async def test_lightrag_isolation():
    # User1 builds a graph
    lightrag1 = get_lightrag(user_id=user1.id, collection_id=collection1.id)
    await lightrag1.insert("Entity A is related to Entity B")

    # User2 builds a separate graph
    lightrag2 = get_lightrag(user_id=user2.id, collection_id=collection2.id)
    await lightrag2.insert("Entity C is related to Entity D")

    # User1 queries their graph
    result1 = await lightrag1.query("How is Entity A related?", mode="local")
    assert "Entity B" in result1
    assert "Entity C" not in result1  # User2's data not visible

    # Verify separate working directories
    assert lightrag1.working_dir.endswith(f"users/{user1.id}/collections/{collection1.id}")
    assert lightrag2.working_dir.endswith(f"users/{user2.id}/collections/{collection2.id}")
    assert lightrag1.working_dir != lightrag2.working_dir
```

---

## Production Checklist

### Database Security
- [ ] All tables have `user_id` foreign key
- [ ] Row-level security policies enabled (optional, for extra protection)
- [ ] Indexes on `user_id` for query performance
- [ ] Regular audits of query patterns to ensure filtering

### API Security
- [ ] All endpoints use `get_current_user` dependency
- [ ] Ownership checks on all resource access
- [ ] No endpoints expose data without user filtering
- [ ] Rate limiting per API key (prevents abuse)

### Storage Security
- [ ] S3 bucket policy enforces user path isolation
- [ ] Object metadata includes `user_id` for verification
- [ ] Presigned URLs scoped to user's objects only
- [ ] Regular S3 access logs review

### LightRAG Security
- [ ] Working directories scoped to `users/{user_id}/collections/{collection_id}`
- [ ] No shared graph data between users
- [ ] File permissions restrict access to backend process only
- [ ] Regular cleanup of stale graphs

### Monitoring
- [ ] Log all cross-user access attempts
- [ ] Alert on 403 errors (potential security issue)
- [ ] Track API key usage per user
- [ ] Monitor storage growth per user

---

## Common Pitfalls

### ❌ Pitfall 1: Forgetting User Filter

```python
# WRONG: Missing user_id filter
def get_all_documents():
    return db.query(Document).all()  # Returns ALL users' documents!

# CORRECT: Always filter by user
def get_user_documents(user_id: UUID):
    return db.query(Document).filter(Document.user_id == user_id).all()
```

### ❌ Pitfall 2: Using Document ID Without Ownership Check

```python
# WRONG: Trusts document_id from client
def delete_document(document_id: UUID):
    document = db.query(Document).filter(Document.id == document_id).first()
    db.delete(document)  # Any user could delete any document!

# CORRECT: Verify ownership
def delete_document(document_id: UUID, current_user: User):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id  # Ownership check
    ).first()

    if not document:
        raise HTTPException(status_code=404)

    db.delete(document)
```

### ❌ Pitfall 3: Shared LightRAG Instance

```python
# WRONG: Single shared LightRAG for all users
lightrag = LightRAG(working_dir="/app/data/lightrag")  # Shared!

# CORRECT: Per-user, per-collection instances
def get_lightrag(user_id: UUID, collection_id: UUID):
    working_dir = f"/app/data/lightrag/users/{user_id}/collections/{collection_id}"
    return LightRAG(working_dir=working_dir)
```

---

## Summary

Mnemosyne's multi-tenancy ensures:

1. **Database Isolation**: Every table filtered by `user_id`
2. **API Isolation**: Authentication + ownership checks on all endpoints
3. **Storage Isolation**: User-scoped S3 paths or filesystem directories
4. **Graph Isolation**: Per-user, per-collection LightRAG instances

**Result**: Users can NEVER access each other's data at any layer of the system.

This architecture supports:
- ✅ Thousands of users on shared infrastructure
- ✅ Complete data privacy and security
- ✅ Efficient resource utilization (shared PostgreSQL, Redis, Celery)
- ✅ Scalable to millions of documents per user
- ✅ GDPR-compliant data deletion (CASCADE DELETE)

---

**Reference**: See `docs/developer/end-to-end-architecture.md` for complete system architecture.
