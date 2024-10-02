import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).absolute().parents[1].absolute()
sys.path.insert(0, str(PROJECT_ROOT))
from flask import Flask, request, jsonify, render_template
from config import Config
from service.MnemsoyneService import MnemsoyneService
import random
import string

app = Flask(__name__, template_folder='../templates')
mnemsoyne_service = MnemsoyneService(Config())

# Endpoint for searching the indexed data
def generate_unique_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_endpoint():
    query = request.args.get('query', '')
    if query:
        results = mnemsoyne_service.retrieve_knowlede(query)
        return jsonify(results)
    else:
        return jsonify({'error': 'No query provided'}), 400
    
@app.route('/insert', methods=['GET'])
def insert_endpoint():
    url = request.args.get('query', '')
    if url:
        results = mnemsoyne_service.insert_knowledge(url)
        return jsonify(results)
    else:
        return jsonify({'error': 'No URL provided'}), 400


@app.route('/search_mock/<query>')
def search_mock(query):
    # Decode the query
    decoded_query = query.split('-')[0].replace('-', ' ')

    # Mock response
    mock_response = {
        "query": decoded_query,
        "images": [
            {"url": "https://example.com/image1.jpg", "description": "Example Image 1"},
            {"url": "https://example.com/image2.jpg", "description": "Example Image 2"},
            {"url": "https://example.com/image3.jpg", "description": "Example Image 3"},
        ],
        "sources": [
            {"title": "Source 1", "url": "https://example.com/source1", "content": "Content from source 1..."},
            {"title": "Source 2", "url": "https://example.com/source2", "content": "Content from source 2..."},
            {"title": "Source 3", "url": "https://example.com/source3", "content": "Content from source 3..."},
        ],
        "answer": f"This is a mock answer for the query: {decoded_query}. It would contain a summary of information from various sources.",
        "response_time": 0.5
    }
    return jsonify(mock_response)

if __name__ == '__main__':
    app.run(debug=False)
