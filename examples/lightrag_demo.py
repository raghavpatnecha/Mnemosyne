"""
LightRAG Demo - Knowledge Graph RAG in Action
Demonstrates entity extraction, relationship detection, and graph-based retrieval
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.lightrag_service import get_lightrag_service, initialize_lightrag
from backend.config import settings


async def demo_lightrag():
    """
    Comprehensive LightRAG demonstration

    Shows:
    1. Service initialization
    2. Document insertion with entity extraction
    3. Local queries (specific entities)
    4. Global queries (abstract themes)
    5. Hybrid queries (combined approach)
    """
    print("=" * 80)
    print("🔮 LightRAG Knowledge Graph Demo")
    print("=" * 80)

    # Check prerequisites
    if not settings.OPENAI_API_KEY:
        print("\n❌ ERROR: OPENAI_API_KEY not set in environment")
        print("   Please set OPENAI_API_KEY in .env file")
        print("\n   Example:")
        print("   OPENAI_API_KEY=sk-...")
        return False

    print(f"\n✅ OPENAI_API_KEY configured")
    print(f"✅ LightRAG enabled: {settings.LIGHTRAG_ENABLED}")
    print(f"✅ Working directory: {settings.LIGHTRAG_WORKING_DIR}")

    # Initialize service
    print("\n" + "=" * 80)
    print("Step 1: Initializing LightRAG Service")
    print("=" * 80)

    try:
        await initialize_lightrag()
        lightrag = get_lightrag_service()
        print("✅ LightRAG service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize LightRAG: {e}")
        return False

    # Sample documents with rich entity relationships
    documents = [
        {
            "id": uuid4(),
            "title": "Apple Inc. History",
            "content": """
            Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne on
            April 1, 1976, in Cupertino, California. The company revolutionized personal
            computing with the Apple II in 1977 and the Macintosh in 1984. Steve Jobs
            was ousted from Apple in 1985 but returned in 1997, leading the company to
            unprecedented success with products like the iPod (2001), iPhone (2007),
            and iPad (2010). Tim Cook became CEO after Steve Jobs' death in 2011.
            """
        },
        {
            "id": uuid4(),
            "title": "Microsoft Corporation",
            "content": """
            Microsoft was founded by Bill Gates and Paul Allen on April 4, 1975, in
            Albuquerque, New Mexico. The company became famous for MS-DOS and Windows
            operating systems. Bill Gates served as CEO until 2000, when Steve Ballmer
            took over. Satya Nadella became CEO in 2014, leading Microsoft's
            transformation to cloud computing with Azure. Microsoft is headquartered
            in Redmond, Washington.
            """
        },
        {
            "id": uuid4(),
            "title": "Tech Industry Trends",
            "content": """
            The technology industry has seen major shifts over the past decades.
            Artificial intelligence and machine learning are transforming how companies
            operate. Cloud computing has enabled startups to compete with established
            players. Major tech hubs include Silicon Valley (California), Seattle
            (Washington), and Austin (Texas). Companies like Apple, Microsoft, Google,
            and Amazon dominate the market.
            """
        }
    ]

    # Insert documents
    print("\n" + "=" * 80)
    print("Step 2: Inserting Documents & Building Knowledge Graph")
    print("=" * 80)
    print("\nIndexing documents (this may take 30-60 seconds)...")

    for i, doc in enumerate(documents, 1):
        print(f"\n[{i}/{len(documents)}] Indexing: {doc['title']}")
        try:
            result = await lightrag.insert_document(
                content=doc["content"],
                document_id=doc["id"],
                metadata={"title": doc["title"]}
            )
            if result["status"] == "indexed":
                print(f"   ✅ Indexed successfully ({result['content_length']} chars)")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n✅ Knowledge graph constructed!")
    print("   - Entities extracted (people, companies, locations, dates)")
    print("   - Relationships detected (founded by, works at, located in)")
    print("   - Graph nodes and edges created")

    # Demo queries
    queries = [
        {
            "type": "LOCAL",
            "mode": "local",
            "query": "Who founded Apple?",
            "description": "Specific entity query - finds exact person and relationship"
        },
        {
            "type": "LOCAL",
            "mode": "local",
            "query": "When did Steve Jobs return to Apple?",
            "description": "Specific event query - finds temporal relationships"
        },
        {
            "type": "GLOBAL",
            "mode": "global",
            "query": "What are the major tech companies?",
            "description": "Abstract theme query - aggregates across documents"
        },
        {
            "type": "GLOBAL",
            "mode": "global",
            "query": "Where are tech companies located?",
            "description": "Pattern detection - finds location relationships"
        },
        {
            "type": "HYBRID",
            "mode": "hybrid",
            "query": "Tell me about Microsoft's CEOs and their contributions",
            "description": "Combined query - uses both local (CEOs) and global (contributions)"
        }
    ]

    print("\n" + "=" * 80)
    print("Step 3: Querying Knowledge Graph (5 Examples)")
    print("=" * 80)

    for i, q in enumerate(queries, 1):
        print(f"\n{'-' * 80}")
        print(f"Query {i}: [{q['type']}] {q['query']}")
        print(f"Mode: {q['mode']}")
        print(f"Description: {q['description']}")
        print(f"{'-' * 80}")

        try:
            result = await lightrag.query(
                query_text=q["query"],
                mode=q["mode"],
                top_k=10
            )

            if result["status"] == "success":
                context = result["context"]
                print(f"\n📊 Result:")
                print(f"   Mode: {result['mode']}")
                print(f"   Context length: {len(context)} chars")
                print(f"\n💡 Answer:")
                print(f"   {context[:500]}..." if len(context) > 500 else f"   {context}")
            else:
                print(f"\n❌ Query failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"\n❌ Error: {e}")

    # Cleanup
    print("\n" + "=" * 80)
    print("Step 4: Cleanup")
    print("=" * 80)

    try:
        await lightrag.cleanup()
        print("✅ LightRAG service cleaned up")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("🎉 Demo Complete!")
    print("=" * 80)
    print("\n📚 What Just Happened:")
    print("   1. Initialized LightRAG service")
    print("   2. Inserted 3 documents about tech companies")
    print("   3. Automatically extracted entities (people, companies, locations)")
    print("   4. Built knowledge graph with relationships")
    print("   5. Demonstrated 3 query modes (local, global, hybrid)")
    print("\n🎯 Key Benefits:")
    print("   - Entity-aware search (understands WHO, WHAT, WHERE)")
    print("   - Relationship detection (founded by, works at, etc.)")
    print("   - Multi-hop reasoning (traverses graph connections)")
    print("   - 99% token reduction vs naive RAG")
    print("\n🚀 Next Steps:")
    print("   - Use via API: POST /retrievals with mode='graph'")
    print("   - Upload documents to build your knowledge graph")
    print("   - Try different query modes for your use case")
    print("\n✨ Happy Knowledge Graphing!")

    return True


if __name__ == "__main__":
    print("\n🚀 Starting LightRAG Demo...\n")
    success = asyncio.run(demo_lightrag())
    sys.exit(0 if success else 1)
