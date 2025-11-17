# LightRAG Examples

This directory contains demonstration scripts for LightRAG graph-based retrieval in Mnemosyne.

## Prerequisites

1. **OpenAI API Key**: Set in `.env` file
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

2. **Dependencies**: Ensure LightRAG is installed
   ```bash
   poetry install
   ```

3. **LightRAG Enabled**: Check `backend/config.py`
   ```python
   LIGHTRAG_ENABLED = True
   ```

---

## Examples

### 1. Direct LightRAG Service Demo

**File:** `lightrag_demo.py`

**What it demonstrates:**
- Service initialization
- Document insertion with automatic entity extraction
- Knowledge graph construction
- Local queries (specific entities like "Who founded Apple?")
- Global queries (abstract themes like "What are major tech companies?")
- Hybrid queries (combined approach)

**Run:**
```bash
poetry run python examples/lightrag_demo.py
```

**Expected output:**
- ✅ Service initialization
- 📚 3 documents indexed (Apple, Microsoft, Tech Trends)
- 🔍 5 example queries with answers
- 💡 Entity and relationship extraction results

**Time:** ~2-3 minutes (includes LLM calls for entity extraction)

---

### 2. REST API Demo

**File:** `lightrag_api_demo.py`

**What it demonstrates:**
- Using LightRAG via REST API
- Graph retrieval endpoint (`POST /retrievals`)
- API authentication with API keys
- Different query patterns

**Setup:**
1. Start Mnemosyne API:
   ```bash
   poetry run uvicorn backend.main:app --reload
   ```

2. Get API key (or use test key)

3. Update `API_KEY` in `lightrag_api_demo.py`

**Run:**
```bash
python examples/lightrag_api_demo.py
```

**Expected output:**
- 🌐 3 API requests to graph retrieval endpoint
- 📊 Structured results with scores
- ✅ JSON responses

---

## Query Modes Explained

### Local Mode
**Use case:** Specific entity queries

**Examples:**
- "Who founded Apple?"
- "When did Steve Jobs return to Apple?"
- "Where is Microsoft headquartered?"

**How it works:**
- Searches for specific entities in knowledge graph
- Returns precise information about nodes and edges
- Best for factual, targeted questions

---

### Global Mode
**Use case:** Abstract themes and patterns

**Examples:**
- "What are major tech companies?"
- "Where are tech hubs located?"
- "What are trends in technology?"

**How it works:**
- Aggregates information across multiple entities
- Identifies patterns and relationships
- Best for broad, exploratory questions

---

### Hybrid Mode (Recommended)
**Use case:** Complex queries needing both approaches

**Examples:**
- "Tell me about Microsoft CEOs and their contributions"
- "How did Apple and Microsoft evolve over time?"
- "What are the connections between Silicon Valley companies?"

**How it works:**
- Combines local and global retrieval
- Balances precision and comprehensiveness
- Best for most real-world queries

---

## Troubleshooting

### "No module named 'lightrag'"
**Solution:** Install dependencies
```bash
poetry install
```

### "OPENAI_API_KEY not set"
**Solution:** Add to `.env` file
```bash
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### "LightRAG is not enabled"
**Solution:** Enable in config
```python
# backend/config.py
LIGHTRAG_ENABLED = True
```

### Empty results
**Cause:** No documents indexed yet

**Solution:** Run demo to index sample documents first
```bash
poetry run python examples/lightrag_demo.py
```

---

## Understanding the Output

### Entity Extraction
LightRAG automatically extracts:
- **People:** Steve Jobs, Bill Gates, Tim Cook
- **Companies:** Apple, Microsoft, Google
- **Locations:** Cupertino, Redmond, Silicon Valley
- **Dates:** April 1, 1976; 2007; 2011

### Relationship Detection
LightRAG identifies:
- **Founded by:** Apple → Steve Jobs
- **Works at:** Tim Cook → Apple
- **Located in:** Apple → Cupertino
- **Succeeded by:** Steve Jobs → Tim Cook

### Knowledge Graph
- **Nodes:** Entities (people, companies, locations)
- **Edges:** Relationships between entities
- **Properties:** Attributes and metadata

---

## Next Steps

1. **Upload your own documents**
   - Use the API to upload documents
   - LightRAG will automatically build your knowledge graph

2. **Query your data**
   - Use the graph retrieval mode
   - Experiment with local/global/hybrid modes

3. **Compare retrieval modes**
   - Try the same query with different modes:
     - `semantic` - Vector similarity
     - `hybrid` - Vector + keyword
     - `hierarchical` - Document → chunk
     - `graph` - Entity + relationship

4. **Optimize for your use case**
   - Tune `LIGHTRAG_TOP_K` for result count
   - Adjust `LIGHTRAG_DEFAULT_MODE` for query style
   - Configure token limits for performance

---

## Performance Notes

**Initial indexing:**
- ~10-20 seconds per document (LLM calls for entity extraction)
- One-time cost per document

**Query performance:**
- Local queries: ~1-2 seconds
- Global queries: ~2-4 seconds
- Hybrid queries: ~3-5 seconds

**Token efficiency:**
- Traditional RAG: ~58,000 tokens
- LightRAG: ~3,000 tokens (99% reduction)

---

## API Endpoint Reference

### Graph Retrieval

**Endpoint:** `POST /retrievals`

**Request:**
```json
{
  "query": "Who founded Apple?",
  "mode": "graph",
  "top_k": 10,
  "collection_id": "optional-uuid"
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "graph_result",
      "content": "Apple was founded by Steve Jobs, Steve Wozniak...",
      "score": 1.0,
      "metadata": {"mode": "hybrid"},
      "document": {
        "id": "lightrag",
        "title": "Knowledge Graph Results"
      }
    }
  ],
  "query": "Who founded Apple?",
  "mode": "graph",
  "total_results": 1
}
```

---

## Resources

- **LightRAG Paper:** [arXiv:2410.05779](https://arxiv.org/abs/2410.05779)
- **Official Repo:** [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG)
- **Mnemosyne Docs:** See main README.md

---

## Support

For issues or questions:
- Check the main [Mnemosyne README](../README.md)
- Review [LightRAG documentation](https://github.com/HKUDS/LightRAG)
- Open an issue on GitHub
