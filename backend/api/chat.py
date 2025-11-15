"""
Chat API endpoints
Conversational retrieval with RAG and SSE streaming
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID, uuid4
import json

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.schemas.chat import (
    ChatRequest,
    ChatSessionResponse,
    ChatMessageResponse
)
from backend.services.chat_service import ChatService
from backend.models.chat_session import ChatSession

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
    Retrieves relevant context from documents and generates AI responses.

    Args:
        request: Chat request (message, session_id, etc.)
        db: Database session
        current_user: Authenticated user

    Returns:
        StreamingResponse: SSE stream with deltas, sources, done

    Example Request:
        ```json
        {
          "message": "What is machine learning?",
          "session_id": null,
          "collection_id": "uuid-here",
          "top_k": 5,
          "stream": true
        }
        ```

    SSE Response Format:
        ```
        data: {"type": "delta", "delta": "Machine"}
        data: {"type": "delta", "delta": " learning"}
        data: {"type": "sources", "sources": [{...}]}
        data: {"type": "done", "done": true, "session_id": "uuid"}
        ```
    """
    session_id = request.session_id or uuid4()

    chat_service = ChatService(db)

    async def event_stream():
        """Generate SSE events"""
        try:
            async for event in chat_service.chat_stream(
                session_id=session_id,
                user_message=request.message,
                user_id=current_user.id,
                collection_id=request.collection_id,
                top_k=request.top_k
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            error_event = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"

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
    """
    List chat sessions for current user

    Args:
        limit: Max sessions to return
        offset: Offset for pagination
        db: Database session
        current_user: Authenticated user

    Returns:
        List of chat sessions ordered by last_message_at
    """
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(
        ChatSession.last_message_at.desc().nullslast()
    ).offset(offset).limit(limit).all()

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
    """
    Get messages for a session

    Args:
        session_id: Session UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        List of messages in chronological order

    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
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
    """
    Delete a chat session and all its messages

    Args:
        session_id: Session UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if session not found or not owned by user
    """
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
