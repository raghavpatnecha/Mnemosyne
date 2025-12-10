"""
Mnemosyne API - FastAPI application entry point
Weeks 1-5: Complete RAG-as-a-Service platform with advanced features
"""

import logging

# Configure logging to show INFO level
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import create_tables
from backend.middleware.rate_limiter import setup_rate_limiting
from backend.utils.error_handlers import setup_error_handlers

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Open-source RAG-as-a-Service platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "authentication", "description": "User registration and API key management"},
        {"name": "collections", "description": "Collection management"},
        {"name": "documents", "description": "Document upload and management"},
        {"name": "retrievals", "description": "Search and retrieval"},
        {"name": "chat", "description": "Conversational AI"}
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup rate limiting (Week 5)
setup_rate_limiting(app)

# Setup error handlers (Week 5)
setup_error_handlers(app)


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    create_tables()
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"API Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "database": "connected"  # Will add actual check in Week 2
    }


# Import and register routers
from backend.api import auth, collections, documents, retrievals, chat

app.include_router(auth.router, prefix="/api/v1")
app.include_router(collections.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(retrievals.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


# Security is now handled by HTTPBearer in deps.py
# FastAPI will automatically generate the OpenAPI schema with security


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )
