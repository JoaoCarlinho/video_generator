"""
Story 2.3: Wan2.5 Inference FastAPI Server
GPU-accelerated video generation service using Wan2.5 model
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import torch
import boto3
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "adgen-model-artifacts")
S3_MODEL_PREFIX = os.getenv("S3_MODEL_PREFIX", "models/wan25/")
MODEL_CACHE_DIR = Path("/tmp/model")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Global model instance
model = None
model_loaded = False


class GenerateRequest(BaseModel):
    """Video generation request schema"""
    prompt: str = Field(..., min_length=1, description="Text prompt for video generation")
    style_spec: Dict[str, Any] = Field(default_factory=dict, description="Style specifications")
    duration: float = Field(default=5.0, ge=1.0, le=10.0, description="Video duration in seconds")
    aspect_ratio: str = Field(default="16:9", description="Video aspect ratio")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    fps: int = Field(default=24, ge=12, le=60, description="Frames per second")


class GenerateResponse(BaseModel):
    """Video generation response schema"""
    status: str
    message: str
    video_url: Optional[str] = None
    generation_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    gpu_available: bool
    gpu_count: int
    gpu_names: list[str]
    model_loaded: bool
    cuda_version: Optional[str] = None


def download_model_from_s3():
    """Download model artifacts from S3 to local cache"""
    logger.info(f"Downloading model from S3: s3://{S3_BUCKET}/{S3_MODEL_PREFIX}")

    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)

        # List all objects in the model prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_MODEL_PREFIX)

        file_count = 0
        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                # Get the file key and construct local path
                file_key = obj['Key']
                relative_path = file_key.replace(S3_MODEL_PREFIX, '', 1)

                if not relative_path:  # Skip if it's just the prefix (folder)
                    continue

                local_file_path = MODEL_CACHE_DIR / relative_path
                local_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Download file
                logger.info(f"Downloading: {file_key} -> {local_file_path}")
                s3_client.download_file(S3_BUCKET, file_key, str(local_file_path))
                file_count += 1

        logger.info(f"✅ Downloaded {file_count} files from S3")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download model from S3: {e}")
        raise


def load_model():
    """Load Wan2.5 model into GPU memory"""
    global model, model_loaded

    logger.info("Loading Wan2.5 model...")

    # Check GPU availability
    if not torch.cuda.is_available():
        logger.warning("⚠️  CUDA not available! Model will run on CPU (slow)")
    else:
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(f"✅ GPU available: {gpu_name}")

    try:
        # TODO: Replace with actual Wan2.5 model loading
        # This is a placeholder - actual implementation depends on Wan2.5 API

        # For now, just verify model files exist
        config_file = MODEL_CACHE_DIR / "config.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Model config not found at {config_file}")

        logger.info("✅ Model files verified")

        # Placeholder: Load actual model here
        # from diffusers import WanPipeline
        # model = WanPipeline.from_pretrained(str(MODEL_CACHE_DIR))
        # if torch.cuda.is_available():
        #     model = model.to("cuda")

        model_loaded = True
        logger.info("✅ Model loaded successfully")

    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("🚀 Starting Wan2.5 Inference Service...")

    try:
        # Download model from S3 if not already cached
        if not MODEL_CACHE_DIR.exists() or not list(MODEL_CACHE_DIR.iterdir()):
            download_model_from_s3()
        else:
            logger.info("✅ Model already cached locally")

        # Load model into memory
        load_model()

        logger.info("✅ Service ready to accept requests")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("👋 Shutting down Wan2.5 Inference Service...")


# Create FastAPI app
app = FastAPI(
    title="Wan2.5 Inference Service",
    description="GPU-accelerated video generation using Wan2.5 model",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for ALB monitoring
    Returns GPU status and model readiness
    """
    gpu_available = torch.cuda.is_available()
    gpu_count = torch.cuda.device_count() if gpu_available else 0
    gpu_names = []

    if gpu_available:
        gpu_names = [torch.cuda.get_device_name(i) for i in range(gpu_count)]

    cuda_version = torch.version.cuda if gpu_available else None

    return HealthResponse(
        status="healthy" if (gpu_available and model_loaded) else "degraded",
        gpu_available=gpu_available,
        gpu_count=gpu_count,
        gpu_names=gpu_names,
        model_loaded=model_loaded,
        cuda_version=cuda_version
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate video using Wan2.5 model

    Args:
        request: Video generation parameters
        background_tasks: FastAPI background tasks for async processing

    Returns:
        GenerateResponse with video URL and metadata
    """
    if not model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service is starting up or encountered an error."
        )

    if not torch.cuda.is_available():
        logger.warning("⚠️  Generating video on CPU (will be slow)")

    try:
        logger.info(f"🎬 Generating video: prompt='{request.prompt}', duration={request.duration}s")

        # TODO: Replace with actual Wan2.5 inference
        # This is a placeholder implementation

        # Simulate video generation
        # result = model(
        #     prompt=request.prompt,
        #     num_frames=int(request.duration * request.fps),
        #     guidance_scale=7.5,
        #     seed=request.seed
        # )

        # Placeholder response
        return GenerateResponse(
            status="success",
            message="Video generation completed (placeholder)",
            video_url="https://placeholder-url.com/video.mp4",
            generation_time=15.0,
            metadata={
                "prompt": request.prompt,
                "duration": request.duration,
                "aspect_ratio": request.aspect_ratio,
                "fps": request.fps,
                "seed": request.seed,
                "gpu_used": torch.cuda.is_available()
            }
        )

    except Exception as e:
        logger.error(f"❌ Video generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Wan2.5 Inference Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "generate": "/generate",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    # Run uvicorn server
    uvicorn.run(
        "serve:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
