"""
Image ingestion example for PNG, JPG, JPEG, and WEBP files.

This example demonstrates:
- Ingesting images using GPT-4 Vision for description extraction
- Processing diagrams, charts, screenshots, and photos
- Monitoring image analysis status
- Searching visual content descriptions
- Metadata tagging for images
"""

import time
from mnemosyne import Client
from uuid import UUID

# Initialize client
client = Client(api_key="your_api_key_here")


def ingest_technical_diagrams():
    """Ingest technical diagrams and architecture images"""

    print("=" * 60)
    print("TECHNICAL DIAGRAMS INGESTION")
    print("=" * 60)

    # Create collection for technical diagrams
    collection = client.collections.create(
        name="System Architecture Diagrams",
        description="Technical diagrams and architecture visualizations",
        metadata={"content_type": "image", "category": "technical"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Image files to upload
    diagram_files = [
        {
            "file": "diagrams/rag_architecture.png",
            "metadata": {
                "title": "RAG System Architecture",
                "diagram_type": "system_architecture",
                "components": ["LLM", "Vector DB", "Embedder"],
                "created_date": "2024-01-15",
            },
        },
        {
            "file": "diagrams/data_flow.png",
            "metadata": {
                "title": "Data Flow Diagram",
                "diagram_type": "flowchart",
                "process": "document_ingestion",
                "created_date": "2024-01-20",
            },
        },
        {
            "file": "diagrams/database_schema.png",
            "metadata": {
                "title": "Database Schema",
                "diagram_type": "entity_relationship",
                "database": "PostgreSQL",
                "created_date": "2024-01-25",
            },
        },
    ]

    print("Uploading diagram images...")
    uploaded_images = []
    for img in diagram_files:
        try:
            # SDK detects image MIME type and uses GPT-4 Vision
            doc = client.documents.create(
                collection_id=collection.id,
                file=img["file"],
                metadata=img["metadata"],
            )
            uploaded_images.append(doc)
            print(f"✓ Queued: {img['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {img['file']} (skipping)")
        except Exception as e:
            print(f"✗ Failed to upload: {e}")

    print()

    # Monitor processing progress
    print("Monitoring image analysis progress...")
    for doc in uploaded_images:
        while True:
            status = client.documents.get_status(doc.id)

            if status.status == "completed":
                print(f"✓ Analysis complete: {doc.id}")
                print(f"  Chunks: {status.chunk_count}")
                print(f"  Tokens: {status.total_tokens}")
                break
            elif status.status == "failed":
                print(f"✗ Analysis failed: {status.error_message}")
                break
            else:
                print(f"⏳ Processing... ({status.status})")
                time.sleep(5)

    return collection.id


def ingest_screenshots():
    """Ingest application screenshots"""

    print("\n" + "=" * 60)
    print("SCREENSHOTS INGESTION")
    print("=" * 60)

    # Create collection for screenshots
    collection = client.collections.create(
        name="UI Screenshots",
        description="Application interface screenshots and mockups",
        metadata={"content_type": "image", "category": "ui_ux"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Screenshot files
    screenshot_files = [
        {
            "file": "screenshots/dashboard.png",
            "metadata": {
                "title": "Main Dashboard",
                "screen_type": "dashboard",
                "app_version": "v2.1.0",
                "resolution": "1920x1080",
            },
        },
        {
            "file": "screenshots/settings_page.jpg",
            "metadata": {
                "title": "Settings Panel",
                "screen_type": "settings",
                "app_version": "v2.1.0",
                "resolution": "1920x1080",
            },
        },
        {
            "file": "screenshots/user_profile.webp",
            "metadata": {
                "title": "User Profile Page",
                "screen_type": "profile",
                "app_version": "v2.1.0",
                "features": ["avatar", "bio", "activity_feed"],
            },
        },
    ]

    print("Uploading screenshot images...")
    for img in screenshot_files:
        try:
            doc = client.documents.create(
                collection_id=collection.id,
                file=img["file"],
                metadata=img["metadata"],
            )
            print(f"✓ Uploaded: {img['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {img['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")

    return collection.id


def ingest_charts_and_graphs():
    """Ingest data visualization images"""

    print("\n" + "=" * 60)
    print("CHARTS AND GRAPHS INGESTION")
    print("=" * 60)

    # Create collection for data visualizations
    collection = client.collections.create(
        name="Data Visualizations",
        description="Charts, graphs, and data analysis visualizations",
        metadata={"content_type": "image", "category": "data_viz"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Chart images
    chart_files = [
        {
            "file": "charts/performance_metrics.png",
            "metadata": {
                "title": "System Performance Metrics",
                "chart_type": "line_chart",
                "metrics": ["latency", "throughput", "error_rate"],
                "time_period": "2024-Q1",
            },
        },
        {
            "file": "charts/user_growth.png",
            "metadata": {
                "title": "User Growth Analysis",
                "chart_type": "bar_chart",
                "metrics": ["active_users", "new_signups", "churn_rate"],
                "time_period": "2024-Q1",
            },
        },
        {
            "file": "charts/cost_breakdown.png",
            "metadata": {
                "title": "Infrastructure Cost Breakdown",
                "chart_type": "pie_chart",
                "categories": ["compute", "storage", "network", "other"],
                "time_period": "2024-01",
            },
        },
    ]

    print("Uploading chart images...")
    for img in chart_files:
        try:
            doc = client.documents.create(
                collection_id=collection.id,
                file=img["file"],
                metadata=img["metadata"],
            )
            print(f"✓ Uploaded: {img['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {img['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")

    return collection.id


def search_image_content(collection_id: UUID):
    """Search analyzed image descriptions"""

    print("\n" + "=" * 60)
    print("SEARCHING IMAGE DESCRIPTIONS")
    print("=" * 60)

    queries = [
        "What components are shown in the system architecture?",
        "Describe the database schema structure",
        "What UI elements are visible in the dashboard?",
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
            print(f"     Image: {result.document.title or result.document.filename}")
            print(f"     Type: {result.document.metadata.get('diagram_type', 'N/A')}")
            print(f"     Description: {result.content[:150]}...")


def main():
    """Run image ingestion examples"""

    print("\nMnemosyne Image Ingestion Example\n")
    print("Supported formats: PNG, JPG, JPEG, WEBP")
    print("Uses GPT-4 Vision for image analysis\n")

    # Example 1: Technical diagrams
    diagrams_collection_id = ingest_technical_diagrams()

    # Example 2: Screenshots
    screenshots_collection_id = ingest_screenshots()

    # Example 3: Charts and graphs
    charts_collection_id = ingest_charts_and_graphs()

    # Example 4: Search image descriptions
    search_image_content(diagrams_collection_id)

    print("\n" + "=" * 60)
    print("IMAGE INGESTION COMPLETE!")
    print("=" * 60)
    print(f"\nDiagrams Collection ID: {diagrams_collection_id}")
    print(f"Screenshots Collection ID: {screenshots_collection_id}")
    print(f"Charts Collection ID: {charts_collection_id}")
    print("\nAll images have been analyzed and are searchable!")
    print("\nNote: Images are analyzed using GPT-4 Vision to extract:")
    print("  - Visual descriptions")
    print("  - Text content (OCR)")
    print("  - Structural elements")
    print("  - Key features and components")


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
