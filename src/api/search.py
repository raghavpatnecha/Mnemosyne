import json
import time

from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from joblib import executor

from src.config import Config
from src.service.MnemsoyneService import MnemsoyneService
from src.service.LLMService import LLMService
import random
import string
from flask_cors import CORS
app = Flask(__name__, template_folder='../templates',static_folder='../static')
CORS(app)
mnemsoyne_service = MnemsoyneService(Config())
llm_service = LLMService(Config())

# Endpoint for searching the indexed data
def generate_unique_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search/<query>')
def search(query):
    query_parts = query.split('-')
    decoded_query = []
    for part in query_parts:
        if part.isalnum() and not part.isalpha() and not part.isdigit():
            break
        decoded_query.append(part)

    final_query = ' '.join(decoded_query)
    def generate_stream(final_query):
        retrieved_info = mnemsoyne_service.retrieve_knowlede(final_query)
        for chunk in llm_service.query_knowledge(retrieved_info, final_query, model_name=Config.LLM.MODEL_NAME):
            if chunk.startswith("{"):
                yield f'data: {chunk}\n\n'
            else:
                lines = chunk.split('\n')
                for line in lines:
                    if line.strip():  # Only send non-empty lines
                        yield f'data: {line}\n\n'
                        time.sleep(0.12)
        yield ''

    return Response(generate_stream(final_query),
                    mimetype='text/event-stream')


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
    query_parts = query.split('-')
    decoded_query = []
    for part in query_parts:
        if part.isalnum() and not part.isalpha() and not part.isdigit():
            break
        decoded_query.append(part)

    final_query = ' '.join(decoded_query)

    def generate_stream():
        # Simulating the streaming process
        yield 'data: {"stream_start": true}\n\n'

        # Simulating chunks of streamed content
        content_chunks = [
            "**GymLytics: AI-powered Realtime Workout Analytics**\n",
            "=====================================================\n\n",
            "**Overview**\n",
            "------------\n\n",
            "GymLytics is an AI-powered tool that provides real-time workout analytics ",
            "to help users track their progress and improve their fitness routines. ",
            "The tool uses computer vision concepts, specifically the Mediapipe library, ",
            "to analyze user movements and provide "
        ]

        for chunk in content_chunks:
            yield f'data: {chunk}\n\n'

        yield 'data: {"stream_end": true}\n\n'

        # Simulating the final JSON payload
        final_json = {
            "reason": "The provided context appears to be an article about GymLytics, an AI-powered real-time workout analytics system.",
            "confidence_score": 0.95,
            "sources": [
                {
                    "title": "GymLytics",
                    "url": "https://akshaybahadur.medium.com/gymlytics-519caa05f045",
                    "content": "A gym user has to depend on a gym trainer or an experienced gym-goer for posture correction. Several users might develop injuries due to the absence of proper guidance."
                },
                {
                    "title": "Mediapipe by Google",
                    "url": "https://github.com/google/mediapipe",
                    "content": "Mediapipe is a library that enables developers like me to integrate advanced computer vision concepts seamlessly with the system."
                }
            ],
            "follow_up": [
                "What are some potential applications of GymLytics beyond traditional workout tracking?",
                "How does Mediapipe handle edge cases in motion tracking?",
                "How does GymLytics handle user data privacy?",
                "Can GymLytics be integrated with popular fitness tracking devices?",
                "What are the future plans for GymLytics in terms of feature development and expansion?"
            ],
            "images": [
                {
                    "url": "https://miro.medium.com/v2/1*wtnk9nKW67EUGPEML200Ew.gif",
                    "description": "A screenshot of the GymLytics interface"
                },
                {
                    "url": "https://miro.medium.com/v2/1*AFu6VBnkbiu10W35k0HkGQ.gif",
                    "description": "An animation demonstrating Mediapipe's motion tracking capabilities"
                },
                {
                    "url": "https://miro.medium.com/v2/1*ZeWdpB0tfNxF6WKEGFeCkg.png",
                    "description": "Image of the GymLytics interface"
                },
                {
                    "url": "https://miro.medium.com/v2/1*AnJEvyaKsBp0Tk8MUn0vfw.png",
                    "description": "Image of a user using GymLytics"
                },
                {
                    "description": "Motion tracking with MediaPipe",
                    "url": "https://miro.medium.com/v2/1*PD2VI55HZut6yGXXDyTKCg.gif"
                }
            ],
            "timestamp": "2024-10-09T12:36:07.998452",
            "response_time": 0
        }

        yield f'data: {json.dumps(final_json)}\n\n'

    return Response(generate_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=False)
