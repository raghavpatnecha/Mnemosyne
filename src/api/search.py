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


def _generate_metadata_from_sources(sources: list, query: str) -> dict:
    """
    Generate metadata from SourceReference objects returned by chat stream.

    Args:
        sources: List of SourceReference objects from chat stream
        query: Original query string

    Returns:
        Dict with sources, follow-ups, and confidence for frontend display
    """
    # Build source list for frontend
    formatted_sources = []
    seen_docs = set()

    for source in sources:
        doc_id = str(source.document_id) if source.document_id else ""
        if doc_id and doc_id not in seen_docs:
            seen_docs.add(doc_id)
            formatted_sources.append({
                'title': source.title or source.filename or "Unknown",
                'url': f"/api/documents/{doc_id}",
                'filename': source.filename,
                'relevance': round(source.score, 3) if source.score else 0.0
            })

    # Limit to top 5 sources
    formatted_sources = formatted_sources[:5]

    # Generate follow-up questions (mode unknown, use generic)
    follow_ups = _generate_follow_up_questions(query, "hybrid")

    # Calculate confidence from source scores
    confidence = _calculate_confidence_from_scores(sources)

    return {
        'images': [],  # Images not available in SourceReference
        'sources': formatted_sources,
        'followUps': follow_ups,
        'confidence': confidence,
        'mode': 'hybrid',  # Backend uses hybrid by default
        'total_results': len(sources),
        'graph_enhanced': True  # Backend enables graph by default
    }


def _calculate_confidence_from_scores(sources: list) -> float:
    """
    Calculate confidence score from SourceReference scores.

    Args:
        sources: List of SourceReference objects

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not sources:
        return 0.0

    # Average the top 3 scores
    top_scores = [s.score for s in sources[:3] if s.score is not None]

    if not top_scores:
        return 0.5  # Default medium confidence

    avg_score = sum(top_scores) / len(top_scores)

    # Normalize to 0-1 range
    confidence = min(1.0, max(0.0, avg_score))

    return round(confidence, 2)


def _extract_rich_metadata(retrieval_results, query: str) -> dict:
    """
    Extract rich metadata from retrieval results for frontend display.

    NOTE: This function is kept for backward compatibility with search_documents().
    The stream_response() function now uses _generate_metadata_from_sources() instead.

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


async def stream_response(
    query: str,
    collection_id: str = None,
    session_id: str = None,
    mode: str = None,
    preset: str = None,
    reasoning_mode: str = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    custom_instruction: str = None,
    is_follow_up: bool = False
) -> AsyncGenerator[str, None]:
    """
    Generate streaming chat response using Mnemosyne SDK.

    The chat endpoint already performs retrieval internally with optimal defaults
    (hybrid mode, rerank=True, enable_graph=True, hierarchical=True, expand_context=True).
    Sources are streamed as part of the chat response.

    Args:
        query: Search query
        collection_id: Optional collection ID to filter results
        session_id: Optional session ID for multi-turn conversations
        mode: Search mode (hybrid, semantic, keyword, hierarchical, graph) - unused, backend uses optimal defaults
        preset: Answer style preset (concise, detailed, research, technical, creative, qna)
        reasoning_mode: Reasoning mode (standard, deep)
        model: LLM model to use (any LiteLLM-compatible model)
        temperature: Override temperature (0.0-1.0)
        max_tokens: Override max tokens for response
        custom_instruction: Custom instruction for additional guidance
        is_follow_up: Whether this is a follow-up question
    """
    if not sdk_client or not config.SDK.API_KEY:
        yield 'data: {"error": "SDK not configured. Please set MNEMOSYNE_API_KEY"}\n\n'
        return

    try:
        # Use config defaults if not specified
        chat_preset = preset or config.CHAT.PRESET
        chat_reasoning = reasoning_mode or config.CHAT.REASONING_MODE
        chat_model = model or config.CHAT.MODEL or None  # Empty string -> None
        chat_temperature = temperature if temperature is not None else config.CHAT.TEMPERATURE
        chat_max_tokens = max_tokens if max_tokens is not None else config.CHAT.MAX_TOKENS

        # Collect sources from the stream for metadata generation
        collected_sources = []

        # Stream chat response from SDK - backend handles retrieval with optimal defaults
        for chunk in sdk_client.chat.chat(
            message=query,
            collection_id=collection_id,
            session_id=session_id,
            stream=True,
            preset=chat_preset,
            reasoning_mode=chat_reasoning,
            model=chat_model,
            temperature=chat_temperature,
            max_tokens=chat_max_tokens,
            custom_instruction=custom_instruction,
            is_follow_up=is_follow_up
        ):
            # Handle StreamChunk objects from SDK
            if chunk.type == "delta" and chunk.content:
                yield f'data: {chunk.content}\n\n'
                await asyncio.sleep(0.01)  # Small delay for smooth streaming
            elif chunk.type == "reasoning_step":
                # Deep reasoning mode: send reasoning step info
                step_data = {
                    "type": "reasoning_step",
                    "step": chunk.step,
                    "description": chunk.description
                }
                yield f'data: {json.dumps(step_data)}\n\n'
            elif chunk.type == "sub_query":
                # Deep reasoning mode: send sub-query info
                sub_query_data = {
                    "type": "sub_query",
                    "query": chunk.query
                }
                yield f'data: {json.dumps(sub_query_data)}\n\n'
            elif chunk.type == "sources" and chunk.sources:
                # Collect sources for metadata generation
                collected_sources = chunk.sources
                # Also send sources to frontend
                sources_data = [
                    {
                        "document_id": s.document_id,
                        "title": s.title,
                        "filename": s.filename,
                        "chunk_index": s.chunk_index,
                        "score": s.score
                    }
                    for s in chunk.sources
                ]
                yield f'data: {json.dumps({"sources": sources_data})}\n\n'

        # Generate metadata from collected sources
        metadata = _generate_metadata_from_sources(collected_sources, query)
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
        key = api_key or config.SDK.API_KEY
        print(f"Reinitializing SDK client with key: {key[:10] if key else 'None'}...")
        print(f"  Base URL: {config.SDK.BASE_URL}")
        print(f"  Timeout: {config.SDK.TIMEOUT}s")

        sdk_client = Client(
            api_key=key,
            base_url=config.SDK.BASE_URL,
            timeout=config.SDK.TIMEOUT,
            max_retries=config.SDK.MAX_RETRIES
        )
        print(f"SDK client reinitialized successfully")
        return True
    except Exception as e:
        print(f"Failed to reinitialize client: {type(e).__name__}: {e}")
        return False
