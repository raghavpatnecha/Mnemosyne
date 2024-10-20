import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config import Config
from src.service.MnemsoyneService import MnemsoyneService
from src.service.LLMService import LLMService
import uvicorn

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

mnemsoyne_service = MnemsoyneService(Config())
llm_service = LLMService(Config())


@app.get("/")
async def home():
    return {"message": "Welcome to the Mnemosyne RAG Search API"}


@app.get("/mnemosyne/api/v1/search/{query}")
async def search(query: str, request: Request):
    query_parts = query.split('-')
    decoded_query = []
    for part in query_parts:
        if part.isalnum() and not part.isalpha() and not part.isdigit():
            break
        decoded_query.append(part)

    final_query = ' '.join(decoded_query)
    async def event_generator():
        decoded_query = query.replace("-", " ")
        retrieved_info = mnemsoyne_service.retrieve_knowlede(final_query)
        async for chunk in retrieved_info:
            if await request.is_disconnected():
                break
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
