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


@app.route('/')
async def home():
    """Render the main application page"""
    return await render_template('index.html')


@app.route('/mnemosyne/api/v1/search/<query>')
async def search(query: str) -> Response:
    """
    Handle streaming search/chat requests (legacy endpoint).
    Maintains compatibility with existing frontend.
    """
    final_query = decode_query(query)

    # Get optional query parameters
    args = request.args
    collection_id = args.get('collection_id')
    session_id = args.get('session_id')
    mode = args.get('mode')

    return Response(
        stream_response(final_query, collection_id=collection_id,
                       session_id=session_id, mode=mode),
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
    Supports collection filtering and multi-turn conversations.
    """
    data = await request.get_json()
    query = data.get('message') or data.get('query')
    collection_id = data.get('collection_id')
    session_id = data.get('session_id')
    mode = data.get('mode')

    if not query:
        return jsonify({"error": "Missing 'message' or 'query' field"}), 400

    return Response(
        stream_response(query, collection_id=collection_id,
                       session_id=session_id, mode=mode),
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
    collection_id = data.get('collection_id')
    mode = data.get('mode')
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
            "total": collections.total,
            "limit": collections.limit,
            "offset": collections.offset
        })

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        collection_id = request.args.get('collection_id')
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
            "total": docs.total,
            "limit": docs.limit,
            "offset": docs.offset
        })

    except MnemosyneError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/documents', methods=['POST'])
async def upload_document():
    """Upload a document (file or URL)"""
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
            # Upload file
            doc = client.documents.create(
                collection_id=collection_id,
                file=file.stream,
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
