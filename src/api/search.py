import asyncio
import json
from typing import List, AsyncGenerator

from quart import Quart, render_template, Response
from quart_cors import cors
from src.config import Config
from src.service.MnemsoyneService import MnemsoyneService
from src.service.LLMService import LLMService, LLMMode

app = Quart(__name__, template_folder='../templates', static_folder='../static')
app = cors(app)

config = Config()
mnemosyne_service = MnemsoyneService(config)
llm_service = LLMService(config)

# Set the LLMMode manually here
LLM_MODE = LLMMode.SYNC  # or LLMMode.ASYNC


@app.route('/')
async def home():
    return await render_template('index.html')


def decode_query(query: str) -> str:
    """Decode the query string."""
    query_parts = query.split('-')
    decoded_parts: List[str] = []
    for part in query_parts:
        if part.isalnum() and not part.isalpha() and not part.isdigit():
            break
        decoded_parts.append(part)
    return ' '.join(decoded_parts)


async def stream_response(query: str) -> AsyncGenerator[str, None]:
    """Generate streaming response for the given query."""
    try:
        retrieved_info = mnemosyne_service.retrieve_knowlede(query, LLM_MODE)
        async for chunk in retrieved_info:
            if isinstance(chunk, str):
                if chunk.startswith("{"):
                    yield f'data: {chunk}\n\n'
                else:
                    lines = chunk.split('\n')
                    for line in lines:
                        if line.strip():
                            yield f'data: {line}\n\n'
                            await asyncio.sleep(0.12)
            elif isinstance(chunk, dict):
                yield f'data: {json.dumps(chunk)}\n\n'
            else:
                app.logger.warning(f"Unexpected chunk type: {type(chunk)}")

        yield 'data: [DONE]\n\n'
    except Exception as e:
        app.logger.error(f"Error processing query: {str(e)}")
        yield f'data: {{"error": "An error occurred while processing your request"}}\n\n'


@app.route('/mnemosyne/api/v1/search/<query>')
async def search(query: str) -> Response:
    """Handle search requests."""
    final_query = decode_query(query)
    return Response(
        stream_response(final_query),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


if __name__ == '__main__':
    app.run()