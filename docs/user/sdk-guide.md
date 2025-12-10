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
    if chunk.type == "delta" and chunk.content:
        print(chunk.content, end="", flush=True)
    elif chunk.type == "sources":
        print(f"\nSources: {[s.title for s in chunk.sources]}")
```

### Non-Streaming Chat

```python
# Get complete response
response = client.chat.chat(
    message="Explain this concept",
    stream=False
)
print(response.response)
print(f"Sources: {response.sources}")
```

### Answer Style Presets

```python
# Concise answer for quick lookups
for chunk in client.chat.chat("What is RAG?", preset="concise"):
    if chunk.type == "delta":
        print(chunk.content, end="")

# Research-grade response
for chunk in client.chat.chat(
    message="Compare vector databases",
    preset="research",
    model="gpt-4o"  # Use more capable model
):
    if chunk.type == "delta":
        print(chunk.content, end="")

# Technical precise answer with exact details
for chunk in client.chat.chat(
    message="What are the key specifications?",
    preset="technical"
):
    if chunk.type == "delta":
        print(chunk.content, end="")
```

### Custom Instructions & Question Generation

```python
# Generate MCQs using qna preset with custom instruction
for chunk in client.chat.chat(
    message="Create questions about machine learning",
    preset="qna",  # Question generation mode
    custom_instruction="Generate 10 MCQs with 4 options each. Mark the correct answer."
):
    if chunk.type == "delta":
        print(chunk.content, end="")

# Focus on specific aspects with custom instruction
for chunk in client.chat.chat(
    message="Analyze this codebase",
    preset="technical",
    custom_instruction="Focus on security vulnerabilities and potential exploits"
):
    if chunk.type == "delta":
        print(chunk.content, end="")
```

### Follow-up Questions with Context Preservation

```python
# Initial question
session_id = None
for chunk in client.chat.chat("What is RAG?", session_id=session_id):
    if chunk.type == "delta":
        print(chunk.content, end="")
    elif chunk.type == "done" and chunk.metadata:
        session_id = chunk.metadata.session_id
print()

# Follow-up with context preservation
for chunk in client.chat.chat(
    "How does it compare to fine-tuning?",
    session_id=session_id,
    is_follow_up=True  # Preserves context from previous exchange
):
    if chunk.type == "delta":
        print(chunk.content, end="")
```

### Deep Reasoning Mode

```python
# Multi-step iterative reasoning for complex questions
for chunk in client.chat.chat(
    message="Compare RAG architectures and recommend the best for legal documents",
    preset="research",
    reasoning_mode="deep",
    model="gpt-4o"
):
    if chunk.type == "reasoning_step":
        print(f"\n[Step {chunk.step}] {chunk.description}")
    elif chunk.type == "sub_query":
        print(f"  Searching: {chunk.query}")
    elif chunk.type == "delta":
        print(chunk.content, end="")
    elif chunk.type == "sources":
        print(f"\nSources: {len(chunk.sources)} documents")
```

## 📖 Example Scripts

The SDK includes 10 complete example scripts in `sdk/examples/`:

### Core Examples
1. **`basic_retrieval.py`** - All 5 search modes demonstrated
2. **`ingestion_workflow.py`** - Complete document ingestion lifecycle
3. **`streaming_chat.py`** - Real-time chat with SSE streaming
4. **`async_streaming.py`** - Async/await with concurrent operations
5. **`langchain_integration.py`** - LangChain retriever integration

### Multimodal Examples
6. **`video_ingestion.py`** - YouTube and MP4 video transcription
7. **`image_ingestion.py`** - Image analysis with GPT-4 Vision (PNG, JPG, WEBP)
8. **`audio_ingestion.py`** - Audio transcription with Whisper (MP3, WAV, M4A, FLAC)
9. **`excel_ingestion.py`** - Excel spreadsheet processing (XLSX, XLS)
10. **`multimodal_ingestion.py`** - Combined multimodal knowledge base

Run any example:
```bash
cd sdk
python examples/basic_retrieval.py
python examples/multimodal_ingestion.py
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
