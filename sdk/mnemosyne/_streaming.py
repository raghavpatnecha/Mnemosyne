"""Server-Sent Events (SSE) streaming utilities"""

from typing import Iterator, AsyncIterator
import httpx


def parse_sse_stream(response: httpx.Response) -> Iterator[str]:
    """
    Parse Server-Sent Events from a streaming response.

    Args:
        response: httpx Response object with streaming enabled

    Yields:
        str: Event data from each SSE message

    Example:
        >>> response = client.post("/chat", data={...}, stream=True)
        >>> for chunk in parse_sse_stream(response):
        ...     print(chunk, end="", flush=True)
    """
    for line in response.iter_lines():
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            yield data


async def parse_sse_stream_async(response: httpx.Response) -> AsyncIterator[str]:
    """
    Parse Server-Sent Events from an async streaming response.

    Args:
        response: httpx Response object with streaming enabled

    Yields:
        str: Event data from each SSE message

    Example:
        >>> response = await client.post("/chat", data={...}, stream=True)
        >>> async for chunk in parse_sse_stream_async(response):
        ...     print(chunk, end="", flush=True)
    """
    async for line in response.aiter_lines():
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            yield data
