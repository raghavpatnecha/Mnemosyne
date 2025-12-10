"""
Audio ingestion example for MP3, WAV, M4A, FLAC, and other audio formats.

This example demonstrates:
- Ingesting audio files using LiteLLM/Whisper for transcription
- Processing podcasts, meetings, interviews, and lectures
- Monitoring transcription status
- Searching transcribed audio content
- Metadata tagging for audio files
"""

import time
from mnemosyne import Client
from uuid import UUID

# Initialize client
client = Client(api_key="your_api_key_here")


def ingest_podcast_episodes():
    """Ingest podcast episodes"""

    print("=" * 60)
    print("PODCAST EPISODES INGESTION")
    print("=" * 60)

    # Create collection for podcasts
    collection = client.collections.create(
        name="Tech Podcasts",
        description="Transcribed technology podcast episodes",
        metadata={"content_type": "audio", "category": "podcast"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Podcast audio files
    podcast_files = [
        {
            "file": "podcasts/ai_trends_ep_42.mp3",
            "metadata": {
                "title": "The Future of RAG Systems",
                "podcast_name": "AI Trends",
                "episode_number": 42,
                "host": "Jane Smith",
                "guest": "John Doe",
                "duration_minutes": 45,
                "published_date": "2024-01-15",
                "topics": ["RAG", "Vector Databases", "LLM"],
            },
        },
        {
            "file": "podcasts/deep_learning_weekly_123.mp3",
            "metadata": {
                "title": "Transformer Architecture Deep Dive",
                "podcast_name": "Deep Learning Weekly",
                "episode_number": 123,
                "host": "Alex Chen",
                "guest": "Sarah Johnson",
                "duration_minutes": 60,
                "published_date": "2024-01-22",
                "topics": ["Transformers", "Attention", "NLP"],
            },
        },
    ]

    print("Uploading podcast audio files...")
    uploaded_audio = []
    for audio in podcast_files:
        try:
            # SDK detects audio MIME type and uses Whisper transcription
            doc = client.documents.create(
                collection_id=collection.id,
                file=audio["file"],
                metadata=audio["metadata"],
            )
            uploaded_audio.append(doc)
            print(f"✓ Queued: {audio['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {audio['file']} (skipping)")
        except Exception as e:
            print(f"✗ Failed to upload: {e}")

    print()

    # Monitor transcription progress
    print("Monitoring transcription progress...")
    for doc in uploaded_audio:
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


def ingest_meeting_recordings():
    """Ingest meeting audio recordings"""

    print("\n" + "=" * 60)
    print("MEETING RECORDINGS INGESTION")
    print("=" * 60)

    # Create collection for meetings
    collection = client.collections.create(
        name="Team Meetings",
        description="Transcribed internal meeting recordings",
        metadata={"content_type": "audio", "category": "meetings"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Meeting audio files (various formats)
    meeting_files = [
        {
            "file": "meetings/standup_2024_01_15.wav",
            "metadata": {
                "title": "Daily Standup - Jan 15",
                "meeting_type": "standup",
                "date": "2024-01-15",
                "participants": ["Alice", "Bob", "Charlie"],
                "duration_minutes": 15,
                "department": "Engineering",
            },
        },
        {
            "file": "meetings/product_review.m4a",
            "metadata": {
                "title": "Q1 Product Review",
                "meeting_type": "review",
                "date": "2024-01-20",
                "participants": ["Product Team", "Engineering", "Design"],
                "duration_minutes": 90,
                "topics": ["roadmap", "features", "priorities"],
            },
        },
        {
            "file": "meetings/client_call.flac",
            "metadata": {
                "title": "Client Feedback Session",
                "meeting_type": "client_call",
                "date": "2024-01-25",
                "client": "Acme Corp",
                "duration_minutes": 60,
                "topics": ["feedback", "feature_requests", "issues"],
            },
        },
    ]

    print("Uploading meeting audio files...")
    for audio in meeting_files:
        try:
            doc = client.documents.create(
                collection_id=collection.id,
                file=audio["file"],
                metadata=audio["metadata"],
            )
            print(f"✓ Uploaded: {audio['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {audio['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")

    return collection.id


def ingest_lecture_recordings():
    """Ingest educational lecture recordings"""

    print("\n" + "=" * 60)
    print("LECTURE RECORDINGS INGESTION")
    print("=" * 60)

    # Create collection for lectures
    collection = client.collections.create(
        name="ML Course Lectures",
        description="Transcribed machine learning course lectures",
        metadata={"content_type": "audio", "category": "education"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Lecture audio files
    lecture_files = [
        {
            "file": "lectures/ml_intro_lecture_1.mp3",
            "metadata": {
                "title": "Introduction to Machine Learning",
                "course": "CS229 - Machine Learning",
                "lecture_number": 1,
                "professor": "Andrew Ng",
                "semester": "Fall 2024",
                "duration_minutes": 75,
                "topics": ["supervised_learning", "linear_regression"],
            },
        },
        {
            "file": "lectures/deep_learning_lecture_5.ogg",
            "metadata": {
                "title": "Convolutional Neural Networks",
                "course": "CS231n - Deep Learning for Computer Vision",
                "lecture_number": 5,
                "professor": "Fei-Fei Li",
                "semester": "Fall 2024",
                "duration_minutes": 80,
                "topics": ["CNN", "convolution", "pooling"],
            },
        },
    ]

    print("Uploading lecture audio files...")
    for audio in lecture_files:
        try:
            doc = client.documents.create(
                collection_id=collection.id,
                file=audio["file"],
                metadata=audio["metadata"],
            )
            print(f"✓ Uploaded: {audio['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {audio['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")

    return collection.id


def search_audio_transcriptions(collection_id: UUID):
    """Search transcribed audio content"""

    print("\n" + "=" * 60)
    print("SEARCHING AUDIO TRANSCRIPTIONS")
    print("=" * 60)

    queries = [
        "What were the main discussion points about RAG systems?",
        "Explain the transformer architecture concepts mentioned",
        "What action items were discussed in the meetings?",
    ]

    for query in queries:
        print(f"\n🔍 Query: {query}")

        results = client.retrievals.retrieve(
            query=query,
            mode="hybrid",
            top_k=3,
            collection_id=collection_id,
        )

        print(f"Found {len(results.results)} results:")
        for i, result in enumerate(results.results, 1):
            print(f"\n  {i}. Score: {result.score:.4f}")
            print(f"     Audio: {result.document.title or result.document.filename}")
            print(f"     Metadata: {result.document.metadata}")
            print(f"     Transcript: {result.content[:200]}...")


def main():
    """Run audio ingestion examples"""

    print("\nMnemosyne Audio Ingestion Example\n")
    print("Supported formats: MP3, WAV, M4A, FLAC, OGG, WEBM")
    print("Uses LiteLLM/Whisper for transcription\n")

    # Example 1: Podcast episodes
    podcast_collection_id = ingest_podcast_episodes()

    # Example 2: Meeting recordings
    meeting_collection_id = ingest_meeting_recordings()

    # Example 3: Lecture recordings
    lecture_collection_id = ingest_lecture_recordings()

    # Example 4: Search transcriptions
    search_audio_transcriptions(podcast_collection_id)

    print("\n" + "=" * 60)
    print("AUDIO INGESTION COMPLETE!")
    print("=" * 60)
    print(f"\nPodcast Collection ID: {podcast_collection_id}")
    print(f"Meeting Collection ID: {meeting_collection_id}")
    print(f"Lecture Collection ID: {lecture_collection_id}")
    print("\nAll audio files have been transcribed and are searchable!")
    print("\nNote: Audio transcription uses:")
    print("  - OpenAI Whisper (default)")
    print("  - Azure Whisper")
    print("  - Groq Whisper")
    print("  - Other providers via LiteLLM")
    print("\nTranscription quality:")
    print("  - High accuracy for clear audio")
    print("  - Timestamps preserved")
    print("  - Speaker diarization (when available)")


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
