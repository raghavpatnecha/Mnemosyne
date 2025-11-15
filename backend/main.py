"""
Mnemosyne API - FastAPI application entry point
Week 1: Basic CRUD with authentication
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import create_tables

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Open-source RAG-as-a-Service platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
from backend.api import auth, collections, documents

app.include_router(auth.router, prefix="/api/v1")
app.include_router(collections.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )
