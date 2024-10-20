import asyncio
import json
import time

from quart import Quart, request, jsonify, render_template, Response
from quart_cors import cors
from src.config import Config
from src.service.MnemsoyneService import MnemsoyneService
from src.service.LLMService import LLMService

app = Quart(__name__, template_folder='../templates', static_folder='../static')
app = cors(app)

mnemsoyne_service = MnemsoyneService(Config())
llm_service = LLMService(Config())

@app.route('/')
async def home():
    return await render_template('index.html')

@app.route('/mnemosyne/api/v1/search/<query>')
async def search(query):
    query_parts = query.split('-')
    decoded_query = []
    for part in query_parts:
        if part.isalnum() and not part.isalpha() and not part.isdigit():
            break
        decoded_query.append(part)
    final_query = ' '.join(decoded_query)
    async def generate_stream(final_query):
        retrieved_info = mnemsoyne_service.retrieve_knowlede(final_query)
        async for chunk in retrieved_info:
            if isinstance(chunk, str) and chunk.startswith("{"):
                yield f'data: {chunk}\n\n'
            else:
                # Ensure we're working with complete lines
                # chunk_str = str(chunk).strip()
                # if chunk_str:
                #     yield f'data: {chunk_str}\n\n'
                lines = chunk.split('\n')
                for line in lines:
                    if line.strip():  # Only send non-empty lines
                        yield f'data: {line}\n\n'
                    await asyncio.sleep(0.07)  # Use asyncio.sleep instead of time.sleep
        yield ''

    return Response(
        generate_stream(final_query),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

if __name__ == '__main__':
    app.run()