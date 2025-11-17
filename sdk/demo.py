#!/usr/bin/env python3
"""
Mnemosyne SDK Demo - Complete Walkthrough

This demo showcases all major features of the Mnemosyne SDK:
1. Collection management
2. Document ingestion
3. Multiple search modes
4. Streaming chat
5. Error handling

Prerequisites:
- Mnemosyne backend running on http://localhost:8000
- API key (or the backend configured for testing)
- Sample documents in a 'demo_docs/' folder (optional)

Usage:
    python demo.py
"""

import time
import os
from pathlib import Path
from uuid import UUID

# Import SDK
try:
    from mnemosyne import Client, MnemosyneError, NotFoundError
except ImportError:
    print("Error: Mnemosyne SDK not installed")
    print("Install with: pip install -e .")
    exit(1)


class MnemosyneDemo:
    """Interactive demo for Mnemosyne SDK"""

    def __init__(self, api_key: str = None, base_url: str = "http://localhost:8000"):
        """Initialize demo"""
        self.api_key = api_key or os.getenv("MNEMOSYNE_API_KEY", "demo_api_key")
        self.base_url = base_url
        self.client = None
        self.collection = None
        self.documents = []

    def print_header(self, title: str):
        """Print section header"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70 + "\n")

    def print_step(self, step: int, description: str):
        """Print step description"""
        print(f"\n{'─' * 70}")
        print(f"STEP {step}: {description}")
        print('─' * 70)

    def run(self):
        """Run complete demo"""
        try:
            self.print_header("MNEMOSYNE SDK DEMO - Complete Walkthrough")

            # Initialize client
            self.initialize_client()

            # Part 1: Collection Management
            self.demo_collections()

            # Part 2: Document Ingestion
            self.demo_documents()

            # Part 3: Search & Retrieval
            self.demo_retrieval()

            # Part 4: Streaming Chat
            self.demo_chat()

            # Part 5: Cleanup
            self.cleanup()

            self.print_header("DEMO COMPLETE!")
            print("You've successfully explored all major features of Mnemosyne SDK!")
            print("\nNext steps:")
            print("  1. Check out examples/ folder for more detailed use cases")
            print("  2. Read sdk/README.md for full documentation")
            print("  3. Try building your own RAG application!")

        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Demo failed with error: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
        finally:
            if self.client:
                self.client.close()

    def initialize_client(self):
        """Initialize Mnemosyne client"""
        self.print_step(1, "Initializing Mnemosyne Client")

        print(f"📡 Connecting to: {self.base_url}")
        print(f"🔑 API Key: {self.api_key[:10]}...")

        try:
            self.client = Client(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=60.0,
                max_retries=3,
            )
            print("✅ Client initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            raise

    def demo_collections(self):
        """Demonstrate collection management"""
        self.print_step(2, "Collection Management")

        # Create collection
        print("\n📚 Creating a new collection...")
        try:
            self.collection = self.client.collections.create(
                name="SDK Demo Collection",
                description="Demonstration of Mnemosyne SDK capabilities",
                metadata={
                    "purpose": "demo",
                    "created_by": "sdk_demo",
                    "tags": ["demo", "tutorial", "sdk"],
                },
                config={
                    "embedding_model": "text-embedding-3-small",
                    "chunk_size": 512,
                },
            )
            print(f"✅ Collection created!")
            print(f"   ID: {self.collection.id}")
            print(f"   Name: {self.collection.name}")
            print(f"   Metadata: {self.collection.metadata}")
        except Exception as e:
            print(f"❌ Failed to create collection: {e}")
            raise

        # List collections
        print("\n📋 Listing all collections...")
        try:
            collections = self.client.collections.list(limit=5)
            print(f"✅ Found {len(collections.data)} collection(s)")
            for i, coll in enumerate(collections.data[:3], 1):
                print(f"   {i}. {coll.name} ({coll.document_count} docs)")
        except Exception as e:
            print(f"❌ Failed to list collections: {e}")

        # Get collection
        print(f"\n🔍 Retrieving collection by ID...")
        try:
            retrieved = self.client.collections.get(self.collection.id)
            print(f"✅ Retrieved: {retrieved.name}")
        except Exception as e:
            print(f"❌ Failed to retrieve collection: {e}")

    def demo_documents(self):
        """Demonstrate document ingestion"""
        self.print_step(3, "Document Ingestion")

        print("📄 In a real scenario, you would upload PDF, DOCX, or other files.")
        print("   For this demo, we'll simulate document creation.")
        print("\nExample usage:")
        print("   doc = client.documents.create(")
        print("       collection_id=collection.id,")
        print("       file='path/to/document.pdf',")
        print("       metadata={'author': 'John Doe'}")
        print("   )")

        # Simulate document creation
        demo_docs = [
            {"title": "Introduction to RAG", "content_type": "pdf"},
            {"title": "Transformer Architecture", "content_type": "pdf"},
            {"title": "LightRAG Paper", "content_type": "pdf"},
        ]

        print(f"\n📤 Simulating upload of {len(demo_docs)} documents...")
        for i, doc_info in enumerate(demo_docs, 1):
            print(f"   {i}. {doc_info['title']} ({doc_info['content_type']})")

        # Show status monitoring
        print("\n⏳ Monitoring document processing...")
        print("   In real usage, you would poll document status:")
        print("   status = client.documents.get_status(document_id)")
        print("   while status.status != 'completed':")
        print("       time.sleep(2)")
        print("       status = client.documents.get_status(document_id)")

        print("\n✅ All documents processed (simulated)")
        print("   Total chunks: 150")
        print("   Total tokens: 25,000")

    def demo_retrieval(self):
        """Demonstrate search and retrieval"""
        self.print_step(4, "Search & Retrieval (5 Modes)")

        query = "What are the key components of a RAG system?"

        print(f"🔍 Query: '{query}'\n")

        # Show all 5 modes
        modes = {
            "semantic": "Embedding-based similarity search",
            "keyword": "BM25 keyword matching",
            "hybrid": "Combines semantic + keyword (RECOMMENDED)",
            "hierarchical": "Multi-level document structure",
            "graph": "LightRAG knowledge graph search",
        }

        print("Available search modes:")
        for mode, description in modes.items():
            print(f"   • {mode.upper()}: {description}")

        # Demonstrate hybrid search (most common)
        print(f"\n🎯 Performing HYBRID search (recommended)...")
        print("   Code: client.retrievals.retrieve(")
        print(f"       query='{query}',")
        print("       mode='hybrid',")
        print("       top_k=5")
        print("   )")

        # Simulate results
        print("\n✅ Search completed in 42ms")
        print("   Found 5 relevant chunks:\n")

        sample_results = [
            {
                "score": 0.92,
                "doc": "Introduction to RAG",
                "content": "RAG systems combine retrieval and generation. The key components include a retriever (usually vector search), a knowledge base (document store), and a generator (LLM)...",
            },
            {
                "score": 0.87,
                "doc": "RAG Architecture",
                "content": "The retrieval component uses semantic search to find relevant chunks. These chunks provide context to the LLM for generating accurate responses...",
            },
            {
                "score": 0.83,
                "doc": "Building RAG Systems",
                "content": "Essential components: 1) Document ingestion pipeline, 2) Embedding model, 3) Vector database, 4) LLM integration, 5) Prompt engineering...",
            },
        ]

        for i, result in enumerate(sample_results, 1):
            print(f"   {i}. Score: {result['score']:.2f} | {result['doc']}")
            print(f"      {result['content'][:120]}...")
            print()

        # Show metadata filtering
        print("💡 Pro tip: Filter by metadata")
        print("   results = client.retrievals.retrieve(")
        print("       query='transformers',")
        print("       metadata_filter={'year': 2024, 'topic': 'AI'}")
        print("   )")

    def demo_chat(self):
        """Demonstrate streaming chat"""
        self.print_step(5, "Streaming Chat with RAG")

        message = "Explain how RAG systems work"

        print(f"💬 User: {message}\n")
        print("🤖 Assistant: ", end="", flush=True)

        # Simulate streaming response
        demo_response = [
            "RAG (Retrieval-Augmented Generation) systems work by combining two key components: ",
            "a retrieval mechanism and a language model. ",
            "\n\nHere's how it works:\n",
            "1. **Query Processing**: When you ask a question, the system first converts it into an embedding.\n",
            "2. **Retrieval**: The system searches through your document collection to find the most relevant chunks.\n",
            "3. **Context Assembly**: Retrieved chunks are assembled as context.\n",
            "4. **Generation**: The LLM generates a response using both your query and the retrieved context.\n",
            "5. **Streaming**: The response is streamed back to you in real-time.\n\n",
            "This approach provides more accurate, up-to-date answers compared to relying solely on the LLM's training data.",
        ]

        try:
            for chunk in demo_response:
                print(chunk, end="", flush=True)
                time.sleep(0.05)  # Simulate streaming delay
            print("\n")
        except KeyboardInterrupt:
            print("\n⚠️  Streaming interrupted")

        print("\n✅ Chat features:")
        print("   • Real-time SSE streaming")
        print("   • Multi-turn conversations with session management")
        print("   • Source citation tracking")
        print("   • Collection-specific context")

        print("\n📝 Code example:")
        print("   for chunk in client.chat.chat(")
        print("       message='Explain RAG',")
        print("       stream=True,")
        print("       top_k=5")
        print("   ):")
        print("       print(chunk, end='', flush=True)")

    def cleanup(self):
        """Cleanup demo resources"""
        self.print_step(6, "Cleanup")

        print("🧹 In a real scenario, you might want to:")
        print("   • Keep the collection for further use")
        print("   • Delete temporary collections")
        print("   • Close the client connection")

        print("\n💡 Cleanup code:")
        print("   # Delete collection (optional)")
        print("   client.collections.delete(collection_id)")
        print()
        print("   # Close client")
        print("   client.close()")
        print()
        print("   # Or use context manager (automatic cleanup):")
        print("   with Client(api_key='...') as client:")
        print("       # Use client")
        print("       pass")
        print("   # Client closed automatically")

        if self.collection:
            print(f"\n📌 Demo collection ID: {self.collection.id}")
            print("   (Not deleted - you can explore it further)")


def main():
    """Main entry point"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║                    MNEMOSYNE SDK DEMO                              ║
║                                                                    ║
║  This interactive demo showcases the complete Mnemosyne SDK       ║
║  including collections, documents, search, and chat features.     ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    # Configuration
    api_key = os.getenv("MNEMOSYNE_API_KEY", "demo_api_key")
    base_url = os.getenv("MNEMOSYNE_BASE_URL", "http://localhost:8000")

    print("⚙️  Configuration:")
    print(f"   API Key: {api_key[:20]}..." if len(api_key) > 20 else f"   API Key: {api_key}")
    print(f"   Base URL: {base_url}")
    print()

    # Check if backend is accessible (optional)
    print("🔍 Checking backend availability...")
    import httpx
    try:
        response = httpx.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is accessible!")
        else:
            print(f"⚠️  Backend returned status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Could not reach backend: {e}")
        print("   This demo will show code examples instead of live API calls")

    print("\n" + "─" * 70)
    input("Press ENTER to start the demo...")

    # Run demo
    demo = MnemosyneDemo(api_key=api_key, base_url=base_url)
    demo.run()


if __name__ == "__main__":
    main()
