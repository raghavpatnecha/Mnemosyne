import asyncio
import json
from typing import List, AsyncGenerator
from src.config import Config
from src.service.MnemsoyneService import MnemsoyneService
from src.service.LLMService import LLMService, LLMMode

config = Config()
mnemosyne_service = MnemsoyneService(config)
llm_service = LLMService(config)

# Set the LLMMode manually here
LLM_MODE = LLMMode.SYNC  # or LLMMode.ASYNC

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
                print(f"Unexpected chunk type: {type(chunk)}")

        yield ''
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        yield f'data: {{"error": "An error occurred while processing your request"}}\n\n'