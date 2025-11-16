"""
Async streaming example demonstrating AsyncClient usage.

This example shows:
- Concurrent document uploads using asyncio
- Async status monitoring
- Parallel search across multiple collections
- Async chat streaming
"""

import asyncio
from pathlib import Path
from uuid import UUID
from mnemosyne import AsyncClient


async def concurrent_uploads(client: AsyncClient, collection_id: UUID):
    """Upload multiple documents concurrently"""

    print("=" * 60)
    print("CONCURRENT DOCUMENT UPLOADS")
    print("=" * 60)

    documents = [
        {"file": "docs/paper1.pdf", "metadata": {"topic": "nlp"}},
        {"file": "docs/paper2.pdf", "metadata": {"topic": "cv"}},
        {"file": "docs/paper3.pdf", "metadata": {"topic": "rl"}},
        {"file": "docs/paper4.pdf", "metadata": {"topic": "graph"}},
    ]

    # Upload all documents concurrently
    print(f"\nUploading {len(documents)} documents concurrently...")
    tasks = []
    for doc_info in documents:
        task = client.documents.create(
            collection_id=collection_id,
            file=doc_info["file"],
            metadata=doc_info["metadata"],
        )
        tasks.append(task)

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = []
        failed = []
        for doc_info, result in zip(documents, results):
            if isinstance(result, Exception):
                failed.append((doc_info["file"], str(result)))
                print(f"✗ Failed: {doc_info['file']} - {result}")
            else:
                successful.append(result)
                print(f"✓ Uploaded: {result.filename} (ID: {result.id})")

        print(f"\n✓ Successful: {len(successful)}/{len(documents)}")
        if failed:
            print(f"✗ Failed: {len(failed)}/{len(documents)}")

        return successful

    except Exception as e:
        print(f"✗ Batch upload failed: {e}")
        return []


async def monitor_processing(client: AsyncClient, doc_ids: list[UUID]):
    """Monitor document processing status asynchronously"""

    print("\n" + "=" * 60)
    print("ASYNC PROCESSING MONITORING")
    print("=" * 60)

    pending = set(doc_ids)
    while pending:
        await asyncio.sleep(2)

        # Check status of all pending documents concurrently
        tasks = [client.documents.get_status(doc_id) for doc_id in pending]
        statuses = await asyncio.gather(*tasks)

        for doc_id, status in zip(list(pending), statuses):
            if status.status == "completed":
                print(
                    f"✓ {doc_id}: COMPLETED "
                    f"(Chunks: {status.chunk_count}, Tokens: {status.total_tokens})"
                )
                pending.remove(doc_id)
            elif status.status == "failed":
                print(f"✗ {doc_id}: FAILED - {status.error_message}")
                pending.remove(doc_id)

        if pending:
            print(f"⏳ Waiting for {len(pending)} documents...")

    print("\n✓ All documents processed!")


async def parallel_search(client: AsyncClient, collection_ids: list[UUID]):
    """Search multiple collections in parallel"""

    print("\n" + "=" * 60)
    print("PARALLEL MULTI-COLLECTION SEARCH")
    print("=" * 60)

    query = "What are the latest advances in machine learning?"

    # Search all collections concurrently
    print(f"\nSearching {len(collection_ids)} collections in parallel...")
    tasks = [
        client.retrievals.retrieve(
            query=query,
            mode="hybrid",
            top_k=3,
            collection_id=coll_id,
        )
        for coll_id in collection_ids
    ]

    results_list = await asyncio.gather(*tasks)

    print(f"\n✓ Search complete!\n")

    for i, (coll_id, results) in enumerate(zip(collection_ids, results_list), 1):
        print(f"Collection {i} ({coll_id}):")
        print(f"  Found {len(results.results)} results in {results.processing_time_ms:.2f}ms")
        for result in results.results[:2]:
            print(f"  - Score: {result.score:.4f} | {result.content[:80]}...")
        print()


async def streaming_chat(client: AsyncClient):
    """Stream chat responses asynchronously"""

    print("\n" + "=" * 60)
    print("ASYNC CHAT STREAMING")
    print("=" * 60)

    message = "Explain the transformer architecture in simple terms"

    print(f"\nQuery: {message}\n")
    print("Assistant: ", end="", flush=True)

    async for chunk in client.chat.chat(
        message=message,
        stream=True,
    ):
        print(chunk, end="", flush=True)

    print("\n")


async def main():
    """Run async examples"""

    print("\nMnemosyne AsyncClient Example\n")

    async with AsyncClient(api_key="your_api_key_here") as client:
        # Create a test collection
        collection = await client.collections.create(
            name="Async Test Collection",
            description="Testing async operations",
        )
        print(f"✓ Created collection: {collection.id}\n")

        # Example 1: Concurrent uploads
        uploaded_docs = await concurrent_uploads(client, collection.id)

        if uploaded_docs:
            # Example 2: Monitor processing
            doc_ids = [doc.id for doc in uploaded_docs]
            await monitor_processing(client, doc_ids)

            # Example 3: Parallel search (if we had multiple collections)
            # await parallel_search(client, [collection.id])

        # Example 4: Streaming chat
        await streaming_chat(client)

        print("\n" + "=" * 60)
        print("ASYNC EXAMPLES COMPLETE!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
