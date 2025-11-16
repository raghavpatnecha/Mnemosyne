"""
LightRAG API Demo - Using the Graph Retrieval Endpoint
Demonstrates how to use LightRAG via the REST API
"""

import requests
import json
from typing import Dict, Any


# Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "mn_test_your_api_key_here"  # Replace with your API key


def make_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Make authenticated API request"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    url = f"{API_BASE_URL}{endpoint}"

    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")

    return response.json()


def demo_graph_retrieval():
    """Demonstrate graph-based retrieval via API"""
    print("=" * 80)
    print("🌐 LightRAG API Demo")
    print("=" * 80)

    # Example queries
    queries = [
        {
            "query": "Who founded Apple?",
            "mode": "graph",
            "top_k": 10,
            "description": "Entity-specific query using graph mode"
        },
        {
            "query": "What are major tech companies?",
            "mode": "graph",
            "top_k": 10,
            "description": "Abstract theme query using graph mode"
        },
        {
            "query": "Tell me about Microsoft CEOs",
            "mode": "graph",
            "top_k": 10,
            "description": "Relationship query using graph mode"
        }
    ]

    for i, query_data in enumerate(queries, 1):
        print(f"\n{'-' * 80}")
        print(f"Query {i}: {query_data['query']}")
        print(f"Mode: {query_data['mode']}")
        print(f"Description: {query_data['description']}")
        print(f"{'-' * 80}")

        try:
            # Make API request
            result = make_request(
                endpoint="/retrievals",
                method="POST",
                data={
                    "query": query_data["query"],
                    "mode": query_data["mode"],
                    "top_k": query_data["top_k"]
                }
            )

            # Display results
            print(f"\n📊 Results:")
            print(f"   Total: {result['total_results']}")
            print(f"   Mode: {result['mode']}")

            if result['results']:
                for j, chunk in enumerate(result['results'], 1):
                    print(f"\n   Result {j}:")
                    print(f"   Score: {chunk['score']}")
                    print(f"   Content: {chunk['content'][:200]}...")
                    print(f"   Document: {chunk['document']['title']}")

        except Exception as e:
            print(f"\n❌ Error: {e}")

    print("\n" + "=" * 80)
    print("✅ Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    print("\n🚀 Starting LightRAG API Demo...\n")
    demo_graph_retrieval()
