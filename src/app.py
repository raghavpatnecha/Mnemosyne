"""
Mnemosyne Frontend Application with SDK Integration
Provides web interface for RAG-powered search and chat
"""
from quart import Quart, render_template, Response, request, jsonify
from quart_cors import cors
from src.api.search import decode_query, stream_response, search_documents, get_sdk_client
from src.config import Config
from mnemosyne.exceptions import MnemosyneError

config = Config()

app = Quart(__name__, template_folder='./templates', static_folder='./static')
app = cors(app)


def sanitize_optional_param(value):
    """Convert invalid optional params (string 'None', 'null', etc.) to Python None."""
    if value in (None, '', 'None', 'null', 'undefined'):
        return None
    return value


@app.route('/')
async def home():
    """Render the main application page"""
    return await render_template('index.html')


@app.route('/search/<path:query>')
async def search_page(query: str):
    """
    Render the main page for search URLs.
    The actual search is triggered by JavaScript on page load.
    """
    return await render_template('index.html')


@app.route('/mnemosyne/api/v1/search/<query>')
async def search(query: str) -> Response:
    """
    Handle streaming search/chat requests (legacy endpoint).
    Maintains compatibility with existing frontend while supporting new features.

    Query parameters:
        collection_id: Optional collection ID to filter results
        session_id: Optional session ID for multi-turn conversations
        mode: Search mode (hybrid, semantic, keyword, hierarchical, graph)
        preset: Answer style (concise, detailed, research, technical, creative, qna)
        reasoning_mode: Reasoning mode (standard, deep)
        model: LLM model to use (any LiteLLM-compatible model)
        temperature: Override temperature (0.0-1.0)
        max_tokens: Override max tokens for response
        custom_instruction: Custom instruction for additional guidance
        is_follow_up: Whether this is a follow-up question
    """
    final_query = decode_query(query)

    # Get optional query parameters
    args = request.args
    collection_id = sanitize_optional_param(args.get('collection_id'))
    session_id = sanitize_optional_param(args.get('session_id'))
    mode = sanitize_optional_param(args.get('mode'))
    # New enhanced chat parameters
    preset = sanitize_optional_param(args.get('preset'))
    reasoning_mode = sanitize_optional_param(args.get('reasoning_mode'))
    model = sanitize_optional_param(args.get('model'))
    temperature = args.get('temperature', type=float)
    max_tokens = args.get('max_tokens', type=int)
    custom_instruction = sanitize_optional_param(args.get('custom_instruction'))
    is_follow_up = args.get('is_follow_up', 'false').lower() == 'true'

    return Response(
        stream_response(
            final_query,
            collection_id=collection_id,
            session_id=session_id,
            mode=mode,
            preset=preset,
            reasoning_mode=reasoning_mode,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            custom_instruction=custom_instruction,
            is_follow_up=is_follow_up
        ),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/chat', methods=['POST'])
async def chat():
    """
    Handle chat requests with JSON payload.
    Supports collection filtering, multi-turn conversations, and enhanced features.

    JSON body parameters:
        message/query: The chat message (required)
        collection_id: Optional collection ID to filter results
        session_id: Optional session ID for multi-turn conversations
        mode: Search mode (hybrid, semantic, keyword, hierarchical, graph)
        preset: Answer style (concise, detailed, research, technical, creative, qna)
        reasoning_mode: Reasoning mode (standard, deep)
        model: LLM model to use (any LiteLLM-compatible model)
        temperature: Override temperature (0.0-1.0)
        max_tokens: Override max tokens for response
        custom_instruction: Custom instruction for additional guidance
        is_follow_up: Whether this is a follow-up question
    """
    data = await request.get_json()
    query = data.get('message') or data.get('query')
    collection_id = sanitize_optional_param(data.get('collection_id'))
    session_id = sanitize_optional_param(data.get('session_id'))
    mode = sanitize_optional_param(data.get('mode'))
    # New enhanced chat parameters
    preset = sanitize_optional_param(data.get('preset'))
    reasoning_mode = sanitize_optional_param(data.get('reasoning_mode'))
    model = sanitize_optional_param(data.get('model'))
    temperature = data.get('temperature')
    max_tokens = data.get('max_tokens')
    custom_instruction = sanitize_optional_param(data.get('custom_instruction'))
    is_follow_up = data.get('is_follow_up', False)

    if not query:
        return jsonify({"error": "Missing 'message' or 'query' field"}), 400

    return Response(
        stream_response(
            query,
            collection_id=collection_id,
            session_id=session_id,
            mode=mode,
            preset=preset,
            reasoning_mode=reasoning_mode,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            custom_instruction=custom_instruction,
            is_follow_up=is_follow_up
        ),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/retrieve', methods=['POST'])
async def retrieve():
    """
    Handle document retrieval requests (non-streaming search).
    Returns ranked document chunks without chat generation.
    """
    data = await request.get_json()
    query = data.get('query')
    collection_id = sanitize_optional_param(data.get('collection_id'))
    mode = sanitize_optional_param(data.get('mode'))
    top_k = data.get('top_k')

    if not query:
        return jsonify({"error": "Missing 'query' field"}), 400

    results = await search_documents(query, collection_id=collection_id,
                                    mode=mode, top_k=top_k)
    return jsonify(results)


@app.route('/api/collections', methods=['GET'])
async def list_collections():
    """List all collections"""
    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)

        collections = client.collections.list(limit=limit, offset=offset)

        return jsonify({
            "collections": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "description": c.description,
                    "document_count": c.document_count,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in collections.data
            ],
            "total": collections.pagination.get("total", 0),
            "limit": collections.pagination.get("limit", limit),
            "offset": collections.pagination.get("offset", offset)
        })

    except MnemosyneError as e:
        print(f"MnemosyneError in list_collections: {type(e).__name__}: {e}")
        return jsonify({"error": str(e), "type": type(e).__name__}), 400
    except Exception as e:
        print(f"Exception in list_collections: {type(e).__name__}: {e}")
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


@app.route('/api/collections', methods=['POST'])
async def create_collection():
    """Create a new collection"""
    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        data = await request.get_json()
        name = data.get('name')
        description = data.get('description')
        metadata = data.get('metadata', {})

        if not name:
            return jsonify({"error": "Missing 'name' field"}), 400

        collection = client.collections.create(
            name=name,
            description=description,
            metadata=metadata
        )

        return jsonify({
            "id": str(collection.id),
            "name": collection.name,
            "description": collection.description,
            "metadata": collection.metadata,
            "created_at": collection.created_at.isoformat() if collection.created_at else None
        }), 201

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/collections/<collection_id>', methods=['GET'])
async def get_collection(collection_id: str):
    """Get a specific collection"""
    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        collection = client.collections.get(collection_id)
        return jsonify({
            "id": str(collection.id),
            "name": collection.name,
            "description": collection.description,
            "document_count": collection.document_count,
            "metadata": collection.metadata,
            "created_at": collection.created_at.isoformat() if collection.created_at else None
        })

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/collections/<collection_id>', methods=['DELETE'])
async def delete_collection(collection_id: str):
    """Delete a collection"""
    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        client.collections.delete(collection_id)
        return jsonify({"message": "Collection deleted successfully"}), 200

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/documents', methods=['GET'])
async def list_documents():
    """List documents (optionally filtered by collection)"""
    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        collection_id = sanitize_optional_param(request.args.get('collection_id'))
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)

        docs = client.documents.list(
            collection_id=collection_id,
            limit=limit,
            offset=offset
        )

        return jsonify({
            "documents": [
                {
                    "id": str(d.id),
                    "collection_id": str(d.collection_id),
                    "title": d.title,
                    "filename": d.filename,
                    "status": d.status,
                    "created_at": d.created_at.isoformat() if d.created_at else None
                }
                for d in docs.data
            ],
            "total": docs.pagination.get("total", 0),
            "limit": docs.pagination.get("limit", limit),
            "offset": docs.pagination.get("offset", offset)
        })

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/documents', methods=['POST'])
async def upload_document():
    """Upload a document (file or URL)"""
    import io

    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        form = await request.form
        collection_id = form.get('collection_id')

        if not collection_id:
            return jsonify({"error": "Missing 'collection_id' field"}), 400

        files = await request.files
        file = files.get('file')

        if file:
            # Read file content into a BytesIO buffer and set name attribute
            # The SDK needs a file-like object with a .name attribute
            file_content = file.stream.read()
            file_buffer = io.BytesIO(file_content)
            file_buffer.name = file.filename  # SDK uses this for the filename

            # Upload file
            doc = client.documents.create(
                collection_id=collection_id,
                file=file_buffer,
                metadata={"filename": file.filename}
            )
        else:
            # Check for URL
            url = form.get('url')
            if not url:
                return jsonify({"error": "Missing 'file' or 'url' field"}), 400

            doc = client.documents.create(
                collection_id=collection_id,
                file=url,
                metadata={"source_url": url}
            )

        return jsonify({
            "id": str(doc.id),
            "collection_id": str(doc.collection_id),
            "title": doc.title,
            "filename": doc.filename,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        }), 201

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/documents/<document_id>', methods=['GET'])
async def get_document(document_id: str):
    """Get document details"""
    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        doc = client.documents.get(document_id)
        return jsonify({
            "id": str(doc.id),
            "collection_id": str(doc.collection_id),
            "title": doc.title,
            "filename": doc.filename,
            "status": doc.status,
            "metadata": doc.metadata,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        })

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/documents/<document_id>/status', methods=['GET'])
async def get_document_status(document_id: str):
    """Get document processing status"""
    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        status = client.documents.get_status(document_id)
        return jsonify({
            "document_id": str(status.document_id),
            "status": status.status,
            "chunk_count": status.chunk_count,
            "total_tokens": status.total_tokens,
            "error_message": status.error_message
        })

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/documents/<document_id>', methods=['DELETE'])
async def delete_document(document_id: str):
    """Delete a document"""
    client = get_sdk_client()
    if not client:
        return jsonify({"error": "SDK not configured"}), 500

    try:
        client.documents.delete(document_id)
        return jsonify({"message": "Document deleted successfully"}), 200

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health')
async def health():
    """Health check endpoint"""
    client = get_sdk_client()
    return jsonify({
        "status": "healthy",
        "sdk_configured": client is not None and config.SDK.API_KEY != ""
    })


@app.route('/api/setup/status', methods=['GET'])
async def get_setup_status():
    """Get SDK configuration status"""
    client = get_sdk_client()
    return jsonify({
        "configured": client is not None and config.SDK.API_KEY != "",
        "backend_url": config.SDK.BASE_URL,
        "has_api_key": config.SDK.API_KEY != ""
    })


@app.route('/api/setup/register', methods=['POST'])
async def register_user():
    """
    Register a new user on the FastAPI backend and get API key.
    This is a proxy endpoint that calls the FastAPI /auth/register endpoint.
    """
    import httpx

    data = await request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Missing 'email' or 'password' field"}), 400

    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{config.SDK.BASE_URL}/auth/register",
                json={"email": email, "password": password},
                timeout=30.0
            )

            if response.status_code == 201:
                result = response.json()
                return jsonify({
                    "api_key": result.get("api_key"),
                    "message": "Registration successful"
                }), 201
            else:
                error_data = response.json()
                return jsonify({"error": error_data.get("detail", "Registration failed")}), response.status_code

    except httpx.RequestError as e:
        return jsonify({"error": f"Failed to connect to backend: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/setup/configure', methods=['POST'])
async def configure_api_key():
    """
    Configure the Flask app with an API key.
    This reinitializes the SDK client with the provided API key.
    """
    from src.api.search import reinitialize_client
    import os

    data = await request.get_json()
    api_key = data.get('api_key')

    if not api_key:
        return jsonify({"error": "Missing 'api_key' field"}), 400

    try:
        print(f"Configuring API key: {api_key[:10]}...")
        os.environ['MNEMOSYNE_API_KEY'] = api_key
        config.SDK.API_KEY = api_key

        success = reinitialize_client(api_key)
        print(f"SDK client reinitialized: {success}")

        if success:
            return jsonify({
                "message": "API key configured successfully",
                "configured": True
            }), 200
        else:
            return jsonify({"error": "Failed to initialize SDK client"}), 500

    except Exception as e:
        print(f"Error configuring API key: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
