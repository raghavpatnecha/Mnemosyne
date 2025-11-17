# Mnemosyne SDK Frontend Integration

This folder contains a web-based frontend for testing and demonstrating the Mnemosyne SDK capabilities. It provides a user-friendly interface for managing collections, uploading documents, and searching/chatting with your knowledge base.

## Features

- **Collection Management**: Create, view, select, and delete collections
- **Document Upload**: Upload PDFs, DOCX, TXT files, MP4 videos, or YouTube URLs
- **Multiple Search Modes**:
  - Semantic (vector similarity)
  - Hybrid (keyword + semantic, recommended)
  - Graph (LightRAG knowledge graph)
- **Graph Enhancement**: Toggle knowledge graph context for richer responses
- **Streaming Chat**: Real-time AI-powered responses with RAG context
- **Beautiful UI**: Clean, modern interface with existing Mnemosyne design

## Setup Instructions

### 1. Start the Backend

First, ensure the Mnemosyne backend is running. From the project root:

```bash
# Option A: Using Docker (recommended)
docker-compose up -d

# Option B: Run locally (requires PostgreSQL, Redis, Celery)
cd backend
python main.py
```

The backend should be running at `http://localhost:8000`

### 2. Register a User and Get API Key

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123"}'
```

Save the returned API key (starts with `mn_`).

### 3. Configure the Frontend

```bash
cd src

# Copy environment template
cp .env.example .env

# Edit .env and add your API key
nano .env  # or use your favorite editor
```

Set your API key in `.env`:
```
MNEMOSYNE_API_KEY=mn_your_actual_api_key_here
```

### 4. Install Dependencies

```bash
# Install Python dependencies (Quart, SDK, etc.)
pip install quart quart-cors mnemosyne-sdk

# Or use the project requirements
pip install -r ../requirements.txt
```

### 5. Start the Frontend

```bash
python app.py
```

The frontend will be available at `http://localhost:5000`

## Usage

### Creating Your First Collection

1. Open `http://localhost:5000` in your browser
2. Look for the toolbar at the top with "Collection:" dropdown
3. Click the **+** button to create a new collection
4. Enter a name (e.g., "Research Papers") and optional description
5. Click OK

### Uploading Documents

1. Select your collection from the dropdown
2. Click the **📤 Upload** button
3. Choose to either:
   - **Upload File**: Select PDF, DOCX, TXT, or MP4 files
   - **Upload from URL**: Paste a URL or YouTube link
4. Wait for processing (you'll see notifications)
5. Once complete, your documents are ready to search!

### Searching and Chatting

1. Click the search button or type your query
2. Choose your search mode:
   - **Semantic**: Best for conceptual questions
   - **Hybrid**: Balanced (recommended for most queries)
   - **Graph**: Best for complex relationships and reasoning
3. Toggle **🕸️** to enable/disable graph enhancement
4. Ask follow-up questions to continue the conversation

### Search Modes Explained

**Semantic Mode**
- Uses vector embeddings to find semantically similar content
- Best for: "What are the key concepts in machine learning?"

**Hybrid Mode** (Default)
- Combines keyword matching (BM25) with semantic search
- Best for: Most queries - balanced accuracy and relevance

**Graph Mode**
- Uses LightRAG knowledge graph for entity relationships
- Best for: "How do proteins interact with diseases?"
- Provides deeper context and connections

**Graph Enhancement**
- Adds knowledge graph context to any search mode
- Toggle with the 🕸️ button
- Recommended: Keep ON for richer responses

## API Endpoints

The frontend provides these API endpoints:

### Search & Chat
- `GET /mnemosyne/api/v1/search/<query>` - Legacy streaming search
- `POST /api/chat` - Chat with streaming response
- `POST /api/retrieve` - Non-streaming document retrieval

### Collections
- `GET /api/collections` - List all collections
- `POST /api/collections` - Create a new collection
- `GET /api/collections/<id>` - Get collection details
- `DELETE /api/collections/<id>` - Delete a collection

### Documents
- `GET /api/documents?collection_id=<id>` - List documents
- `POST /api/documents` - Upload a document
- `GET /api/documents/<id>` - Get document details
- `GET /api/documents/<id>/status` - Check processing status
- `DELETE /api/documents/<id>` - Delete a document

### Health
- `GET /health` - Check frontend and SDK status

## Architecture

```
src/
├── app.py                    # Quart web server with SDK integration
├── api/
│   └── search.py            # Search and chat logic using SDK
├── config.py                # Configuration (SDK settings)
├── static/
│   ├── css/
│   │   ├── style.css        # Existing UI styles
│   │   └── sdk-features.css # New SDK feature styles
│   └── js/
│       ├── script.js        # Existing search UI logic
│       └── sdk-features.js  # Collection, upload, mode management
├── templates/
│   └── index.html           # Main HTML template with SDK toolbar
└── README.md                # This file
```

## Troubleshooting

### "SDK not configured" Error
- Make sure you set `MNEMOSYNE_API_KEY` in `.env`
- Restart the frontend app after changing `.env`

### "Failed to connect to backend" Error
- Verify the backend is running: `curl http://localhost:8000/health`
- Check `MNEMOSYNE_BASE_URL` in `.env` is correct
- Ensure firewall allows connections to port 8000

### Document Processing Stuck
- Check Celery worker is running (if using Docker, it auto-starts)
- View document status with: `GET /api/documents/<document-id>/status`
- Check backend logs for errors

### No Collections Showing
- Create a collection using the + button
- Check browser console (F12) for JavaScript errors
- Verify API key has correct permissions

## Development

### File Size Guidelines
Per project guidelines, all files should stay under 300 lines. The code is organized as:

- `sdk-features.js` (370 lines) - Could be split into:
  - `collections.js` (collection management)
  - `documents.js` (document upload)
  - `search-config.js` (search mode selection)

### Adding New Features

1. **Backend**: Add endpoints to `app.py`
2. **Frontend Logic**: Add functions to `sdk-features.js` or new module
3. **UI**: Update `index.html` and `sdk-features.css`
4. **Testing**: Test with backend running and documents uploaded

## SDK Reference

This frontend uses the [Mnemosyne Python SDK](../sdk/README.md).

Key SDK operations:
```python
from mnemosyne import Client

# Initialize
client = Client(api_key="mn_...")

# Collections
collection = client.collections.create(name="Papers")
collections = client.collections.list()

# Documents
doc = client.documents.create(collection.id, file="paper.pdf")
status = client.documents.get_status(doc.id)

# Search
results = client.retrievals.retrieve(
    query="transformers",
    mode="hybrid",
    enable_graph=True
)

# Chat
for chunk in client.chat.chat(message="Explain RAG", stream=True):
    print(chunk, end="")
```

## Credits

Built by Raghav Patnecha and Akshay Bahadur

Original Medium search frontend adapted for Mnemosyne SDK integration.
