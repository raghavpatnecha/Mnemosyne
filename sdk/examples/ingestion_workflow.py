"""
Complete ingestion workflow example.

This example demonstrates the full document ingestion lifecycle:
1. Create a collection
2. Batch upload documents
3. Monitor processing status
4. Verify ingestion success
5. Update collection metadata
"""

import time
from pathlib import Path
from mnemosyne import Client

# Initialize client
client = Client(api_key="your_api_key_here")


def main():
    """Run complete ingestion workflow"""

    # STEP 1: Create Collection
    print("Step 1: Creating collection...")
    collection = client.collections.create(
        name="AI Research Papers 2024",
        description="Latest papers on LLMs, RAG, and transformers",
        metadata={"domain": "machine_learning", "year": 2024},
        config={"embedding_model": "text-embedding-3-small"},
    )
    print(f"✓ Created collection: {collection.id}")
    print(f"  Name: {collection.name}")
    print()

    # STEP 2: Batch Upload Documents
    print("Step 2: Uploading documents...")
    documents_to_upload = [
        {
            "file": "papers/attention_is_all_you_need.pdf",
            "metadata": {"authors": "Vaswani et al.", "year": 2017, "topic": "transformers"},
        },
        {
            "file": "papers/rag_paper.pdf",
            "metadata": {"authors": "Lewis et al.", "year": 2020, "topic": "retrieval"},
        },
        {
            "file": "papers/llama2.pdf",
            "metadata": {"authors": "Touvron et al.", "year": 2023, "topic": "language_models"},
        },
    ]

    uploaded_docs = []
    for doc_info in documents_to_upload:
        try:
            doc = client.documents.create(
                collection_id=collection.id,
                file=doc_info["file"],
                metadata=doc_info["metadata"],
            )
            uploaded_docs.append(doc)
            print(f"✓ Uploaded: {doc.filename} (ID: {doc.id})")
        except FileNotFoundError:
            print(f"✗ File not found: {doc_info['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")

    print(f"\nUploaded {len(uploaded_docs)}/{len(documents_to_upload)} documents")
    print()

    # STEP 3: Monitor Processing Status
    print("Step 3: Monitoring processing status...")

    def wait_for_processing(doc_ids, check_interval=3):
        """Wait for all documents to finish processing"""
        pending = set(doc_ids)
        while pending:
            time.sleep(check_interval)
            for doc_id in list(pending):
                status = client.documents.get_status(doc_id)

                if status.status == "completed":
                    print(
                        f"✓ {doc_id}: COMPLETED "
                        f"(Chunks: {status.chunk_count}, Tokens: {status.total_tokens})"
                    )
                    pending.remove(doc_id)
                elif status.status == "failed":
                    print(f"✗ {doc_id}: FAILED - {status.error_message}")
                    pending.remove(doc_id)
                elif status.status == "processing":
                    print(f"⏳ {doc_id}: Processing...")

            if pending:
                print(f"Waiting for {len(pending)} documents...")

    doc_ids = [doc.id for doc in uploaded_docs]
    wait_for_processing(doc_ids)
    print()

    # STEP 4: Verify Ingestion
    print("Step 4: Verifying ingestion...")
    collection = client.collections.get(collection.id)
    print(f"✓ Collection document count: {collection.document_count}")

    docs_list = client.documents.list(
        collection_id=collection.id,
        status_filter="completed",
    )
    print(f"✓ Completed documents: {len(docs_list.data)}")

    total_chunks = 0
    total_tokens = 0
    for doc in docs_list.data:
        status = client.documents.get_status(doc.id)
        total_chunks += status.chunk_count
        total_tokens += status.total_tokens

    print(f"✓ Total chunks created: {total_chunks}")
    print(f"✓ Total tokens processed: {total_tokens}")
    print()

    # STEP 5: Update Collection Metadata
    print("Step 5: Updating collection metadata...")
    updated_collection = client.collections.update(
        collection_id=collection.id,
        metadata={
            **collection.metadata,
            "total_documents": collection.document_count,
            "total_chunks": total_chunks,
            "total_tokens": total_tokens,
            "status": "ready",
        },
    )
    print(f"✓ Updated collection metadata: {updated_collection.metadata}")
    print()

    print("=" * 60)
    print("INGESTION COMPLETE!")
    print("=" * 60)
    print(f"Collection ID: {collection.id}")
    print(f"Documents: {collection.document_count}")
    print(f"Chunks: {total_chunks}")
    print(f"Tokens: {total_tokens}")
    print("\nYou can now use this collection for retrieval and chat!")


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
