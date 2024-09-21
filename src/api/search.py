from flask import Flask, request, jsonify
from config import Config
from service.LangchainService import LangchainService

app = Flask(__name__)
langchain_service = LangchainService(Config())

# Endpoint for searching the indexed data
@app.route('/search', methods=['GET'])
def search_endpoint():
    query = request.args.get('query', '')
    if query:
        results = langchain_service.search(query)
        return jsonify(results)
    else:
        return jsonify({'error': 'No query provided'}), 400

if __name__ == '__main__':
    app.run(debug=True)
