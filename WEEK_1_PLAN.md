# Week 1 Implementation Plan - Database Setup + Basic CRUD

**Goal:** Set up PostgreSQL with pgvector, create core models, and implement basic CRUD endpoints (no processing pipeline yet)

**Status:** Planning
**Duration:** 5-7 days
**Dependencies:** API_DESIGN.md, ARCHITECTURE.md, RESEARCH.md

---

## Overview

Week 1 focuses on **foundation only**:
- ✅ PostgreSQL + pgvector database setup
- ✅ FastAPI application structure
- ✅ Core database models (User, APIKey, Collection, Document)
- ✅ Authentication middleware (API key validation)
- ✅ Basic CRUD endpoints (Collections, Documents - metadata only)
- ❌ NO document processing (Week 2)
- ❌ NO vector search (Week 2)
- ❌ NO Celery (Week 2)

---

## Optimal Implementation Order (7 Steps)

### Step 1: Project Structure Setup (Day 1, Morning)

**Priority:** CRITICAL - Foundation for everything
**Time:** 2-3 hours

**Tasks:**
```bash
mnemosyne/
├── docker-compose.yml         # PostgreSQL + pgvector
├── .env.example               # Environment variables template
├── pyproject.toml             # Python dependencies (Poetry)
├── README.md                  # Updated with setup instructions
│
├── backend/
│   ├── main.py                # FastAPI app entry point
│   ├── config.py              # Configuration management
│   ├── database.py            # Database session management
│   │
│   ├── models/                # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── api_key.py
│   │   ├── collection.py
│   │   └── document.py
│   │
│   ├── schemas/               # Pydantic schemas (request/response)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── collection.py
│   │   └── document.py
│   │
│   ├── api/                   # API routes
│   │   ├── __init__.py
│   │   ├── deps.py            # Dependencies (auth, db)
│   │   ├── auth.py            # Authentication routes
│   │   ├── collections.py     # Collection routes
│   │   └── documents.py       # Document routes
│   │
│   └── core/                  # Core utilities
│       ├── __init__.py
│       ├── security.py        # API key generation, hashing
│       └── exceptions.py      # Custom exceptions
│
└── tests/                     # Tests (Week 2)
    └── __init__.py
```

**Deliverables:**
- Directory structure created
- `pyproject.toml` with dependencies
- `.env.example` with required variables
- Basic `README.md` with setup instructions

**Dependencies:**
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
sqlalchemy = "^2.0.0"
psycopg2-binary = "^2.9.0"
pgvector = "^0.3.0"
pydantic = "^2.0.0"
pydantic-settings = "^2.0.0"
python-dotenv = "^1.0.0"
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
```

---

### Step 2: Docker Compose + PostgreSQL Setup (Day 1, Afternoon)

**Priority:** CRITICAL - Database must be running
**Time:** 1-2 hours

**Tasks:**

1. **Create `docker-compose.yml`:**
```yaml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:latest
    container_name: mnemosyne-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-mnemosyne}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-mnemosyne_dev}
      POSTGRES_DB: ${POSTGRES_DB:-mnemosyne}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mnemosyne"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

2. **Create `scripts/init.sql`:**
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions
SELECT * FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');
```

3. **Create `.env`:**
```bash
# Database
POSTGRES_USER=mnemosyne
POSTGRES_PASSWORD=mnemosyne_dev
POSTGRES_DB=mnemosyne
DATABASE_URL=postgresql://mnemosyne:mnemosyne_dev@localhost:5432/mnemosyne

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Security
SECRET_KEY=your-secret-key-change-in-production
API_KEY_PREFIX=mn_test_
```

4. **Test database:**
```bash
docker-compose up -d postgres
docker-compose logs -f postgres
# Wait for "database system is ready to accept connections"
```

**Deliverables:**
- PostgreSQL running with pgvector extension
- Database accessible at localhost:5432
- Health check passing

---

### Step 3: Database Models (Day 2, Morning)

**Priority:** HIGH - Foundation for all CRUD operations
**Time:** 3-4 hours

**Order of Implementation:**
1. Base model (timestamps, UUID)
2. User model
3. APIKey model
4. Collection model
5. Document model

**Implementation:**

**1. `backend/database.py` - Session Management:**
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**2. `backend/models/user.py`:**
```python
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**3. `backend/models/api_key.py`:**
```python
from sqlalchemy import Column, String, ARRAY, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)
    name = Column(String(255))
    scopes = Column(ARRAY(String))
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="api_keys")
```

**4. `backend/models/collection.py`:**
```python
from sqlalchemy import Column, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base

class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    metadata = Column(JSON, default={})
    config = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="collections")
    documents = relationship("Document", back_populates="collection", cascade="all, delete-orphan")
```

**5. `backend/models/document.py`:**
```python
from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    title = Column(String(512))
    filename = Column(String(512))
    content_type = Column(String(255))
    size_bytes = Column(Integer)

    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    unique_identifier_hash = Column(String(64), unique=True)

    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    metadata = Column(JSON, default={})
    processing_info = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    collection = relationship("Collection", back_populates="documents")
    user = relationship("User")
```

**6. Create all tables:**
```python
# backend/main.py or migration script
from backend.database import engine, Base
from backend.models import user, api_key, collection, document

Base.metadata.create_all(bind=engine)
```

**Deliverables:**
- All 4 models defined
- Relationships configured
- Tables created in PostgreSQL
- Cascade deletes working

---

### Step 4: Pydantic Schemas (Day 2, Afternoon)

**Priority:** HIGH - Required for API validation
**Time:** 2-3 hours

**Implementation:**

**1. `backend/schemas/collection.py`:**
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID

class CollectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict] = {}
    config: Optional[Dict] = {}

class CollectionCreate(CollectionBase):
    pass

class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict] = None

class CollectionResponse(CollectionBase):
    id: UUID
    user_id: UUID
    document_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
```

**2. `backend/schemas/document.py`:**
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID

class DocumentBase(BaseModel):
    title: Optional[str] = None
    filename: Optional[str] = None
    metadata: Optional[Dict] = {}

class DocumentCreate(DocumentBase):
    collection_id: UUID

class DocumentUpdate(BaseModel):
    metadata: Optional[Dict] = None

class DocumentResponse(DocumentBase):
    id: UUID
    collection_id: UUID
    user_id: UUID
    content_type: Optional[str]
    size_bytes: Optional[int]
    status: str
    content_hash: str
    processing_info: Optional[Dict]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
```

**Deliverables:**
- Collection schemas (Create, Update, Response)
- Document schemas (Create, Update, Response)
- Validation rules applied

---

### Step 5: Authentication System (Day 3, Morning)

**Priority:** CRITICAL - Required before any endpoints
**Time:** 3-4 hours

**Implementation:**

**1. `backend/core/security.py`:**
```python
import secrets
import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_api_key() -> tuple[str, str]:
    """Generate API key and return (key, key_hash)"""
    key = f"mn_test_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(key)
    return key, key_hash

def hash_api_key(key: str) -> str:
    """Hash API key using SHA-256"""
    return hashlib.sha256(key.encode()).hexdigest()

def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify API key against hash"""
    return hash_api_key(key) == key_hash

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)
```

**2. `backend/api/deps.py` - Auth Dependencies:**
```python
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.core.security import verify_api_key

async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from API key"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )

    api_key = authorization[7:]  # Remove "Bearer " prefix

    # Hash the provided key
    from backend.core.security import hash_api_key
    key_hash = hash_api_key(api_key)

    # Find API key in database
    api_key_obj = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check if key is expired
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )

    # Update last used timestamp
    api_key_obj.last_used_at = datetime.utcnow()
    db.commit()

    # Get user
    user = db.query(User).filter(User.id == api_key_obj.user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user
```

**3. `backend/api/auth.py` - Auth Endpoints:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.core.security import generate_api_key, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(email: str, password: str, db: Session = Depends(get_db)):
    """Register new user and return API key"""
    # Check if user exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        email=email,
        hashed_password=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate API key
    key, key_hash = generate_api_key()
    api_key_obj = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key[:10],
        name="Default API Key",
        scopes=["documents:read", "documents:write", "retrievals:read"]
    )
    db.add(api_key_obj)
    db.commit()

    return {
        "user_id": user.id,
        "email": user.email,
        "api_key": key  # Only returned once!
    }
```

**Deliverables:**
- API key generation working
- API key hashing (SHA-256)
- Auth middleware (get_current_user)
- Register endpoint

---

### Step 6: Collection CRUD Endpoints (Day 3, Afternoon)

**Priority:** HIGH - First entity to implement
**Time:** 2-3 hours

**Implementation:**

**`backend/api/collections.py`:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.collection import Collection
from backend.schemas.collection import CollectionCreate, CollectionUpdate, CollectionResponse

router = APIRouter(prefix="/collections", tags=["collections"])

@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection: CollectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new collection"""
    # Check for duplicate name
    existing = db.query(Collection).filter(
        Collection.user_id == current_user.id,
        Collection.name == collection.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Collection '{collection.name}' already exists"
        )

    # Create collection
    db_collection = Collection(
        user_id=current_user.id,
        **collection.dict()
    )
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)

    return db_collection

@router.get("", response_model=List[CollectionResponse])
async def list_collections(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all collections for current user"""
    collections = db.query(Collection).filter(
        Collection.user_id == current_user.id
    ).offset(offset).limit(limit).all()

    return collections

@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get collection by ID"""
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return collection

@router.patch("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: UUID,
    collection_update: CollectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update collection"""
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Update fields
    update_data = collection_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)

    db.commit()
    db.refresh(collection)

    return collection

@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete collection and all documents"""
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    db.delete(collection)
    db.commit()

    return None
```

**Deliverables:**
- POST /collections (create)
- GET /collections (list)
- GET /collections/{id} (get)
- PATCH /collections/{id} (update)
- DELETE /collections/{id} (delete)
- Ownership verification working
- Cascade delete working

---

### Step 7: Document CRUD Endpoints (Day 4)

**Priority:** HIGH - Core entity
**Time:** 3-4 hours

**Implementation:**

**`backend/api/documents.py`:**
```python
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import hashlib

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.document import Document
from backend.models.collection import Collection
from backend.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_document(
    collection_id: UUID = Form(...),
    file: UploadFile = File(...),
    metadata: Optional[str] = Form("{}"),  # JSON string
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload document (metadata only in Week 1, processing in Week 2)"""
    # Verify collection ownership
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Read file content
    content = await file.read()

    # Calculate content hash
    content_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = db.query(Document).filter(
        Document.content_hash == content_hash
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Document with same content already exists: {existing.id}"
        )

    # Create document (metadata only, no processing)
    import json
    document = Document(
        collection_id=collection_id,
        user_id=current_user.id,
        title=file.filename,
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(content),
        content_hash=content_hash,
        status="pending",  # Will be processed in Week 2
        metadata=json.loads(metadata) if metadata else {}
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document

@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    collection_id: UUID,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents in collection"""
    # Verify ownership
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    documents = db.query(Document).filter(
        Document.collection_id == collection_id
    ).offset(offset).limit(limit).all()

    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document by ID"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document

@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update document metadata"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update metadata only
    if document_update.metadata:
        document.metadata = document_update.metadata

    db.commit()
    db.refresh(document)

    return document

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete document"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    return None
```

**Deliverables:**
- POST /documents (upload - metadata only)
- GET /documents (list)
- GET /documents/{id} (get)
- PATCH /documents/{id} (update)
- DELETE /documents/{id} (delete)
- Content hashing working
- Duplicate detection working

---

## Week 1 Deliverables Checklist

### Infrastructure
- [ ] PostgreSQL running with pgvector
- [ ] Docker Compose setup
- [ ] Database migrations
- [ ] Health checks

### Authentication
- [ ] User registration
- [ ] API key generation
- [ ] API key authentication middleware
- [ ] JWT support (optional)

### Database Models
- [ ] User model
- [ ] APIKey model
- [ ] Collection model
- [ ] Document model
- [ ] Cascade deletes working

### API Endpoints
- [ ] POST /auth/register
- [ ] POST /collections
- [ ] GET /collections
- [ ] GET /collections/{id}
- [ ] PATCH /collections/{id}
- [ ] DELETE /collections/{id}
- [ ] POST /documents (upload)
- [ ] GET /documents
- [ ] GET /documents/{id}
- [ ] PATCH /documents/{id}
- [ ] DELETE /documents/{id}

### Testing
- [ ] Can create user and get API key
- [ ] Can create collection
- [ ] Can upload document (metadata stored)
- [ ] Can list/get/update/delete collections
- [ ] Can list/get/update/delete documents
- [ ] Ownership verification works
- [ ] Duplicate detection works

### Documentation
- [ ] README updated with setup instructions
- [ ] API documented (OpenAPI/Swagger)
- [ ] Environment variables documented

---

## What's NOT in Week 1

❌ Document processing (Docling, parsing)
❌ Chunking (Chonkie)
❌ Embeddings (text-embedding-3-large)
❌ Vector search
❌ Celery task queue
❌ Redis
❌ LightRAG
❌ Chat API
❌ SDKs

**These are Week 2+**

---

## Testing Strategy (Manual for Week 1)

### Test Flow:

1. **Start PostgreSQL:**
```bash
docker-compose up -d postgres
```

2. **Run FastAPI:**
```bash
cd backend
uvicorn main:app --reload
```

3. **Register user:**
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'

# Response: {"user_id": "...", "email": "...", "api_key": "mn_test_..."}
```

4. **Create collection:**
```bash
curl -X POST "http://localhost:8000/collections" \
  -H "Authorization: Bearer mn_test_..." \
  -H "Content-Type: application/json" \
  -d '{"name": "my-docs", "description": "Test collection"}'
```

5. **Upload document:**
```bash
curl -X POST "http://localhost:8000/documents" \
  -H "Authorization: Bearer mn_test_..." \
  -F "collection_id=<collection_id>" \
  -F "file=@test.pdf"
```

6. **List documents:**
```bash
curl -X GET "http://localhost:8000/documents?collection_id=<collection_id>" \
  -H "Authorization: Bearer mn_test_..."
```

---

## Success Criteria

Week 1 is complete when:
1. ✅ PostgreSQL running with pgvector
2. ✅ User can register and get API key
3. ✅ User can create/read/update/delete collections
4. ✅ User can upload documents (metadata stored, status="pending")
5. ✅ User can list/get/update/delete documents
6. ✅ Ownership verification prevents cross-user access
7. ✅ Duplicate documents rejected by content hash
8. ✅ OpenAPI docs accessible at /docs

**Next Week:** Document processing pipeline with Celery + Docling

---

## Estimated Timeline

| Day | Tasks | Hours |
|-----|-------|-------|
| Day 1 | Project structure + Docker Compose + PostgreSQL | 5-6 |
| Day 2 | Database models + Pydantic schemas | 6-7 |
| Day 3 | Authentication + Collection CRUD | 5-6 |
| Day 4 | Document CRUD | 3-4 |
| Day 5 | Testing + documentation + polish | 3-4 |

**Total:** ~25-30 hours over 5 days
