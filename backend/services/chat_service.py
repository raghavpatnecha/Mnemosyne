"""
Chat Service
Handles conversational retrieval (RAG) with OpenAI chat models
"""

from typing import List, Dict, Any, AsyncGenerator
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

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
            Dict with type (delta/sources/done) and data
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
                title=user_message[:100]
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
            chunk_ids=chunk_ids,
            metadata={
                "model": settings.CHAT_MODEL,
                "temperature": settings.CHAT_TEMPERATURE,
                "chunks_used": len(chunk_ids)
            }
        )
        self.db.add(assistant_msg)

        # Update session
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
            "done": True,
            "session_id": str(session_id)
        }

    def _get_history(self, session_id: UUID, limit: int = 10) -> List[ChatMessage]:
        """Get conversation history"""
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
        return messages[::-1]

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
                    "Always cite sources using [1], [2], etc. when referencing context."
                )
            }
        ]

        # Add history (last 10 messages, excluding system)
        for msg in history[-10:]:
            if msg.role != "system":
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Add current message with context
        if context:
            content = f"Context from knowledge base:\n{context}\n\nUser question: {user_message}"
        else:
            content = user_message

        messages.append({
            "role": "user",
            "content": content
        })

        return messages
