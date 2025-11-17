"""
Video ingestion example for YouTube URLs and MP4 files.

This example demonstrates:
- Ingesting YouTube videos (automatic transcription)
- Ingesting local MP4 files
- Monitoring video processing status
- Searching transcribed video content
"""

import time
from mnemosyne import Client
from uuid import UUID

# Initialize client
client = Client(api_key="your_api_key_here")


def ingest_youtube_video():
    """Ingest a YouTube video"""

    print("=" * 60)
    print("YOUTUBE VIDEO INGESTION")
    print("=" * 60)

    # Create collection for video content
    collection = client.collections.create(
        name="AI Lectures",
        description="Transcribed AI/ML lecture videos",
        metadata={"content_type": "video", "source": "youtube"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # YouTube URL examples
    youtube_urls = [
        {
            "url": "https://www.youtube.com/watch?v=example1",
            "metadata": {
                "title": "Attention is All You Need - Paper Explained",
                "speaker": "Yannic Kilcher",
                "duration_minutes": 45,
            },
        },
        {
            "url": "https://www.youtube.com/watch?v=example2",
            "metadata": {
                "title": "RAG Systems Tutorial",
                "speaker": "Andrew Ng",
                "duration_minutes": 60,
            },
        },
    ]

    print("Uploading YouTube videos...")
    uploaded_videos = []
    for video in youtube_urls:
        try:
            # SDK detects YouTube URL and handles appropriately
            doc = client.documents.create(
                collection_id=collection.id,
                file=video["url"],
                metadata=video["metadata"],
            )
            uploaded_videos.append(doc)
            print(f"✓ Queued: {video['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except Exception as e:
            print(f"✗ Failed to upload: {e}")

    print()

    # Monitor transcription progress
    print("Monitoring transcription progress...")
    for doc in uploaded_videos:
        while True:
            status = client.documents.get_status(doc.id)

            if status.status == "completed":
                print(f"✓ Transcription complete: {doc.id}")
                print(f"  Chunks: {status.chunk_count}")
                print(f"  Tokens: {status.total_tokens}")
                break
            elif status.status == "failed":
                print(f"✗ Transcription failed: {status.error_message}")
                break
            else:
                print(f"⏳ Processing... ({status.status})")
                time.sleep(5)

    return collection.id


def ingest_mp4_file():
    """Ingest a local MP4 file"""

    print("\n" + "=" * 60)
    print("LOCAL MP4 FILE INGESTION")
    print("=" * 60)

    # Create collection
    collection = client.collections.create(
        name="Meeting Recordings",
        description="Transcribed internal meeting videos",
        metadata={"content_type": "video", "source": "local"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Upload MP4 files
    mp4_files = [
        {
            "file": "videos/team_meeting_2024_01.mp4",
            "metadata": {
                "meeting_type": "standup",
                "date": "2024-01-15",
                "participants": ["Alice", "Bob", "Charlie"],
            },
        },
        {
            "file": "videos/product_demo.mp4",
            "metadata": {
                "meeting_type": "demo",
                "date": "2024-01-20",
                "product": "RAG System v2",
            },
        },
    ]

    print("Uploading MP4 files...")
    for video_info in mp4_files:
        try:
            doc = client.documents.create(
                collection_id=collection.id,
                file=video_info["file"],
                metadata=video_info["metadata"],
            )
            print(f"✓ Uploaded: {video_info['file']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {video_info['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")

    return collection.id


def search_video_content(collection_id: UUID):
    """Search transcribed video content"""

    print("\n" + "=" * 60)
    print("SEARCHING VIDEO TRANSCRIPTIONS")
    print("=" * 60)

    query = "What were the main discussion points about the RAG architecture?"

    results = client.retrievals.retrieve(
        query=query,
        mode="hybrid",
        top_k=5,
        collection_id=collection_id,
    )

    print(f"\nQuery: {query}")
    print(f"Found {len(results.results)} results\n")

    for i, result in enumerate(results.results, 1):
        print(f"{i}. Score: {result.score:.4f}")
        print(f"   Video: {result.document.title or result.document.filename}")
        print(f"   Metadata: {result.document.metadata}")
        print(f"   Transcript: {result.content[:200]}...")
        print()


def main():
    """Run video ingestion examples"""

    print("\nMnemosyne Video Ingestion Example\n")

    # Example 1: YouTube videos
    youtube_collection_id = ingest_youtube_video()

    # Example 2: Local MP4 files
    mp4_collection_id = ingest_mp4_file()

    # Example 3: Search video content
    search_video_content(youtube_collection_id)

    print("\n" + "=" * 60)
    print("VIDEO INGESTION COMPLETE!")
    print("=" * 60)
    print(f"\nYouTube Collection ID: {youtube_collection_id}")
    print(f"MP4 Collection ID: {mp4_collection_id}")
    print("\nAll videos have been transcribed and are searchable!")


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
