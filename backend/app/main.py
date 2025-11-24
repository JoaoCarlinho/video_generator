"""FastAPI application entry point."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.database.connection import test_connection, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
# redirect_slashes=False prevents automatic redirects between /path and /path/
# This is crucial for Lambda Function URLs which also handle redirects
app = FastAPI(
    title="AI Ad Video Generator",
    description="Generate professional ad videos with product compositing",
    version="1.0.0",
    redirect_slashes=False
)

# Middleware to prevent redirect loops
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class NoRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Prevent 307 redirects that cause loops
        if response.status_code == 307:
            location = response.headers.get("location", "")
            # If redirecting to the same path, return 404 instead
            if location.rstrip('/') == str(request.url).rstrip('/'):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Not found"}, status_code=404)
        return response

app.add_middleware(NoRedirectMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite frontend dev
        "http://localhost:5176",  # Vite frontend dev (alternate)
        "http://localhost:3000",  # Alternative dev port
        "https://localhost:5173",
        "http://adgen-frontend-1763351975.s3-website-us-east-1.amazonaws.com",  # Production frontend
        "*",  # Allow all origins for now (remove in production if needed)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and log them for debugging."""
    errors = exc.errors()
    logger.error(f"Validation error on {request.method} {request.url.path}:")
    for error in errors:
        logger.error(f"  Field: {error.get('loc')}, Error: {error.get('msg')}, Type: {error.get('type')}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "message": "Validation error - check field requirements"
        }
    )


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("🚀 Starting up AI Ad Video Generator...")

    # Initialize database connection
    init_db()

    # Test database connection
    db_connected = test_connection()
    if db_connected:
        logger.info("✅ Database connection established and tested")
    else:
        logger.warning("⚠️ Database connection could not be established - running in degraded mode")

    logger.info("✅ Server startup complete")


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
from app.api import campaigns, generation, storage, uploads, brands, products, editing, providers, creatives, admin
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(creatives.router, prefix="/api/campaigns", tags=["creatives"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])
app.include_router(storage.router, prefix="/api", tags=["storage"])
app.include_router(uploads.router, prefix="/api", tags=["uploads"])
app.include_router(brands.router, prefix="/api/brands", tags=["brands"])
app.include_router(products.router, prefix="/api", tags=["products"])
app.include_router(providers.router, tags=["providers"])
app.include_router(editing.router)  # Already has /api/campaigns prefix
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )

