"""Server-Sent Events (SSE) streaming utilities"""

from typing import Iterator, AsyncIterator, Dict, Any
import httpx
import json


def parse_sse_stream(response: httpx.Response) -> Iterator[Dict[str, Any]]:
    """
    Parse Server-Sent Events from a streaming response.

    Automatically parses JSON events and yields structured dictionaries.
    Event types: delta, sources, done, error

    Args:
        response: httpx Response object with streaming enabled

    Yields:
        Dict with parsed event data (type, delta/sources/done/error fields)

    Example:
        >>> response = client.post("/chat", data={...}, stream=True)
        >>> for event in parse_sse_stream(response):
        ...     if event['type'] == 'delta':
        ...         print(event['delta'], end="", flush=True)
        ...     elif event['type'] == 'sources':
        ...         print(f"\\nSources: {event['sources']}")
        ...     elif event['type'] == 'done':
        ...         print(f"\\nSession ID: {event.get('session_id')}")
    """
    for line in response.iter_lines():
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            try:
                event = json.loads(data)
                yield event
                if event.get('type') == 'done':
                    break
            except json.JSONDecodeError:
                continue


async def parse_sse_stream_async(response: httpx.Response) -> AsyncIterator[Dict[str, Any]]:
    """
    Parse Server-Sent Events from an async streaming response.

    Automatically parses JSON events and yields structured dictionaries.
    Event types: delta, sources, done, error

    Args:
        response: httpx Response object with streaming enabled

    Yields:
        Dict with parsed event data (type, delta/sources/done/error fields)

    Example:
        >>> response = await client.post("/chat", data={...}, stream=True)
        >>> async for event in parse_sse_stream_async(response):
        ...     if event['type'] == 'delta':
        ...         print(event['delta'], end="", flush=True)
        ...     elif event['type'] == 'sources':
        ...         print(f"\\nSources: {event['sources']}")
        ...     elif event['type'] == 'done':
        ...         print(f"\\nSession ID: {event.get('session_id')}")
    """
    async for line in response.aiter_lines():
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            try:
                event = json.loads(data)
                yield event
                if event.get('type') == 'done':
                    break
            except json.JSONDecodeError:
                continue
