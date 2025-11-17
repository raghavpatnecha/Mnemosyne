# Python SDK Guide

The Mnemosyne Python SDK provides a clean, type-safe interface to interact with the Mnemosyne RAG API.

## 📦 Installation

```bash
pip install mnemosyne-sdk
```

## 📚 Complete Documentation

For the complete SDK documentation, see:

**👉 [Python SDK README](../../sdk/README.md)**

The SDK README includes:
- ✅ Installation instructions
- ✅ Quick start guide
- ✅ All 5 search modes (semantic, keyword, hybrid, hierarchical, graph)
- ✅ Streaming chat examples
- ✅ Async/await usage
- ✅ Error handling
- ✅ Configuration options
- ✅ API reference

## 🎯 Quick Examples

### Basic Usage

```python
from mnemosyne import Client

# Initialize
client = Client(api_key="mn_...")

# Create collection
collection = client.collections.create(name="My Docs")

# Upload document
doc = client.documents.create(
    collection_id=collection.id,
    file="document.pdf"
)

# Search
results = client.retrievals.retrieve(
    query="What is this about?",
    mode="hybrid",
    top_k=10
)
```

### Streaming Chat

```python
# Stream chat responses
for chunk in client.chat.chat(
    message="Explain this concept",
    stream=True
):
    print(chunk, end="", flush=True)
```

## 📖 Example Scripts

The SDK includes 6 complete example scripts in `sdk/examples/`:

1. **`basic_retrieval.py`** - All 5 search modes demonstrated
2. **`ingestion_workflow.py`** - Complete document ingestion lifecycle
3. **`video_ingestion.py`** - YouTube and MP4 video processing
4. **`streaming_chat.py`** - Real-time chat with SSE streaming
5. **`async_streaming.py`** - Async/await with concurrent operations
6. **`langchain_integration.py`** - LangChain retriever integration

Run any example:
```bash
cd sdk
python examples/basic_retrieval.py
```

## 🔗 Full SDK Documentation

For comprehensive documentation including:
- All SDK methods
- Type definitions
- Error handling
- Advanced configuration
- LangChain integration
- Production tips

**See the complete SDK documentation: [sdk/README.md](../../sdk/README.md)**

## 📦 Package Information

- **Package**: `mnemosyne-sdk`
- **PyPI**: https://pypi.org/project/mnemosyne-sdk/
- **Source**: [github.com/raghavpatnecha/Mnemosyne/tree/main/sdk](https://github.com/raghavpatnecha/Mnemosyne/tree/main/sdk)
- **License**: MIT

## 🆘 Getting Help

- **SDK README**: [sdk/README.md](../../sdk/README.md)
- **Examples**: [sdk/examples/](../../sdk/examples/)
- **API Docs**: [api-reference.md](api-reference.md)
- **Issues**: https://github.com/raghavpatnecha/Mnemosyne/issues
