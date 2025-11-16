"""
Basic retrieval example demonstrating all 5 search modes.

This example shows how to:
- Perform semantic search (embeddings)
- Perform keyword search (BM25)
- Perform hybrid search (combining both)
- Perform hierarchical search (multi-level)
- Perform graph search (LightRAG)
"""

from mnemosyne import Client
from uuid import UUID

# Initialize client
client = Client(api_key="your_api_key_here")

# Your collection ID (from ingestion)
COLLECTION_ID = UUID("your-collection-id-here")


def print_results(results, mode):
    """Pretty print search results"""
    print(f"\n{'=' * 60}")
    print(f"MODE: {mode.upper()}")
    print(f"{'=' * 60}")
    print(f"Found {len(results.results)} results in {results.processing_time_ms:.2f}ms\n")

    for i, result in enumerate(results.results, 1):
        print(f"{i}. Score: {result.score:.4f}")
        print(f"   Document: {result.document.title or result.document.filename}")
        print(f"   Chunk {result.chunk_index}: {result.content[:150]}...")
        print()


def main():
    """Run retrieval examples for all modes"""

    query = "What are the key innovations in transformer architecture?"

    # 1. Semantic Search (Default)
    print("1. SEMANTIC SEARCH (Embedding-based)")
    print("   Best for: Conceptual similarity, meaning-based retrieval")
    semantic_results = client.retrievals.retrieve(
        query=query,
        mode="semantic",
        top_k=5,
        collection_id=COLLECTION_ID,
    )
    print_results(semantic_results, "semantic")

    # 2. Keyword Search (BM25)
    print("\n2. KEYWORD SEARCH (BM25)")
    print("   Best for: Exact term matching, technical jargon")
    keyword_results = client.retrievals.retrieve(
        query=query,
        mode="keyword",
        top_k=5,
        collection_id=COLLECTION_ID,
    )
    print_results(keyword_results, "keyword")

    # 3. Hybrid Search (Combines both)
    print("\n3. HYBRID SEARCH (Semantic + Keyword)")
    print("   Best for: Balanced results, production use")
    hybrid_results = client.retrievals.retrieve(
        query=query,
        mode="hybrid",
        top_k=5,
        collection_id=COLLECTION_ID,
    )
    print_results(hybrid_results, "hybrid")

    # 4. Hierarchical Search (Multi-level)
    print("\n4. HIERARCHICAL SEARCH (Multi-level)")
    print("   Best for: Long documents, structured content")
    hierarchical_results = client.retrievals.retrieve(
        query=query,
        mode="hierarchical",
        top_k=5,
        collection_id=COLLECTION_ID,
    )
    print_results(hierarchical_results, "hierarchical")

    # 5. Graph Search (LightRAG)
    print("\n5. GRAPH SEARCH (LightRAG)")
    print("   Best for: Complex reasoning, entity relationships")
    graph_results = client.retrievals.retrieve(
        query=query,
        mode="graph",
        top_k=5,
        collection_id=COLLECTION_ID,
    )
    print_results(graph_results, "graph")

    # Filter by metadata
    print("\n6. METADATA FILTERING")
    print("   Filter results by document metadata")
    filtered_results = client.retrievals.retrieve(
        query=query,
        mode="hybrid",
        top_k=5,
        collection_id=COLLECTION_ID,
        metadata_filter={"year": 2023},  # Only 2023 papers
    )
    print_results(filtered_results, "hybrid + metadata filter")


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
