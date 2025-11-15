"""
Chat Service
Handles conversational retrieval (RAG) with LLM models via LiteLLM
Supports 100+ model providers (OpenAI, Anthropic, Groq, Ollama, etc.)
"""

from typing import List, Dict, Any, AsyncGenerator
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage
from backend.search.vector_search import VectorSearchService
from backend.embeddings.openai_embedder import OpenAIEmbedder
from backend.services.reranker_service import RerankerService
from backend.config import settings
import logging

import litellm
from langchain_litellm import ChatLiteLLM
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Configure litellm to automatically drop unsupported parameters
litellm.drop_params = True

logger = logging.getLogger(__name__)


class ChatService:
    """
    Chat service with RAG (Retrieval-Augmented Generation)
    Handles conversation, retrieval, and LLM generation
    """

    def __init__(self, db: Session):
        self.db = db
        self.search_service = VectorSearchService(db)
        self.embedder = OpenAIEmbedder()
        self.reranker = RerankerService()
        self.llm = self._initialize_llm()

    def _initialize_llm(self) -> ChatLiteLLM:
        """
        Initialize LiteLLM client with configured provider and model

        Returns:
            ChatLiteLLM instance configured with provider settings
        """
        # Build model string for LiteLLM
        if settings.LLM_MODEL_STRING:
            # Use explicit model string if provided
            model_string = settings.LLM_MODEL_STRING
        else:
            # Build from provider and model name
            model_string = f"{settings.LLM_PROVIDER}/{settings.CHAT_MODEL}"

        # Build LiteLLM kwargs
        litellm_kwargs = {
            "model": model_string,
            "temperature": settings.CHAT_TEMPERATURE,
            "max_tokens": settings.CHAT_MAX_TOKENS,
            "timeout": settings.LLM_TIMEOUT,
        }

        # Add API key based on provider
        if settings.LLM_PROVIDER == "openai" or settings.LLM_PROVIDER.startswith("openai"):
            litellm_kwargs["api_key"] = settings.OPENAI_API_KEY
        # Add other provider API keys here as needed
        # elif settings.LLM_PROVIDER == "anthropic":
        #     litellm_kwargs["api_key"] = settings.ANTHROPIC_API_KEY

        # Add custom API base if provided
        if settings.LLM_API_BASE:
            litellm_kwargs["api_base"] = settings.LLM_API_BASE

        logger.info(f"Initializing LiteLLM with model: {model_string}")
        return ChatLiteLLM(**litellm_kwargs)

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

        # Retrieve relevant documents using hybrid search
        query_embedding = await self.embedder.embed(user_message)

        # Get more results for reranking (2x top_k)
        search_results = self.search_service.hybrid_search(
            query_text=user_message,
            query_embedding=query_embedding,
            collection_id=collection_id,
            user_id=user_id,
            top_k=top_k * 2  # Get more for reranking
        )

        # Rerank results if enabled
        if self.reranker.is_available():
            logger.debug(f"Reranking {len(search_results)} results")
            search_results = self.reranker.rerank(
                query=user_message,
                chunks=search_results,
                top_k=top_k
            )

        # Build context
        context = self._build_context(search_results)

        # Build messages for LLM (LangChain format)
        messages = self._build_langchain_messages(history, user_message, context)

        # Stream response
        full_response = ""
        chunk_ids = [r['chunk_id'] for r in search_results]

        # Stream using LangChain's astream
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                delta = chunk.content
                full_response += delta

                yield {
                    "type": "delta",
                    "delta": delta
                }

        # Save assistant message
        model_string = settings.LLM_MODEL_STRING or f"{settings.LLM_PROVIDER}/{settings.CHAT_MODEL}"
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_response,
            chunk_ids=chunk_ids,
            metadata={
                "model": model_string,
                "temperature": settings.CHAT_TEMPERATURE,
                "chunks_used": len(chunk_ids),
                "provider": settings.LLM_PROVIDER
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

    def _build_langchain_messages(
        self,
        history: List[ChatMessage],
        user_message: str,
        context: str
    ) -> List[SystemMessage | HumanMessage | AIMessage]:
        """
        Build messages for LangChain LLM (ChatLiteLLM)

        Args:
            history: Conversation history
            user_message: Current user message
            context: Retrieved context from knowledge base

        Returns:
            List of LangChain message objects
        """
        messages = [
            SystemMessage(content=(
                "You are a helpful AI assistant with access to a knowledge base. "
                "Answer questions using the provided context. "
                "If the context doesn't contain relevant information, say so. "
                "Always cite sources using [1], [2], etc. when referencing context."
            ))
        ]

        # Add history (last 10 messages, excluding system)
        for msg in history[-10:]:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        # Add current message with context
        if context:
            content = f"Context from knowledge base:\n{context}\n\nUser question: {user_message}"
        else:
            content = user_message

        messages.append(HumanMessage(content=content))

        return messages
