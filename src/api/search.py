from flask import Flask, request, jsonify
from config import Config
from service.MnemsoyneService import MnemsoyneService

app = Flask(__name__)
mnemsoyne_service = MnemsoyneService(Config())

# Endpoint for searching the indexed data
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

if __name__ == '__main__':
    app.run(debug=True)
