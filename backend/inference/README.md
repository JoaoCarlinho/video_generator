# Wan2.5 Inference Container

GPU-accelerated video generation service using Wan2.5 model.

## Story 2.3: Build Wan2.5 Inference Container Image

This container provides a FastAPI service for generating videos using the Wan2.5 model on NVIDIA GPUs.

## Prerequisites

- Docker with NVIDIA GPU support (nvidia-docker)
- NVIDIA GPU with CUDA 11.8+ support
- AWS credentials (for S3 model download)
- Model artifacts in S3: `s3://adgen-model-artifacts/models/wan25/`

## Build

```bash
cd backend/inference
docker build -t wan25-inference .
```

Build time: ~10-15 minutes (first build)
Image size: ~8-10 GB

## Run Locally

```bash
docker run --gpus all \
  -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e S3_BUCKET=adgen-model-artifacts \
  -e S3_MODEL_PREFIX=models/wan25/ \
  wan25-inference
```

## Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "gpu_available": true,
  "gpu_count": 1,
  "gpu_names": ["NVIDIA A10G"],
  "model_loaded": true,
  "cuda_version": "11.8"
}
```

### Generate Video
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene mountain landscape at sunset",
    "style_spec": {"style": "cinematic"},
    "duration": 5.0,
    "aspect_ratio": "16:9",
    "fps": 24
  }'
```

Response:
```json
{
  "status": "success",
  "message": "Video generation completed",
  "video_url": "https://s3.amazonaws.com/...",
  "generation_time": 15.0,
  "metadata": {
    "prompt": "...",
    "duration": 5.0,
    "gpu_used": true
  }
}
```

## Environment Variables

- `AWS_REGION` - AWS region (default: us-east-1)
- `S3_BUCKET` - S3 bucket for model artifacts (default: adgen-model-artifacts)
- `S3_MODEL_PREFIX` - S3 prefix for model files (default: models/wan25/)
- `CUDA_VISIBLE_DEVICES` - GPU device ID (default: 0)

## Container Startup Flow

1. Container starts
2. Downloads model from S3 to `/tmp/model/` (if not cached)
3. Loads model into GPU memory
4. Starts FastAPI server on port 8000
5. Ready to accept inference requests

**Startup Time:**
- Cold start (download + load): ~60-90 seconds
- Warm start (cached model): ~10-20 seconds

## GPU Requirements

- **Minimum:** NVIDIA GPU with 16GB VRAM (T4, A10G)
- **Recommended:** A10G (g5.xlarge instance)
- **CUDA:** 11.8 or higher
- **Driver:** 520.x or higher

## Testing

### Verify GPU Access
```bash
docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### Test Generate Endpoint
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test video","duration":5.0}'
```

## Deployment to ECS

This container is designed to run on ECS with:
- EC2 launch type on g5.xlarge instances
- Internal ALB for load balancing
- IAM role for S3 access
- Auto-scaling based on request load

See Story 2.5+ for ECS deployment configuration.

## Troubleshooting

### Model Download Fails
- Verify AWS credentials are set correctly
- Check S3 bucket exists: `aws s3 ls s3://adgen-model-artifacts/models/wan25/`
- Verify IAM permissions for S3 access

### GPU Not Detected
- Verify nvidia-docker is installed: `docker run --gpus all nvidia/cuda:11.8.0-base nvidia-smi`
- Check CUDA version: `nvidia-smi`
- Ensure `--gpus all` flag is used

### Out of Memory
- Model requires ~10GB GPU memory
- Use smaller batch size or reduce video duration
- Ensure no other processes are using GPU

## Architecture

```
Container Startup
    ↓
Check /tmp/model/
    ↓
[Not Cached] Download from S3 → Cache in /tmp/model/
    ↓
Load Model to GPU Memory
    ↓
Start FastAPI Server (port 8000)
    ↓
Ready for Requests (/health, /generate)
```

## Performance

- **Cold Start:** 60-90 seconds (download + load)
- **Warm Start:** 10-20 seconds (load only)
- **Generation Time:** 10-20 seconds per 5s video
- **Throughput:** ~3-6 videos/minute (depends on duration)

## References

- Story 2.1: S3 bucket for model artifacts
- Story 2.2: Model weights in S3
- Story 2.4: ECR repository for image
- Story 2.5: ECS task definition
