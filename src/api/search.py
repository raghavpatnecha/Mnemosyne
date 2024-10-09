from flask import Flask, request, jsonify, render_template
from src.config import Config
from src.service.MnemsoyneService import MnemsoyneService
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
    # Split the query by '-'
    query_parts = query.split('-')

    # Rebuild the query while excluding trailing alphanumeric parts
    decoded_query = []
    for part in query_parts:
        # If part contains both letters and numbers (likely an ID), stop processing further
        if part.isalnum() and not part.isalpha() and not part.isdigit():
            break
        decoded_query.append(part)

    # Join the valid parts with spaces to form the full query
    final_query = ' '.join(decoded_query)
    #decoded_query = query.replace('-', ' ')
    #results = mnemsoyne_service.retrieve_knowlede(final_query)
    # Mock response
    mock_response = {
    "answer": "> **GymLytics: AI-powered Realtime Workout Analytics**\n\nGymLytics is an AI-powered application that provides real-time workout analytics to help users optimize their fitness routines. It uses machine learning algorithms to analyze key points associated with the wrists, elbows, shoulders, and ankles during various exercises.\n\n> **Posture Correction:** GymLytics employs a sophisticated approach that combines keypoint detection, analysis, and limb angle assessment to offer a detailed understanding of each exercise. Taking the example of planks, GymLytics meticulously analyzes the key points corresponding to the shoulder, hip, and ankle. By examining the spatial relationships among these crucial points, GymLytics derives precise information about the participant\u2019s body alignment during the exercise.\n\n> **Performance Optimization:** The application significantly boosts the efficiency of keypoint analysis by tailoring the input to include only the relevant skeletal markers for each exercise. This targeted approach enhances the speed of keypoint analysis and ensures that the computational resources are allocated precisely where needed, contributing to a more optimized and responsive performance overall.\n\n> **Key Features:**\n\n*   Key point detection and analysis\n*   Limb angle assessment\n*   Posture correction\n*   Performance optimization\n\n> **References:**\n\n[Mediapipe by Google](https://github.com/google/mediapipe)\n\n> **Image:**\n\n![Motion tracking with MediaPipe](https://miro.medium.com/v2/1*PD2VI55HZut6yGXXDyTKCg.gif)\n\n> **Follow-up Questions:*\n\n*   How does GymLytics handle user data privacy?\n\n*   Can GymLytics be integrated with popular fitness tracking devices?\n\n*   What are the future plans for GymLytics in terms of feature development and expansion?\n\n> **Sources:**\n\n[Mediapipe by Google](https://github.com/google/mediapipe)\n\n",
    "code_blocks": "> **Code Block 1:**\n\n```python\nimport mediapipe as mp\nmp_pose = mp.solutions.pose\npose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)\n\n> **Code Block 2:**\n\n```python\nfrom gymlytics import GymLytics\ngymlytics = GymLytics()\ngymlytics.analyze_exercise()\n```\n",
    "confidence_score": 0.95,
    "follow_up": [
        "How does GymLytics handle user data privacy?",
        "Can GymLytics be integrated with popular fitness tracking devices?",
        "What are the future plans for GymLytics in terms of feature development and expansion?"
    ],
    "images": [
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
    "query": "what is gymlytics explain with add code",
    "reason": "The provided information from the CONTEXT is sufficient to answer the query about GymLytics.",
    "response_time": 0,
    "sources": [
        {
            "title": "GymLytics: AI-powered Realtime Workout Analytics | by Akshay Bahadur 👨\u200d🚀 | Medium",
            "url": "https://akshaybahadur.medium.com/gymlytics-519caa05f045",
            "content": "GymLytics is an AI-powered tool that provides real-time workout analytics to help users optimize their fitness routines."
        },
        {
            "content": "A machine learning framework for media processing.",
            "title": "Mediapipe by Google",
            "url": "https://github.com/google/mediapipe"
        }
    ]
}
    return jsonify(mock_response)

if __name__ == '__main__':
    app.run(debug=False)
