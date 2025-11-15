"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database.connection import test_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Ad Video Generator",
    description="Generate professional ad videos with product compositing",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite frontend dev
        "http://localhost:5176",  # Vite frontend dev (alternate)
        "http://localhost:3000",  # Alternative dev port
        "https://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    try:
        logger.info("🚀 Starting up AI Ad Video Generator...")
        
        # Test database connection
        if test_connection():
            logger.info("✅ All systems ready!")
        else:
            logger.warning("⚠️ Database connection failed - some features may not work")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        # Don't crash - allow server to start anyway


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "environment": settings.environment,
        "debug": settings.debug
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "AI Ad Video Generator",
        "version": "1.0.0",
        "status": "running"
    }


# Import and include routers
from app.api import projects, generation
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )

