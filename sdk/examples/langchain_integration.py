"""
LangChain integration example.

This example demonstrates how to use Mnemosyne SDK with LangChain:
- Custom retriever implementation
- Integration with LangChain chains
- Building RAG pipelines
- Using Mnemosyne as a vector store
"""

from typing import List
from uuid import UUID
from mnemosyne import Client

# LangChain imports
try:
    from langchain.schema import Document
    from langchain.schema.retriever import BaseRetriever
    from langchain.callbacks.manager import CallbackManagerForRetrieverRun
    from langchain.chains import RetrievalQA
    from langchain.llms import OpenAI
    from langchain.prompts import PromptTemplate
except ImportError:
    print("Error: LangChain not installed. Install with: pip install langchain openai")
    exit(1)


class MnemosyneRetriever(BaseRetriever):
    """
    LangChain retriever for Mnemosyne RAG API.

    This retriever integrates Mnemosyne's search capabilities
    into LangChain workflows.
    """

    client: Client
    collection_id: UUID
    mode: str = "hybrid"
    top_k: int = 10

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun = None,
    ) -> List[Document]:
        """
        Retrieve relevant documents from Mnemosyne.

        Args:
            query: Search query
            run_manager: LangChain callback manager

        Returns:
            List[Document]: Retrieved documents in LangChain format
        """
        # Query Mnemosyne API
        results = self.client.retrievals.retrieve(
            query=query,
            mode=self.mode,
            top_k=self.top_k,
            collection_id=self.collection_id,
        )

        # Convert to LangChain Document format
        documents = []
        for result in results.results:
            doc = Document(
                page_content=result.content,
                metadata={
                    "chunk_id": result.chunk_id,
                    "score": result.score,
                    "chunk_index": result.chunk_index,
                    "document_id": result.document.id,
                    "document_title": result.document.title,
                    "document_metadata": result.document.metadata,
                },
            )
            documents.append(doc)

        return documents

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun = None,
    ) -> List[Document]:
        """Async version (not implemented in this example)"""
        raise NotImplementedError("Async retrieval not implemented")


def basic_retrieval_example():
    """Basic retrieval using Mnemosyne retriever"""

    print("=" * 60)
    print("BASIC LANGCHAIN RETRIEVAL")
    print("=" * 60)

    # Initialize Mnemosyne client
    client = Client(api_key="your_api_key_here")
    collection_id = UUID("your-collection-id-here")

    # Create retriever
    retriever = MnemosyneRetriever(
        client=client,
        collection_id=collection_id,
        mode="hybrid",
        top_k=5,
    )

    # Retrieve documents
    query = "What are transformers in deep learning?"
    docs = retriever.get_relevant_documents(query)

    print(f"\nQuery: {query}\n")
    print(f"Retrieved {len(docs)} documents:\n")

    for i, doc in enumerate(docs, 1):
        print(f"{i}. Score: {doc.metadata['score']:.4f}")
        print(f"   Source: {doc.metadata['document_title']}")
        print(f"   Content: {doc.page_content[:150]}...")
        print()


def retrieval_qa_chain():
    """Build a RetrievalQA chain with Mnemosyne"""

    print("\n" + "=" * 60)
    print("RETRIEVAL QA CHAIN")
    print("=" * 60)

    # Initialize components
    client = Client(api_key="your_api_key_here")
    collection_id = UUID("your-collection-id-here")

    retriever = MnemosyneRetriever(
        client=client,
        collection_id=collection_id,
        mode="hybrid",
        top_k=5,
    )

    # Initialize LLM (you need OPENAI_API_KEY env var)
    llm = OpenAI(temperature=0)

    # Create custom prompt
    prompt_template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context:
{context}

Question: {question}

Answer:"""

    PROMPT = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"],
    )

    # Build RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True,
    )

    # Ask questions
    questions = [
        "What is the attention mechanism in transformers?",
        "How does retrieval-augmented generation work?",
        "What are the benefits of using RAG over fine-tuning?",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}]")
        print(f"Q: {question}\n")

        result = qa_chain({"query": question})

        print(f"A: {result['result']}\n")
        print(f"Sources ({len(result['source_documents'])} documents):")
        for doc in result["source_documents"][:3]:
            print(f"  - {doc.metadata['document_title']} (score: {doc.metadata['score']:.4f})")
        print()


def multi_mode_comparison():
    """Compare different retrieval modes in LangChain"""

    print("\n" + "=" * 60)
    print("MULTI-MODE RETRIEVAL COMPARISON")
    print("=" * 60)

    client = Client(api_key="your_api_key_here")
    collection_id = UUID("your-collection-id-here")

    query = "What are the key innovations in transformer architecture?"

    modes = ["semantic", "keyword", "hybrid", "hierarchical", "graph"]

    print(f"\nQuery: {query}\n")

    for mode in modes:
        retriever = MnemosyneRetriever(
            client=client,
            collection_id=collection_id,
            mode=mode,
            top_k=3,
        )

        docs = retriever.get_relevant_documents(query)

        print(f"\n{mode.upper()} MODE:")
        print(f"  Retrieved {len(docs)} documents")
        print(f"  Top result score: {docs[0].metadata['score']:.4f}")
        print(f"  Preview: {docs[0].page_content[:100]}...")


def custom_chain_example():
    """Build a custom chain with multiple Mnemosyne collections"""

    print("\n" + "=" * 60)
    print("CUSTOM MULTI-COLLECTION CHAIN")
    print("=" * 60)

    client = Client(api_key="your_api_key_here")

    # Multiple collections for different domains
    collections = {
        "research_papers": UUID("collection-id-1"),
        "documentation": UUID("collection-id-2"),
        "blog_posts": UUID("collection-id-3"),
    }

    query = "How do I implement a RAG system?"

    print(f"\nQuery: {query}\n")
    print("Searching across multiple collections...\n")

    all_docs = []
    for name, coll_id in collections.items():
        retriever = MnemosyneRetriever(
            client=client,
            collection_id=coll_id,
            mode="hybrid",
            top_k=3,
        )

        docs = retriever.get_relevant_documents(query)
        all_docs.extend(docs)

        print(f"{name.upper()}:")
        for doc in docs:
            print(f"  - Score: {doc.metadata['score']:.4f} | {doc.page_content[:80]}...")
        print()

    # Sort by score and take top results
    all_docs.sort(key=lambda x: x.metadata["score"], reverse=True)
    top_docs = all_docs[:5]

    print(f"\nTop {len(top_docs)} results across all collections:")
    for i, doc in enumerate(top_docs, 1):
        print(f"{i}. Score: {doc.metadata['score']:.4f}")
        print(f"   Collection: {doc.metadata['document_metadata'].get('collection', 'N/A')}")
        print(f"   Content: {doc.page_content[:100]}...")
        print()


def main():
    """Run LangChain integration examples"""

    print("\nMnemosyne + LangChain Integration Examples\n")

    # Example 1: Basic retrieval
    basic_retrieval_example()

    # Example 2: RetrievalQA chain (requires OpenAI API key)
    # retrieval_qa_chain()

    # Example 3: Multi-mode comparison
    multi_mode_comparison()

    # Example 4: Custom chain
    custom_chain_example()

    print("\n" + "=" * 60)
    print("LANGCHAIN EXAMPLES COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
