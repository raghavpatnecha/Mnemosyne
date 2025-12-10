"""Chat resource implementation - OpenAI-compatible with RAG enhancements"""

from typing import Optional, Iterator, AsyncIterator, List, Dict, Union, TYPE_CHECKING
from uuid import UUID
import json
from ..types.chat import (
    ChatRequest,
    ChatCompletionResponse,
    ChatSessionResponse,
    ChatMessageResponse,
    StreamChunk,
    Message,
    MessageRole,
    RetrievalConfig,
    GenerationConfig,
    ChatPreset,
    ReasoningMode,
    Source,
    UsageStats,
    ChatMetadata,
)
from .._streaming import parse_sse_stream, parse_sse_stream_async

if TYPE_CHECKING:
    from ..client import Client
    from ..async_client import AsyncClient


class ChatResource:
    """Synchronous Chat resource with OpenAI-compatible interface"""

    def __init__(self, client: "Client"):
        self._client = client

    def chat(
        self,
        message: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        session_id: Optional[UUID] = None,
        collection_id: Optional[UUID] = None,
        stream: bool = True,
        retrieval: Optional[Dict] = None,
        generation: Optional[Dict] = None,
        system_prompt: Optional[str] = None,
        # NEW: Enhanced parameters
        model: Optional[str] = None,
        preset: str = "detailed",
        reasoning_mode: str = "standard",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        custom_instruction: Optional[str] = None,
        is_follow_up: bool = False,
    ) -> Union[Iterator[StreamChunk], ChatCompletionResponse]:
        """
        Send a chat message with RAG-powered response.

        Supports both OpenAI-compatible messages array and simple message string.

        Args:
            message: Simple user message (deprecated, use messages instead)
            messages: OpenAI-compatible messages array
                [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            session_id: Session UUID for multi-turn conversations
            collection_id: Filter retrieval by collection UUID
            stream: Enable SSE streaming (default: True)
            retrieval: Retrieval configuration dict
            generation: Generation configuration dict
            system_prompt: System prompt (alternative to messages with system role)
            model: LLM model override (e.g., "gpt-4o", "claude-3-opus")
            preset: Answer style preset ("concise", "detailed", "research", "technical", "creative")
            reasoning_mode: Reasoning mode ("standard" or "deep" for multi-step iterative)
            temperature: Temperature override (0.0-2.0)
            max_tokens: Max tokens override

        Returns:
            If stream=True: Iterator[StreamChunk] yielding chunks
            If stream=False: ChatCompletionResponse with full response

        Example:
            # Simple message with preset
            for chunk in client.chat.chat("What is machine learning?", preset="research"):
                if chunk.type == "delta":
                    print(chunk.content, end="")

            # Deep reasoning mode
            for chunk in client.chat.chat(
                "Compare RAG architectures",
                reasoning_mode="deep",
                model="gpt-4o"
            ):
                if chunk.type == "reasoning_step":
                    print(f"Step {chunk.step}: {chunk.description}")
                elif chunk.type == "delta":
                    print(chunk.content, end="")
        """
        # Build messages array
        msg_list = None
        if messages:
            msg_list = [Message(role=MessageRole(m["role"]), content=m["content"]) for m in messages]
        elif system_prompt and message:
            msg_list = [
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                Message(role=MessageRole.USER, content=message)
            ]

        # Build request
        request_data = {
            "session_id": session_id,
            "collection_id": collection_id,
            "stream": stream,
            "preset": preset,
            "reasoning_mode": reasoning_mode,
            "is_follow_up": is_follow_up,
        }

        if msg_list:
            request_data["messages"] = [m.model_dump() for m in msg_list]
        elif message:
            request_data["message"] = message

        if retrieval:
            request_data["retrieval"] = retrieval
        if generation:
            request_data["generation"] = generation
        if model:
            request_data["model"] = model
        if temperature is not None:
            request_data["temperature"] = temperature
        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens
        if custom_instruction:
            request_data["custom_instruction"] = custom_instruction

        # Remove None values
        request_data = {k: v for k, v in request_data.items() if v is not None}

        if stream:
            return self._stream_chat(request_data)
        else:
            response = self._client.request("POST", "/chat", json=request_data)
            return ChatCompletionResponse(**response.json())

    def _stream_chat(self, data: Dict) -> Iterator[StreamChunk]:
        """Stream chat response using SSE"""
        headers = self._client._get_headers()
        headers["Accept"] = "text/event-stream"

        response = self._client._http_client.post(
            f"{self._client.base_url}/chat",
            json=data,
            headers=headers,
            timeout=self._client.timeout,
        )
        self._client._handle_error(response)

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if line_str.startswith("data: "):
                    try:
                        chunk_data = json.loads(line_str[6:])
                        yield StreamChunk(**chunk_data)
                    except json.JSONDecodeError:
                        continue

    def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ChatSessionResponse]:
        """
        List chat sessions with pagination.

        Args:
            limit: Number of results per page (1-100, default: 20)
            offset: Number of results to skip (default: 0)

        Returns:
            List of chat sessions ordered by last_message_at
        """
        params = {"limit": limit, "offset": offset}
        response = self._client.request("GET", "/chat/sessions", params=params)
        return [ChatSessionResponse(**session) for session in response.json()]

    def get_session_messages(
        self,
        session_id: UUID,
    ) -> List[ChatMessageResponse]:
        """
        Get all messages in a chat session.

        Args:
            session_id: Session UUID

        Returns:
            List of messages in chronological order

        Raises:
            NotFoundError: Session not found
        """
        response = self._client.request("GET", f"/chat/sessions/{session_id}/messages")
        return [ChatMessageResponse(**msg) for msg in response.json()]

    def delete_session(self, session_id: UUID) -> None:
        """
        Delete a chat session and all its messages.

        Args:
            session_id: Session UUID

        Raises:
            NotFoundError: Session not found
        """
        self._client.request("DELETE", f"/chat/sessions/{session_id}")


class AsyncChatResource:
    """Asynchronous Chat resource with OpenAI-compatible interface"""

    def __init__(self, client: "AsyncClient"):
        self._client = client

    async def chat(
        self,
        message: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        session_id: Optional[UUID] = None,
        collection_id: Optional[UUID] = None,
        stream: bool = True,
        retrieval: Optional[Dict] = None,
        generation: Optional[Dict] = None,
        system_prompt: Optional[str] = None,
        # NEW: Enhanced parameters
        model: Optional[str] = None,
        preset: str = "detailed",
        reasoning_mode: str = "standard",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        custom_instruction: Optional[str] = None,
        is_follow_up: bool = False,
    ) -> Union[AsyncIterator[StreamChunk], ChatCompletionResponse]:
        """
        Send a chat message with RAG-powered response (async).

        See ChatResource.chat for full documentation.
        """
        # Build messages array
        msg_list = None
        if messages:
            msg_list = [Message(role=MessageRole(m["role"]), content=m["content"]) for m in messages]
        elif system_prompt and message:
            msg_list = [
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                Message(role=MessageRole.USER, content=message)
            ]

        # Build request
        request_data = {
            "session_id": session_id,
            "collection_id": collection_id,
            "stream": stream,
            "preset": preset,
            "reasoning_mode": reasoning_mode,
            "is_follow_up": is_follow_up,
        }

        if msg_list:
            request_data["messages"] = [m.model_dump() for m in msg_list]
        elif message:
            request_data["message"] = message

        if retrieval:
            request_data["retrieval"] = retrieval
        if generation:
            request_data["generation"] = generation
        if model:
            request_data["model"] = model
        if temperature is not None:
            request_data["temperature"] = temperature
        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens
        if custom_instruction:
            request_data["custom_instruction"] = custom_instruction

        # Remove None values
        request_data = {k: v for k, v in request_data.items() if v is not None}

        if stream:
            return self._stream_chat(request_data)
        else:
            response = await self._client.request("POST", "/chat", json=request_data)
            return ChatCompletionResponse(**response.json())

    async def _stream_chat(self, data: Dict) -> AsyncIterator[StreamChunk]:
        """Stream chat response using SSE (async)"""
        headers = self._client._get_headers()
        headers["Accept"] = "text/event-stream"

        response = await self._client._http_client.post(
            f"{self._client.base_url}/chat",
            json=data,
            headers=headers,
            timeout=self._client.timeout,
        )
        self._client._handle_error(response)

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                try:
                    chunk_data = json.loads(line[6:])
                    yield StreamChunk(**chunk_data)
                except json.JSONDecodeError:
                    continue

    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ChatSessionResponse]:
        """List chat sessions with pagination (async)"""
        params = {"limit": limit, "offset": offset}
        response = await self._client.request("GET", "/chat/sessions", params=params)
        return [ChatSessionResponse(**session) for session in response.json()]

    async def get_session_messages(
        self,
        session_id: UUID,
    ) -> List[ChatMessageResponse]:
        """Get all messages in a chat session (async)"""
        response = await self._client.request("GET", f"/chat/sessions/{session_id}/messages")
        return [ChatMessageResponse(**msg) for msg in response.json()]

    async def delete_session(self, session_id: UUID) -> None:
        """Delete a chat session and all its messages (async)"""
        await self._client.request("DELETE", f"/chat/sessions/{session_id}")
