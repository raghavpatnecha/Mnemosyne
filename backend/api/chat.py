"""
Chat API endpoints
RAG-powered conversational AI with SSE streaming
Uses retrieval endpoint internally for all search operations
"""

import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Union
from uuid import UUID, uuid4

from backend.database import get_db
from backend.core.exceptions import http_400_bad_request, http_404_not_found
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.schemas.chat import (
    ChatRequest,
    ChatCompletionResponse,
    ChatSessionResponse,
    ChatMessageResponse,
    StreamChunk
)
from backend.services.chat_service import ChatService
from backend.models.chat_session import ChatSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatCompletionResponse,
    responses={
        200: {
            "description": "Chat response (streaming or non-streaming)",
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/ChatCompletionResponse"}},
                "text/event-stream": {"schema": {"type": "string"}}
            }
        }
    }
)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """
    RAG-powered chat with optional streaming

    Uses the retrieval endpoint internally for all search operations,
    inheriting all its optimizations (LightRAG, reranking, hierarchical search).

    Request Formats:
        OpenAI-compatible messages array (recommended):
        ```json
        {
          "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "What is machine learning?"}
          ],
          "collection_id": "uuid-here",
          "stream": true,
          "retrieval": {"mode": "hybrid", "top_k": 5, "enable_graph": true},
          "generation": {"model": "gpt-4o-mini", "temperature": 0.7}
        }
        ```

        Legacy single message (deprecated):
        ```json
        {
          "message": "What is machine learning?",
          "collection_id": "uuid-here"
        }
        ```

    Streaming Response (SSE):
        ```
        data: {"type": "sources", "sources": [{...}]}
        data: {"type": "graph_context", "graph_context": {...}}
        data: {"type": "delta", "content": "Machine"}
        data: {"type": "delta", "content": " learning"}
        data: {"type": "usage", "usage": {...}}
        data: {"type": "done", "metadata": {...}}
        ```

    Non-Streaming Response:
        Returns ChatCompletionResponse with query, response, sources,
        graph_context, usage, and metadata.

    Args:
        request: Chat request with messages/message, configs
        db: Database session
        current_user: Authenticated user

    Returns:
        ChatCompletionResponse or StreamingResponse (SSE)
    """
    session_id = request.session_id or uuid4()
    chat_service = ChatService(db)

    # Extract user message
    try:
        user_message = request.get_user_message()
    except ValueError as e:
        raise http_400_bad_request(str(e))

    # Get optional system prompt
    system_prompt = request.get_system_prompt()

    # DEBUG: Log collection_id at API entry point
    logger.info(f"[DEBUG] /chat endpoint received collection_id={request.collection_id}")

    if request.stream:
        # Streaming mode
        async def event_stream():
            """Generate SSE events from StreamChunk objects"""
            try:
                async for chunk in chat_service.chat_stream(
                    session_id=session_id,
                    user_message=user_message,
                    user=current_user,
                    collection_id=request.collection_id,
                    retrieval_config=request.retrieval,
                    generation_config=request.generation,
                    system_prompt=system_prompt,
                    # NEW: Enhanced parameters
                    model=request.model,
                    preset=request.preset.value,
                    reasoning_mode=request.reasoning_mode.value,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    # NEW: Custom instruction and follow-up
                    custom_instruction=request.custom_instruction,
                    is_follow_up=request.is_follow_up,
                ):
                    # Convert StreamChunk to SSE data
                    yield f"data: {chunk.model_dump_json()}\n\n"
            except Exception as e:
                error_chunk = StreamChunk(type="error", error=str(e))
                yield f"data: {error_chunk.model_dump_json()}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # Non-streaming mode
        return await chat_service.chat(
            session_id=session_id,
            user_message=user_message,
            user=current_user,
            collection_id=request.collection_id,
            retrieval_config=request.retrieval,
            generation_config=request.generation,
            system_prompt=system_prompt,
            # NEW: Enhanced parameters
            model=request.model,
            preset=request.preset.value,
            reasoning_mode=request.reasoning_mode.value,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            # NEW: Custom instruction and follow-up
            custom_instruction=request.custom_instruction,
            is_follow_up=request.is_follow_up,
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
        limit: Max sessions to return (default: 20)
        offset: Offset for pagination
        db: Database session
        current_user: Authenticated user

    Returns:
        List of chat sessions ordered by last_message_at (most recent first)
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
    Get messages for a chat session

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
        raise http_404_not_found("Session not found")

    db.delete(session)
    db.commit()

    return None
