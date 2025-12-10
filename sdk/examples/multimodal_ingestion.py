"""
Comprehensive multimodal ingestion example.

This example demonstrates:
- Ingesting multiple file types in a single collection
- Processing documents, images, audio, video, and Excel files together
- Building a unified knowledge base from diverse content
- Cross-modal search and retrieval
"""

import time
from mnemosyne import Client
from uuid import UUID

# Initialize client
client = Client(api_key="your_api_key_here")


def create_multimodal_collection():
    """Create a collection that will contain multiple file types"""

    print("=" * 60)
    print("MULTIMODAL COLLECTION CREATION")
    print("=" * 60)

    collection = client.collections.create(
        name="AI Research Knowledge Base",
        description="Comprehensive collection of papers, diagrams, lectures, and data",
        metadata={
            "content_types": ["pdf", "image", "audio", "video", "excel"],
            "domain": "artificial_intelligence",
            "purpose": "research_repository",
        },
    )

    print(f"✓ Created multimodal collection: {collection.id}\n")
    return collection


def ingest_diverse_content(collection_id: UUID):
    """Upload various file types to the same collection"""

    print("=" * 60)
    print("INGESTING DIVERSE CONTENT TYPES")
    print("=" * 60)

    # Diverse files across different modalities
    files_to_upload = [
        # Documents (PDF, DOCX, TXT, PPTX)
        {
            "file": "papers/attention_is_all_you_need.pdf",
            "metadata": {
                "title": "Attention Is All You Need",
                "type": "research_paper",
                "authors": ["Vaswani et al."],
                "year": 2017,
                "topic": "transformers",
            },
        },
        {
            "file": "presentations/rag_overview.pptx",
            "metadata": {
                "title": "RAG Systems Overview",
                "type": "presentation",
                "slides": 25,
                "topic": "rag_architecture",
            },
        },
        # Images (PNG, JPG, WEBP)
        {
            "file": "diagrams/transformer_architecture.png",
            "metadata": {
                "title": "Transformer Architecture Diagram",
                "type": "technical_diagram",
                "topic": "transformers",
                "format": "png",
            },
        },
        {
            "file": "charts/model_performance_comparison.jpg",
            "metadata": {
                "title": "Model Performance Comparison",
                "type": "chart",
                "topic": "benchmarks",
                "format": "jpg",
            },
        },
        # Audio (MP3, WAV, M4A, FLAC)
        {
            "file": "podcasts/rag_systems_interview.mp3",
            "metadata": {
                "title": "RAG Systems: An Expert Interview",
                "type": "podcast",
                "duration_minutes": 45,
                "topic": "rag_systems",
            },
        },
        {
            "file": "lectures/transformer_lecture.wav",
            "metadata": {
                "title": "Transformer Models Lecture",
                "type": "lecture",
                "professor": "Andrew Ng",
                "duration_minutes": 75,
                "topic": "transformers",
            },
        },
        # Video (YouTube, MP4)
        {
            "file": "https://www.youtube.com/watch?v=example_video",
            "metadata": {
                "title": "Attention Mechanism Explained",
                "type": "youtube_video",
                "channel": "AI Explained",
                "duration_minutes": 20,
                "topic": "attention",
            },
        },
        {
            "file": "videos/rag_demo.mp4",
            "metadata": {
                "title": "RAG System Demo",
                "type": "demo_video",
                "duration_minutes": 15,
                "topic": "rag_demo",
            },
        },
        # Excel (XLSX, XLS)
        {
            "file": "data/model_benchmarks.xlsx",
            "metadata": {
                "title": "Model Performance Benchmarks",
                "type": "data_table",
                "metrics": ["accuracy", "latency", "cost"],
                "topic": "benchmarks",
            },
        },
        {
            "file": "data/training_costs.xlsx",
            "metadata": {
                "title": "Model Training Cost Analysis",
                "type": "financial_data",
                "year": 2024,
                "topic": "ml_costs",
            },
        },
    ]

    print(f"Uploading {len(files_to_upload)} files of various types...\n")

    uploaded_docs = []
    for file_info in files_to_upload:
        try:
            doc = client.documents.create(
                collection_id=collection_id,
                file=file_info["file"],
                metadata=file_info["metadata"],
            )
            uploaded_docs.append(doc)
            file_type = file_info["metadata"]["type"]
            print(f"✓ Queued ({file_type}): {file_info['metadata']['title']}")
        except FileNotFoundError:
            print(f"✗ File not found: {file_info['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed for {file_info['file']}: {e}")

    return uploaded_docs


def monitor_processing(uploaded_docs):
    """Monitor processing status for all uploaded files"""

    print("\n" + "=" * 60)
    print("MONITORING MULTIMODAL PROCESSING")
    print("=" * 60)

    print(f"\nTracking {len(uploaded_docs)} documents...\n")

    processing_complete = set()
    processing_failed = set()

    while len(processing_complete) + len(processing_failed) < len(uploaded_docs):
        for doc in uploaded_docs:
            doc_id_str = str(doc.id)

            # Skip if already processed
            if doc_id_str in processing_complete or doc_id_str in processing_failed:
                continue

            try:
                status = client.documents.get_status(doc.id)

                if status.status == "completed":
                    processing_complete.add(doc_id_str)
                    print(f"✓ Completed: {doc_id_str[:8]}...")
                    print(f"  Chunks: {status.chunk_count}, Tokens: {status.total_tokens}")
                elif status.status == "failed":
                    processing_failed.add(doc_id_str)
                    print(f"✗ Failed: {doc_id_str[:8]}... - {status.error_message}")
                else:
                    print(f"⏳ Processing: {doc_id_str[:8]}... ({status.status})")

            except Exception as e:
                print(f"⚠ Error checking status for {doc_id_str[:8]}...: {e}")

        # Wait before next check
        if len(processing_complete) + len(processing_failed) < len(uploaded_docs):
            time.sleep(5)

    print(f"\n✓ Processing complete:")
    print(f"  Success: {len(processing_complete)}")
    print(f"  Failed: {len(processing_failed)}")


def cross_modal_search(collection_id: UUID):
    """Demonstrate searching across different modalities"""

    print("\n" + "=" * 60)
    print("CROSS-MODAL SEARCH")
    print("=" * 60)

    # Queries that could match content from different modalities
    queries = [
        {
            "query": "Explain the transformer architecture",
            "description": "Should find: papers, diagrams, videos, lectures",
        },
        {
            "query": "What are the performance metrics of different models?",
            "description": "Should find: benchmarks table, charts, analysis",
        },
        {
            "query": "How do RAG systems work?",
            "description": "Should find: papers, presentations, videos, podcasts",
        },
    ]

    for q in queries:
        print(f"\n{'='*60}")
        print(f"Query: {q['query']}")
        print(f"Expected: {q['description']}")
        print(f"{'='*60}")

        results = client.retrievals.retrieve(
            query=q["query"],
            mode="hybrid",
            top_k=5,
            collection_id=collection_id,
        )

        print(f"\nFound {len(results.results)} results across modalities:\n")

        for i, result in enumerate(results.results, 1):
            content_type = result.document.metadata.get("type", "unknown")
            topic = result.document.metadata.get("topic", "N/A")

            print(f"{i}. [{content_type}] {result.document.title or result.document.filename}")
            print(f"   Score: {result.score:.4f} | Topic: {topic}")
            print(f"   Preview: {result.content[:150]}...")
            print()


def analyze_collection_stats(collection_id: UUID):
    """Analyze the multimodal collection statistics"""

    print("\n" + "=" * 60)
    print("COLLECTION STATISTICS")
    print("=" * 60)

    # Get all documents in collection
    docs = client.documents.list(collection_id=collection_id)

    # Count by content type
    type_counts = {}
    total_chunks = 0
    total_tokens = 0

    for doc in docs:
        content_type = doc.metadata.get("type", "unknown")
        type_counts[content_type] = type_counts.get(content_type, 0) + 1

        # Get detailed status
        try:
            status = client.documents.get_status(doc.id)
            if status.status == "completed":
                total_chunks += status.chunk_count or 0
                total_tokens += status.total_tokens or 0
        except:
            pass

    print(f"\nCollection: {collection_id}")
    print(f"Total Documents: {len(docs)}")
    print(f"Total Chunks: {total_chunks}")
    print(f"Total Tokens: {total_tokens:,}\n")

    print("Content Types:")
    for content_type, count in sorted(type_counts.items()):
        print(f"  - {content_type}: {count}")


def main():
    """Run comprehensive multimodal ingestion example"""

    print("\n" + "=" * 70)
    print("MNEMOSYNE MULTIMODAL INGESTION EXAMPLE")
    print("=" * 70)
    print("\nThis example demonstrates:")
    print("  ✓ Ingesting multiple file types in one collection")
    print("  ✓ Processing documents, images, audio, video, and Excel")
    print("  ✓ Cross-modal semantic search")
    print("  ✓ Building unified knowledge bases\n")

    # Step 1: Create collection
    collection = create_multimodal_collection()

    # Step 2: Upload diverse content
    uploaded_docs = ingest_diverse_content(collection.id)

    # Step 3: Monitor processing
    monitor_processing(uploaded_docs)

    # Step 4: Cross-modal search
    cross_modal_search(collection.id)

    # Step 5: Analyze statistics
    analyze_collection_stats(collection.id)

    print("\n" + "=" * 70)
    print("MULTIMODAL INGESTION COMPLETE!")
    print("=" * 70)
    print(f"\nCollection ID: {collection.id}")
    print("\nSupported file types:")
    print("  📄 Documents: PDF, DOCX, TXT, PPTX (via Docling)")
    print("  🖼️  Images: PNG, JPG, JPEG, WEBP (via GPT-4 Vision)")
    print("  🎵 Audio: MP3, WAV, M4A, FLAC, OGG (via Whisper)")
    print("  🎬 Video: YouTube URLs, MP4 (via Whisper transcription)")
    print("  📊 Excel: XLSX, XLS (converted to markdown tables)")
    print("\nKey benefits of multimodal collections:")
    print("  ✓ Unified search across all content types")
    print("  ✓ Single API for diverse data sources")
    print("  ✓ Consistent metadata and tagging")
    print("  ✓ Cross-modal semantic relationships")
    print("  ✓ Simplified knowledge management")


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
