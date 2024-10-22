import asyncio
import json

from fastapi import FastAPI, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config import Config
from src.service.MnemsoyneService import MnemsoyneService
from src.service.LLMService import LLMService, LLMMode
import uvicorn
from typing import Optional

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

config = Config()
mnemosyne_service = MnemsoyneService(config)
llm_service = LLMService(config)

@app.get("/")
async def home():
    return {"message": "Welcome to the Mnemosyne RAG Search API"}

def decode_query(query: str) -> str:
    query_parts = query.split('-')
    decoded_query = []
    for part in query_parts:
        if part.isalnum() and not part.isalpha() and not part.isdigit():
            break
        decoded_query.append(part)
    return ' '.join(decoded_query)

@app.get("/mnemosyne/api/v1/search/{query}")
async def search(query: str, request: Request, mode: Optional[str] = Query(None, enum=['sync', 'async'])):
    final_query = decode_query(query)
    llm_mode = LLMMode.ASYNC if mode == 'async' else LLMMode.SYNC

    async def event_generator():
        retrieved_info = mnemosyne_service.retrieve_knowlede(final_query, llm_mode)
        async for chunk in retrieved_info:
            if await request.is_disconnected():
                break
            if isinstance(chunk, str):
                yield f"data: {chunk}\n\n"
            elif isinstance(chunk, dict):
                yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/insert")
async def insert_endpoint(url: str = Query(..., description="URL to insert")):
    if url:
        results = await mnemosyne_service.insert_knowledge(url)
        return JSONResponse(content=results)
    else:
        return JSONResponse(content={'error': 'No URL provided'}, status_code=400)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)