"""Chat resource implementation"""

from typing import Optional, Iterator, AsyncIterator, TYPE_CHECKING
from uuid import UUID
from ..types.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatMessageResponse,
)
from .._streaming import parse_sse_stream, parse_sse_stream_async

if TYPE_CHECKING:
    from ..client import Client
    from ..async_client import AsyncClient


class ChatResource:
    """Synchronous Chat resource"""

    def __init__(self, client: "Client"):
        self._client = client

    def chat(
        self,
        message: str,
        session_id: Optional[UUID] = None,
        collection_id: Optional[UUID] = None,
        top_k: int = 5,
        stream: bool = True,
    ) -> Iterator[str]:
        """
        Send a chat message and stream the response.

        Args:
            message: User message (1-2000 characters)
            session_id: Session UUID (creates new session if not provided)
            collection_id: Filter retrieval by collection UUID
            top_k: Number of chunks to retrieve (1-20, default: 5)
            stream: Enable SSE streaming (default: True)

        Yields:
            str: Response chunks from the assistant

        Raises:
            ValidationError: Invalid message or parameters
            APIError: Chat failed
        """
        data = ChatRequest(
            message=message,
            session_id=session_id,
            collection_id=collection_id,
            top_k=top_k,
            stream=stream,
        ).model_dump(exclude_unset=True)

        if stream:
            # Stream response using SSE
            headers = self._client._get_headers()
            headers["Accept"] = "text/event-stream"

            response = self._client._http_client.post(
                f"{self._client.base_url}/chat",
                json=data,
                headers=headers,
                timeout=self._client.timeout,
            )
            self._client._handle_error(response)

            for chunk in parse_sse_stream(response):
                yield chunk
        else:
            # Non-streaming response
            response = self._client.request("POST", "/chat", json=data)
            chat_response = ChatResponse(**response.json())
            yield chat_response.message

    def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ChatSessionResponse]:
        """
        List chat sessions with pagination.

        Args:
            limit: Number of results per page (1-100, default: 20)
            offset: Number of results to skip (default: 0)

        Returns:
            list[ChatSessionResponse]: List of chat sessions
        """
        params = {"limit": limit, "offset": offset}
        response = self._client.request("GET", "/chat/sessions", params=params)
        return [ChatSessionResponse(**session) for session in response.json()]

    def get_session_messages(
        self,
        session_id: UUID,
    ) -> list[ChatMessageResponse]:
        """
        Get all messages in a chat session.

        Args:
            session_id: Session UUID

        Returns:
            list[ChatMessageResponse]: List of messages in chronological order

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
    """Asynchronous Chat resource"""

    def __init__(self, client: "AsyncClient"):
        self._client = client

    async def chat(
        self,
        message: str,
        session_id: Optional[UUID] = None,
        collection_id: Optional[UUID] = None,
        top_k: int = 5,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send a chat message and stream the response (async)"""
        data = ChatRequest(
            message=message,
            session_id=session_id,
            collection_id=collection_id,
            top_k=top_k,
            stream=stream,
        ).model_dump(exclude_unset=True)

        if stream:
            # Stream response using SSE
            headers = self._client._get_headers()
            headers["Accept"] = "text/event-stream"

            response = await self._client._http_client.post(
                f"{self._client.base_url}/chat",
                json=data,
                headers=headers,
                timeout=self._client.timeout,
            )
            self._client._handle_error(response)

            async for chunk in parse_sse_stream_async(response):
                yield chunk
        else:
            # Non-streaming response
            response = await self._client.request("POST", "/chat", json=data)
            chat_response = ChatResponse(**response.json())
            yield chat_response.message

    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ChatSessionResponse]:
        """List chat sessions with pagination (async)"""
        params = {"limit": limit, "offset": offset}
        response = await self._client.request("GET", "/chat/sessions", params=params)
        return [ChatSessionResponse(**session) for session in response.json()]

    async def get_session_messages(
        self,
        session_id: UUID,
    ) -> list[ChatMessageResponse]:
        """Get all messages in a chat session (async)"""
        response = await self._client.request("GET", f"/chat/sessions/{session_id}/messages")
        return [ChatMessageResponse(**msg) for msg in response.json()]

    async def delete_session(self, session_id: UUID) -> None:
        """Delete a chat session and all its messages (async)"""
        await self._client.request("DELETE", f"/chat/sessions/{session_id}")
