"""
Story 2.3: Wan2.5 Inference FastAPI Server
GPU-accelerated video generation service using Wan2.5 model via diffusers

Uses the WanPipeline from HuggingFace diffusers for text-to-video generation.
Optimized for NVIDIA A10G GPUs (24GB VRAM) on AWS g5.xlarge instances.
"""

import os
import logging
import time
import uuid
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import torch
import boto3
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import uvicorn
import imageio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "adgen-model-artifacts")
S3_MODEL_PREFIX = os.getenv("S3_MODEL_PREFIX", "models/wan25/")
S3_OUTPUT_BUCKET = os.getenv("S3_OUTPUT_BUCKET", "adgen-video-outputs")
S3_OUTPUT_PREFIX = os.getenv("S3_OUTPUT_PREFIX", "generated/")
MODEL_CACHE_DIR = Path("/tmp/model")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Model configuration - use Wan2.1-T2V-1.3B for 24GB GPU compatibility
MODEL_ID = os.getenv("MODEL_ID", "Wan-AI/Wan2.1-T2V-1.3B-Diffusers")
USE_LOCAL_MODEL = os.getenv("USE_LOCAL_MODEL", "true").lower() == "true"

# Video generation defaults
DEFAULT_HEIGHT = 480
DEFAULT_WIDTH = 848  # 16:9 aspect ratio at 480p
DEFAULT_NUM_FRAMES = 81  # ~3.4 seconds at 24fps
DEFAULT_FPS = 24
DEFAULT_GUIDANCE_SCALE = 5.0
DEFAULT_NUM_INFERENCE_STEPS = 50

# Global model instance
pipeline = None
model_loaded = False
s3_client = None


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


def get_aspect_ratio_dimensions(aspect_ratio: str) -> tuple[int, int]:
    """Get width and height for the given aspect ratio at 480p."""
    ratios = {
        "16:9": (848, 480),
        "9:16": (480, 848),  # Portrait/TikTok
        "1:1": (480, 480),
        "4:3": (640, 480),
        "3:4": (480, 640),
    }
    return ratios.get(aspect_ratio, (848, 480))


def calculate_num_frames(duration: float, fps: int = DEFAULT_FPS) -> int:
    """Calculate number of frames for given duration.

    Wan models work best with frame counts that are multiples of 4 + 1.
    E.g., 17, 33, 49, 65, 81, 97, 113 frames.
    """
    target_frames = int(duration * fps)
    # Round to nearest valid frame count (4n + 1)
    n = round((target_frames - 1) / 4)
    return max(17, min(4 * n + 1, 121))  # Min 17 frames, max 121 frames


def load_model():
    """Load Wan model into GPU memory using diffusers WanPipeline."""
    global pipeline, model_loaded, s3_client

    # Initialize S3 client
    s3_client = boto3.client('s3', region_name=AWS_REGION)

    logger.info("Loading Wan video generation model...")
    logger.info(f"Model ID: {MODEL_ID}")
    logger.info(f"Use local model: {USE_LOCAL_MODEL}")

    # Check GPU availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        logger.info(f"✅ GPU available: {gpu_name} ({gpu_memory:.1f}GB)")
    else:
        logger.warning("⚠️  CUDA not available! Model will run on CPU (slow)")

    try:
        # Import diffusers components
        from diffusers import AutoencoderKLWan, WanPipeline
        from diffusers.schedulers import UniPCMultistepScheduler

        # Determine model path
        if USE_LOCAL_MODEL and MODEL_CACHE_DIR.exists():
            model_path = str(MODEL_CACHE_DIR)
            logger.info(f"Loading model from local cache: {model_path}")
        else:
            model_path = MODEL_ID
            logger.info(f"Loading model from HuggingFace: {model_path}")

        # Load VAE in float32 for better quality (as recommended)
        logger.info("Loading VAE...")
        vae = AutoencoderKLWan.from_pretrained(
            model_path,
            subfolder="vae",
            torch_dtype=torch.float32
        )

        # Load pipeline in bfloat16 for memory efficiency
        logger.info("Loading WanPipeline...")
        pipeline = WanPipeline.from_pretrained(
            model_path,
            vae=vae,
            torch_dtype=torch.bfloat16
        )

        # Configure scheduler with flow_shift for better quality
        # flow_shift=5.0 for 720p, 3.0 for 480p
        flow_shift = 3.0  # Using 480p
        pipeline.scheduler = UniPCMultistepScheduler.from_config(
            pipeline.scheduler.config,
            flow_shift=flow_shift
        )

        # Move to GPU
        pipeline = pipeline.to(device)

        # Enable memory optimizations for 24GB GPU
        if device == "cuda":
            logger.info("Enabling VAE slicing for memory optimization...")
            pipeline.enable_vae_slicing()

            # For models larger than 24GB, enable CPU offload
            # pipeline.enable_model_cpu_offload()

        model_loaded = True
        logger.info("✅ Wan model loaded successfully!")

        # Log memory usage
        if device == "cuda":
            allocated = torch.cuda.memory_allocated() / 1e9
            reserved = torch.cuda.memory_reserved() / 1e9
            logger.info(f"GPU memory: {allocated:.2f}GB allocated, "
                       f"{reserved:.2f}GB reserved")

    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}", exc_info=True)
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


def save_video_to_s3(frames: np.ndarray, fps: int, video_id: str) -> str:
    """Save generated video frames to S3 and return the URL.

    Args:
        frames: Video frames as numpy array (T, H, W, C) in uint8
        fps: Frames per second
        video_id: Unique identifier for the video

    Returns:
        S3 URL of the uploaded video
    """
    global s3_client

    # Create temporary file for video
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Write frames to MP4 using imageio
        logger.info(f"Encoding video: {frames.shape[0]} frames at {fps}fps")
        imageio.mimwrite(
            tmp_path,
            frames,
            fps=fps,
            codec='libx264',
            quality=8,  # High quality
            output_params=['-pix_fmt', 'yuv420p']  # Compatibility
        )

        # Generate S3 key
        s3_key = f"{S3_OUTPUT_PREFIX}{video_id}.mp4"

        # Upload to S3
        logger.info(f"Uploading video to s3://{S3_OUTPUT_BUCKET}/{s3_key}")
        s3_client.upload_file(
            tmp_path,
            S3_OUTPUT_BUCKET,
            s3_key,
            ExtraArgs={
                'ContentType': 'video/mp4',
                'CacheControl': 'max-age=31536000'
            }
        )

        # Generate presigned URL (valid for 1 hour)
        video_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_OUTPUT_BUCKET, 'Key': s3_key},
            ExpiresIn=3600
        )

        logger.info(f"✅ Video uploaded successfully: {s3_key}")
        return video_url

    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/generate", response_model=GenerateResponse)
async def generate_video(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """Generate video using Wan model via diffusers pipeline.

    Performs text-to-video generation using the loaded WanPipeline,
    saves the result to S3, and returns the video URL.
    """
    global pipeline

    if not model_loaded or pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service is starting up."
        )

    start_time = time.time()
    video_id = str(uuid.uuid4())

    try:
        # Get dimensions for aspect ratio
        width, height = get_aspect_ratio_dimensions(request.aspect_ratio)

        # Calculate number of frames
        num_frames = calculate_num_frames(request.duration, request.fps)
        actual_duration = num_frames / request.fps

        logger.info(
            f"🎬 Generating video: prompt='{request.prompt[:50]}...', "
            f"duration={actual_duration:.1f}s, "
            f"frames={num_frames}, size={width}x{height}"
        )

        # Set random seed for reproducibility
        generator = None
        if request.seed is not None:
            generator = torch.Generator(device="cuda").manual_seed(request.seed)
            logger.info(f"Using seed: {request.seed}")

        # Build enhanced prompt with style specifications
        enhanced_prompt = request.prompt
        if request.style_spec:
            style_parts = []
            if request.style_spec.get("camera_style"):
                style_parts.append(request.style_spec["camera_style"])
            if request.style_spec.get("lighting_direction"):
                style_parts.append(request.style_spec["lighting_direction"])
            if request.style_spec.get("mood_atmosphere"):
                style_parts.append(request.style_spec["mood_atmosphere"])
            if style_parts:
                enhanced_prompt = f"{request.prompt}. {', '.join(style_parts)}"

        logger.info(f"Enhanced prompt: {enhanced_prompt[:100]}...")

        # Run inference
        with torch.inference_mode():
            output = pipeline(
                prompt=enhanced_prompt,
                height=height,
                width=width,
                num_frames=num_frames,
                num_inference_steps=DEFAULT_NUM_INFERENCE_STEPS,
                guidance_scale=DEFAULT_GUIDANCE_SCALE,
                generator=generator,
            )

        # Extract frames from output
        # WanPipeline returns frames in shape (1, T, C, H, W) or (T, H, W, C)
        frames = output.frames[0]  # Get first batch

        # Convert to numpy uint8 if needed
        if isinstance(frames, torch.Tensor):
            frames = frames.cpu().numpy()

        # Ensure correct shape (T, H, W, C) and dtype
        if frames.ndim == 4 and frames.shape[1] == 3:
            # Shape is (T, C, H, W), transpose to (T, H, W, C)
            frames = np.transpose(frames, (0, 2, 3, 1))

        if frames.dtype != np.uint8:
            if frames.max() <= 1.0:
                frames = (frames * 255).astype(np.uint8)
            else:
                frames = frames.astype(np.uint8)

        logger.info(f"Generated {frames.shape[0]} frames, shape: {frames.shape}")

        # Save to S3
        video_url = save_video_to_s3(frames, request.fps, video_id)

        # Calculate timing
        generation_time = time.time() - start_time

        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info(
            f"✅ Video generated in {generation_time:.1f}s: {video_id}"
        )

        return GenerateResponse(
            status="success",
            message="Video generation completed",
            video_url=video_url,
            generation_time=generation_time,
            metadata={
                "video_id": video_id,
                "prompt": request.prompt,
                "enhanced_prompt": enhanced_prompt[:200],
                "duration": actual_duration,
                "num_frames": num_frames,
                "width": width,
                "height": height,
                "aspect_ratio": request.aspect_ratio,
                "fps": request.fps,
                "seed": request.seed,
                "inference_steps": DEFAULT_NUM_INFERENCE_STEPS,
                "guidance_scale": DEFAULT_GUIDANCE_SCALE,
                "gpu_used": torch.cuda.is_available()
            }
        )

    except torch.cuda.OutOfMemoryError as e:
        logger.error(f"❌ GPU OOM error: {e}")
        torch.cuda.empty_cache()
        raise HTTPException(
            status_code=507,
            detail="GPU out of memory. Try reducing duration or resolution."
        )

    except Exception as e:
        logger.error(f"❌ Video generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Video generation failed: {str(e)}"
        )


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
