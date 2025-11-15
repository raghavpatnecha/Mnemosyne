# Week 4 Implementation Plan - Chat API + Conversational Retrieval

**Goal:** Implement conversational retrieval (RAG chat) with streaming responses and session management

**Status:** Planning
**Duration:** 5-7 days
**Dependencies:** Week 3 (retrieval API), Week 2 (embeddings)

---

## Overview

Week 4 focuses on **conversational retrieval**:
- Chat API endpoint (POST /api/v1/chat)
- SSE (Server-Sent Events) streaming for real-time responses
- Session management for conversation history
- Retrieval-Augmented Generation (RAG) with context
- OpenAI GPT-4 integration for chat
- Message history persistence
- NO LightRAG yet (future enhancement)
- NO reranking yet (future enhancement)

---

## Architecture

```
Chat Request (POST /api/v1/chat)
    ↓
Load/Create Session
    ↓
Retrieve conversation history
    ↓
Generate retrieval query from conversation context
    ↓
Search documents (use Week 3 retrieval API)
    ↓
Build context with retrieved chunks
    ↓
Call OpenAI Chat Completion (GPT-4) with streaming
    ↓
Stream response via SSE (Server-Sent Events)
    ↓
Save message history to database
    ↓
Return sources with response
```

---

## Database Schema Changes

### New Table: chat_sessions

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES collections(id) ON DELETE SET NULL,

    title VARCHAR(255),
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,

    -- Indexes
    INDEX idx_sessions_user_id (user_id),
    INDEX idx_sessions_collection_id (collection_id)
);
```

### New Table: chat_messages

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,

    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,

    -- Retrieval metadata
    chunk_ids JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    INDEX idx_messages_session_id (session_id),
    INDEX idx_messages_created_at (created_at)
);
```

---

## Implementation Steps (6 Steps)

### Step 1: Database Models (Day 1, Morning)

**Priority:** CRITICAL - Foundation for chat
**Time:** 2-3 hours

**Implementation:**

**1. Create `backend/models/chat_session.py`:**
```python
from sqlalchemy import Column, String, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class ChatSession(Base):
    """
    Chat session model - conversation container

    Attributes:
        id: Session UUID
        user_id: Session owner
        collection_id: Optional collection filter
        title: Session title (auto-generated from first message)
        metadata: Flexible metadata
        created_at: Session creation time
        updated_at: Last update time
        last_message_at: Timestamp of last message

    Relationships:
        user: Session owner
        collection: Optional collection
        messages: Chat messages (1:N)
    """

    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="SET NULL"), index=True)

    title = Column(String(255))
    metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")
    collection = relationship("Collection")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, title={self.title})>"
```

**2. Create `backend/models/chat_message.py`:**
```python
from sqlalchemy import Column, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class ChatMessage(Base):
    """
    Chat message model - individual messages in conversation

    Attributes:
        id: Message UUID
        session_id: Parent session
        role: Message role ('user', 'assistant', 'system')
        content: Message text
        chunk_ids: List of chunk UUIDs used (for assistant messages)
        metadata: Flexible metadata (tokens, latency, etc.)
        created_at: Message timestamp

    Relationships:
        session: Parent chat session
    """

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Retrieval metadata
    chunk_ids = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role={self.role}, session_id={self.session_id})>"
```

**3. Update `backend/models/__init__.py`:**
```python
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.models.collection import Collection
from backend.models.document import Document
from backend.models.chunk import DocumentChunk
from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage

__all__ = ["User", "APIKey", "Collection", "Document", "DocumentChunk", "ChatSession", "ChatMessage"]
```

**Deliverables:**
- ChatSession model
- ChatMessage model
- Cascade deletes configured

---

### Step 2: Chat Service (Day 1-2)

**Priority:** CRITICAL - Core chat logic
**Time:** 6-8 hours

**Implementation:**

**Create `backend/services/chat_service.py`:**
```python
from typing import List, Dict, Any, AsyncGenerator
from sqlalchemy.orm import Session
from uuid import UUID
import asyncio

from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage
from backend.search.vector_search import VectorSearchService
from backend.embeddings.openai_embedder import OpenAIEmbedder
from openai import AsyncOpenAI
from backend.config import settings


class ChatService:
    """
    Chat service with RAG (Retrieval-Augmented Generation)
    Handles conversation, retrieval, and LLM generation
    """

    def __init__(self, db: Session):
        self.db = db
        self.search_service = VectorSearchService(db)
        self.embedder = OpenAIEmbedder()
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat_stream(
        self,
        session_id: UUID,
        user_message: str,
        user_id: UUID,
        collection_id: UUID = None,
        top_k: int = 5
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat response with RAG

        Args:
            session_id: Chat session ID
            user_message: User's message
            user_id: User ID for ownership
            collection_id: Optional collection filter
            top_k: Number of chunks to retrieve

        Yields:
            Dict with deltas, sources, done flag
        """
        # Get or create session
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()

        if not session:
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                collection_id=collection_id,
                title=user_message[:100]  # Auto-title from first message
            )
            self.db.add(session)
            self.db.commit()

        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_message
        )
        self.db.add(user_msg)
        self.db.commit()

        # Get conversation history
        history = self._get_history(session_id, limit=10)

        # Retrieve relevant documents
        query_embedding = await self.embedder.embed(user_message)
        search_results = self.search_service.search(
            query_embedding=query_embedding,
            collection_id=collection_id,
            user_id=user_id,
            top_k=top_k
        )

        # Build context
        context = self._build_context(search_results)

        # Build messages for OpenAI
        messages = self._build_messages(history, user_message, context)

        # Stream response
        full_response = ""
        chunk_ids = [r['chunk_id'] for r in search_results]

        stream = await self.openai_client.chat.completions.create(
            model=settings.CHAT_MODEL,
            messages=messages,
            temperature=settings.CHAT_TEMPERATURE,
            max_tokens=settings.CHAT_MAX_TOKENS,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                full_response += delta

                yield {
                    "type": "delta",
                    "delta": delta
                }

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_response,
            chunk_ids=chunk_ids
        )
        self.db.add(assistant_msg)

        # Update session
        from datetime import datetime
        session.last_message_at = datetime.utcnow()
        self.db.commit()

        # Send sources
        yield {
            "type": "sources",
            "sources": [
                {
                    "chunk_id": r['chunk_id'],
                    "content": r['content'][:200],
                    "document": r['document'],
                    "score": r['score']
                }
                for r in search_results
            ]
        }

        # Send done
        yield {
            "type": "done",
            "done": True
        }

    def _get_history(self, session_id: UUID, limit: int = 10) -> List[ChatMessage]:
        """Get conversation history"""
        return self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()[::-1]

    def _build_context(self, search_results: List[Dict]) -> str:
        """Build context from retrieved chunks"""
        if not search_results:
            return ""

        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"[{i}] {result['content']}\n"
                f"Source: {result['document']['filename']}\n"
            )

        return "\n".join(context_parts)

    def _build_messages(
        self,
        history: List[ChatMessage],
        user_message: str,
        context: str
    ) -> List[Dict[str, str]]:
        """Build messages for OpenAI API"""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant with access to a knowledge base. "
                    "Answer questions using the provided context. "
                    "If the context doesn't contain relevant information, say so. "
                    "Always cite sources using [1], [2], etc."
                )
            }
        ]

        # Add history (last 10 messages)
        for msg in history[-10:]:
            if msg.role != "system":
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Add current message with context
        if context:
            content = f"Context:\n{context}\n\nQuestion: {user_message}"
        else:
            content = user_message

        messages.append({
            "role": "user",
            "content": content
        })

        return messages
```

**Deliverables:**
- ChatService with RAG
- Streaming support
- Context building from search results
- Conversation history management

---

### Step 3: Pydantic Schemas (Day 2, Afternoon)

**Priority:** HIGH - Request/Response validation
**Time:** 1-2 hours

**Implementation:**

**Create `backend/schemas/chat.py`:**
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime


class Message(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    session_id: Optional[UUID] = Field(None, description="Session ID (creates new if not provided)")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    collection_id: Optional[UUID] = Field(None, description="Filter retrieval by collection")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    stream: bool = Field(default=True, description="Enable streaming")


class Source(BaseModel):
    """Source chunk information"""
    chunk_id: str
    content: str
    document: Dict
    score: float


class ChatResponse(BaseModel):
    """Response schema for chat endpoint (non-streaming)"""
    session_id: UUID
    message: str
    sources: List[Source]


class ChatSessionResponse(BaseModel):
    """Chat session metadata"""
    id: UUID
    user_id: UUID
    collection_id: Optional[UUID]
    title: Optional[str]
    created_at: datetime
    last_message_at: Optional[datetime]
    message_count: int

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
```

**Deliverables:**
- ChatRequest schema
- ChatResponse schema (for non-streaming)
- ChatSessionResponse schema
- Message and Source schemas

---

### Step 4: Chat API Endpoint (Day 3)

**Priority:** CRITICAL - Main API
**Time:** 4-5 hours

**Implementation:**

**Create `backend/api/chat.py`:**
```python
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
import json

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatMessageResponse,
    Source
)
from backend.services.chat_service import ChatService
from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_class=StreamingResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with RAG and streaming

    Supports Server-Sent Events (SSE) streaming for real-time responses.

    Args:
        request: Chat request (message, session_id, etc.)
        db: Database session
        current_user: Authenticated user

    Returns:
        StreamingResponse: SSE stream with deltas, sources, done

    Example:
        ```json
        {
          "message": "What is machine learning?",
          "session_id": "uuid-or-null",
          "collection_id": "uuid-or-null",
          "top_k": 5,
          "stream": true
        }
        ```

    SSE Response Format:
        ```
        data: {"type": "delta", "delta": "Machine"}
        data: {"type": "delta", "delta": " learning"}
        data: {"type": "sources", "sources": [...]}
        data: {"type": "done", "done": true}
        ```
    """
    session_id = request.session_id or uuid4()

    chat_service = ChatService(db)

    async def event_stream():
        """Generate SSE events"""
        async for event in chat_service.chat_stream(
            session_id=session_id,
            user_message=request.message,
            user_id=current_user.id,
            collection_id=request.collection_id,
            top_k=request.top_k
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List chat sessions for current user"""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.last_message_at.desc().nullslast()).offset(offset).limit(limit).all()

    return [
        ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            collection_id=s.collection_id,
            title=s.title,
            created_at=s.created_at,
            last_message_at=s.last_message_at,
            message_count=len(s.messages)
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages for a session"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        from backend.core.exceptions import http_404_not_found
        raise http_404_not_found("Session not found")

    return [
        ChatMessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at
        )
        for m in session.messages
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat session and all its messages"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        from backend.core.exceptions import http_404_not_found
        raise http_404_not_found("Session not found")

    db.delete(session)
    db.commit()

    return None
```

**Register in `backend/main.py`:**
```python
from backend.api import auth, collections, documents, retrievals, chat

app.include_router(chat.router, prefix="/api/v1")
```

**Deliverables:**
- POST /api/v1/chat (streaming SSE)
- GET /api/v1/chat/sessions
- GET /api/v1/chat/sessions/{id}/messages
- DELETE /api/v1/chat/sessions/{id}

---

### Step 5: Configuration Updates (Day 3, Afternoon)

**Priority:** MEDIUM - Settings for chat
**Time:** 30 minutes

**Update `backend/config.py`:**
```python
# Chat Settings
CHAT_MODEL: str = "gpt-4o-mini"  # or "gpt-4"
CHAT_TEMPERATURE: float = 0.7
CHAT_MAX_TOKENS: int = 1000
```

**Update `.env.example`:**
```bash
# Chat
CHAT_MODEL=gpt-4o-mini
CHAT_TEMPERATURE=0.7
CHAT_MAX_TOKENS=1000
```

**Deliverables:**
- Chat configuration added
- Environment variables documented

---

### Step 6: Testing (Day 4)

**Priority:** HIGH - Verification
**Time:** 3-4 hours

**Test Flow:**

1. **Create session and chat:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?",
    "stream": true
  }'
```

2. **Continue conversation:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "$SESSION_ID",
    "message": "How does it work?",
    "stream": true
  }'
```

3. **List sessions:**
```bash
curl -X GET "http://localhost:8000/api/v1/chat/sessions" \
  -H "Authorization: Bearer $API_KEY"
```

4. **Get session history:**
```bash
curl -X GET "http://localhost:8000/api/v1/chat/sessions/$SESSION_ID/messages" \
  -H "Authorization: Bearer $API_KEY"
```

**Deliverables:**
- All endpoints tested
- Streaming verified
- Session persistence confirmed

---

## Week 4 Success Criteria

Week 4 is complete when:
1. POST /api/v1/chat endpoint works with streaming
2. Conversations saved in database
3. Session management works (create, list, get, delete)
4. RAG integration retrieves relevant context
5. OpenAI GPT integration generates responses
6. SSE streaming delivers real-time responses
7. Message history persists
8. Sources included with responses
9. Multi-turn conversations work
10. API documented in Swagger

---

## What's NOT in Week 4

- LightRAG integration - Future
- Reranking with cross-encoder - Future
- Query expansion - Future
- Caching layer - Future
- Advanced session features (sharing, export) - Future

---

## Estimated Timeline

| Day | Tasks | Hours |
|-----|-------|-------|
| Day 1 | Database models + Chat service (part 1) | 6-8 |
| Day 2 | Chat service (part 2) + Schemas | 5-6 |
| Day 3 | API endpoint + Configuration | 5-6 |
| Day 4 | Testing + Polish | 3-4 |

**Total:** ~20-25 hours over 4 days

---

## Next Steps

After Week 4, the platform will have:
- Full RAG pipeline (upload → process → search → chat)
- 17 API endpoints
- Conversational AI with sources
- Ready for production use

Future enhancements:
- Week 5+: LightRAG, connectors, additional parsers, production polish
