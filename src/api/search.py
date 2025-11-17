"""
Search API using Mnemosyne SDK
Provides streaming chat responses with the SDK backend
"""
import asyncio
import json
from typing import AsyncGenerator
from mnemosyne import Client
from mnemosyne.exceptions import MnemosyneError
from src.config import Config

config = Config()

# Initialize SDK client (will be reinitialized with proper API key when available)
try:
    sdk_client = Client(
        api_key=config.SDK.API_KEY,
        base_url=config.SDK.BASE_URL,
        timeout=config.SDK.TIMEOUT,
        max_retries=config.SDK.MAX_RETRIES
    )
except Exception as e:
    print(f"Warning: SDK client initialization failed: {e}")
    sdk_client = None


def decode_query(query: str) -> str:
    """Decode the query string from URL format."""
    query_parts = query.split('-')
    decoded_parts = []
    for part in query_parts:
        if part.isalnum() and not part.isalpha() and not part.isdigit():
            break
        decoded_parts.append(part)
    return ' '.join(decoded_parts)


async def stream_response(query: str, collection_id: str = None,
                         session_id: str = None, mode: str = None) -> AsyncGenerator[str, None]:
    """
    Generate streaming chat response using Mnemosyne SDK.

    Args:
        query: Search query
        collection_id: Optional collection ID to filter results
        session_id: Optional session ID for multi-turn conversations
        mode: Search mode (hybrid, semantic, keyword, hierarchical, graph)
    """
    if not sdk_client or not config.SDK.API_KEY:
        yield 'data: {"error": "SDK not configured. Please set MNEMOSYNE_API_KEY"}\n\n'
        return

    try:
        # Use configured search mode or default
        search_mode = mode or config.SEARCH.DEFAULT_MODE

        # Stream chat response from SDK
        for chunk in sdk_client.chat.chat(
            message=query,
            collection_id=collection_id,
            session_id=session_id,
            top_k=config.CHAT.TOP_K,
            stream=True
        ):
            if isinstance(chunk, str):
                # Stream text chunks
                if chunk.strip():
                    yield f'data: {chunk}\n\n'
                    await asyncio.sleep(0.01)  # Small delay for smooth streaming
            elif isinstance(chunk, dict):
                # Stream JSON metadata (if any)
                yield f'data: {json.dumps(chunk)}\n\n'

        # Send end marker
        yield 'data: [DONE]\n\n'

    except MnemosyneError as e:
        print(f"SDK Error: {str(e)}")
        error_response = {
            "error": str(e),
            "type": type(e).__name__
        }
        yield f'data: {json.dumps(error_response)}\n\n'
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        error_response = {
            "error": "An unexpected error occurred while processing your request",
            "details": str(e)
        }
        yield f'data: {json.dumps(error_response)}\n\n'


async def search_documents(query: str, collection_id: str = None,
                          mode: str = None, top_k: int = None) -> dict:
    """
    Search documents using Mnemosyne SDK retrieval.

    Args:
        query: Search query
        collection_id: Optional collection ID to filter results
        mode: Search mode (semantic, keyword, hybrid, hierarchical, graph)
        top_k: Number of results to return

    Returns:
        Dict with search results
    """
    if not sdk_client or not config.SDK.API_KEY:
        return {"error": "SDK not configured. Please set MNEMOSYNE_API_KEY"}

    try:
        # Use configured values or defaults
        search_mode = mode or config.SEARCH.DEFAULT_MODE
        result_count = top_k or config.SEARCH.TOP_K

        # Perform retrieval
        results = sdk_client.retrievals.retrieve(
            query=query,
            mode=search_mode,
            collection_id=collection_id,
            top_k=result_count,
            enable_graph=config.SEARCH.ENABLE_GRAPH,
            rerank=config.SEARCH.RERANK
        )

        # Format results
        return {
            "query": results.query,
            "mode": results.mode,
            "total_results": results.total_results,
            "graph_enhanced": results.graph_enhanced,
            "results": [
                {
                    "content": r.content,
                    "score": r.score,
                    "document": {
                        "id": str(r.document.id),
                        "title": r.document.title,
                        "filename": r.document.filename
                    },
                    "metadata": r.metadata
                }
                for r in results.results
            ]
        }

    except MnemosyneError as e:
        return {"error": str(e), "type": type(e).__name__}
    except Exception as e:
        return {"error": str(e)}


def get_sdk_client():
    """Get the SDK client instance"""
    return sdk_client


def reinitialize_client(api_key: str = None):
    """Reinitialize SDK client with new API key"""
    global sdk_client
    try:
        sdk_client = Client(
            api_key=api_key or config.SDK.API_KEY,
            base_url=config.SDK.BASE_URL,
            timeout=config.SDK.TIMEOUT,
            max_retries=config.SDK.MAX_RETRIES
        )
        return True
    except Exception as e:
        print(f"Failed to reinitialize client: {e}")
        return False
