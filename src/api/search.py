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


def _extract_rich_metadata(retrieval_results, query: str) -> dict:
    """
    Extract rich metadata from retrieval results for frontend display.

    Extracts:
    - Images from document metadata
    - Source documents with titles and URLs
    - Follow-up questions based on query
    - Confidence score

    Args:
        retrieval_results: SDK RetrievalResponse object
        query: Original query string

    Returns:
        Dict with images, sources, follow-ups, and metadata
    """
    images = []
    sources = []
    seen_docs = set()

    # Extract images and sources from chunks
    for result in retrieval_results.results:
        # Extract images from metadata
        if result.metadata:
            # Check various metadata fields for images
            if 'images' in result.metadata and result.metadata['images']:
                img_list = result.metadata['images']
                if isinstance(img_list, list):
                    images.extend(img_list)
                elif isinstance(img_list, str):
                    images.append(img_list)

            if 'image_url' in result.metadata and result.metadata['image_url']:
                images.append(result.metadata['image_url'])

            if 'thumbnail' in result.metadata and result.metadata['thumbnail']:
                images.append(result.metadata['thumbnail'])

        # Extract unique source documents
        doc_id = str(result.document.id)
        if doc_id not in seen_docs:
            seen_docs.add(doc_id)

            # Build source URL (use filename or metadata URL)
            source_url = f"/api/documents/{doc_id}"
            if result.metadata and 'source_url' in result.metadata:
                source_url = result.metadata['source_url']

            sources.append({
                'title': result.document.title or result.document.filename,
                'url': source_url,
                'filename': result.document.filename,
                'relevance': round(result.score, 3) if result.score else 0.0,
                'snippet': result.content[:200] + '...' if len(result.content) > 200 else result.content
            })

    # Remove duplicate images
    images = list(dict.fromkeys(images))[:10]  # Max 10 images

    # Limit sources to top 5
    sources = sources[:5]

    # Generate follow-up questions
    follow_ups = _generate_follow_up_questions(query, retrieval_results.mode)

    # Calculate confidence based on scores
    confidence = _calculate_confidence(retrieval_results.results)

    return {
        'images': images,
        'sources': sources,
        'followUps': follow_ups,
        'confidence': confidence,
        'mode': retrieval_results.mode,
        'total_results': retrieval_results.total_results,
        'graph_enhanced': retrieval_results.graph_enhanced
    }


def _generate_follow_up_questions(query: str, mode: str) -> list:
    """
    Generate relevant follow-up questions based on the query.

    Args:
        query: Original query
        mode: Search mode used

    Returns:
        List of follow-up question strings
    """
    # Smart follow-up generation based on query keywords
    query_lower = query.lower()

    follow_ups = []

    # Generic follow-ups
    if 'what' in query_lower:
        follow_ups.append(f"Can you provide examples related to {query.split()[-1]}?")
        follow_ups.append("How does this work in practice?")
    elif 'how' in query_lower:
        follow_ups.append("What are the key steps involved?")
        follow_ups.append("Are there any alternative approaches?")
    elif 'why' in query_lower:
        follow_ups.append("What are the benefits of this approach?")
        follow_ups.append("Are there any drawbacks?")
    else:
        follow_ups.append("Can you explain this in more detail?")
        follow_ups.append("What are the key takeaways?")

    # Add mode-specific follow-ups
    if mode == 'graph':
        follow_ups.append("How do these concepts relate to each other?")
    elif mode == 'semantic':
        follow_ups.append("Are there similar concepts in the documents?")

    # Always add comparison and summary options
    if len(follow_ups) < 3:
        follow_ups.append("Can you summarize the main points?")

    return follow_ups[:3]  # Return max 3 follow-ups


def _calculate_confidence(results: list) -> float:
    """
    Calculate confidence score based on retrieval scores.

    Args:
        results: List of ChunkResult objects

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not results:
        return 0.0

    # Average the top 3 scores
    top_scores = [r.score for r in results[:3] if r.score is not None]

    if not top_scores:
        return 0.5  # Default medium confidence

    avg_score = sum(top_scores) / len(top_scores)

    # Normalize to 0-1 range (assuming scores are similarity scores)
    confidence = min(1.0, max(0.0, avg_score))

    return round(confidence, 2)


async def stream_response(query: str, collection_id: str = None,
                         session_id: str = None, mode: str = None) -> AsyncGenerator[str, None]:
    """
    Generate streaming chat response with rich metadata using Mnemosyne SDK.

    This function showcases the full SDK capabilities by:
    1. Retrieving rich metadata (images, sources, context)
    2. Streaming LLM-generated chat response
    3. Sending structured JSON with images, sources, and follow-ups

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

        # STEP 1: Get retrieval results with rich metadata
        retrieval_results = sdk_client.retrievals.retrieve(
            query=query,
            mode=search_mode,
            collection_id=collection_id,
            top_k=config.SEARCH.TOP_K,
            enable_graph=config.SEARCH.ENABLE_GRAPH,
            rerank=config.SEARCH.RERANK
        )

        # STEP 2: Stream chat response from SDK
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

        # STEP 3: Extract and send rich metadata
        metadata = _extract_rich_metadata(retrieval_results, query)
        yield f'data: {json.dumps(metadata)}\n\n'

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
