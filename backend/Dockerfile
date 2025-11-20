# AWS Lambda Docker image for video generation worker
# Based on official AWS Lambda Python runtime
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
# FFmpeg is required for video processing
# wget, tar, xz for downloading FFmpeg
# gcc-c++, cmake for building Python packages with C++ extensions (like soxr)
# Development tools for building audio libraries
# mesa-libGL, mesa-libGLU for OpenCV/video processing graphics libraries
# libXext, libXrender, libSM, libICE for X11 graphics support
# fontconfig, freetype, fribidi for text rendering support
RUN yum update -y && \
    yum install -y wget tar xz gcc gcc-c++ cmake make \
        mesa-libGL mesa-libGLU libXext libXrender libSM libICE \
        fontconfig freetype fribidi && \
    yum clean all

# Install FFmpeg using ffmpeg-static binaries (Lambda-compatible, includes all filters)
# These binaries are pre-built and tested to work across different Linux distributions
# Includes drawtext filter with libfreetype, libfribidi, and fontconfig support
RUN cd /tmp && \
    wget -O ffmpeg.gz https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffmpeg-linux-x64.gz && \
    wget -O ffprobe.gz https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffprobe-linux-x64.gz && \
    gunzip ffmpeg.gz && \
    gunzip ffprobe.gz && \
    chmod +x ffmpeg ffprobe && \
    mv ffmpeg /usr/local/bin/ffmpeg && \
    mv ffprobe /usr/local/bin/ffprobe && \
    rm -rf /tmp/*

# Note: This FFmpeg build from eugeneware/ffmpeg-static is known to work on Lambda
# Includes all filters including drawtext with proper GLIBC compatibility

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
# Use --no-cache-dir to reduce image size
# Upgrade pip first for better dependency resolution
# Set CXX environment variable for soxr compilation
# Note: soxr==0.3.7 is pinned in requirements.txt for nanobind compatibility
ENV CXX=g++
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Copy Lambda handlers
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY api_handler.py ${LAMBDA_TASK_ROOT}/

# Set Lambda handler for SQS events
# api_handler.handler = Mangum adapter for HTTP/API Gateway (not used here)
# lambda_handler.handler = SQS event processor for video generation
# Format: filename.function_name
CMD ["lambda_handler.handler"]

# Environment variables will be set in Lambda function configuration
# Required env vars:
# - DATABASE_URL
# - SUPABASE_URL
# - SUPABASE_SERVICE_ROLE_KEY
# - S3_BUCKET_NAME
# - AWS_REGION
# - REPLICATE_API_TOKEN
# - OPENAI_API_KEY

# Lambda runtime will provide:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_SESSION_TOKEN
# - AWS_REGION (also set by us for consistency)

# Health check (for local testing with Docker)
# Lambda doesn't use health checks, but useful for local dev
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Labels for documentation
LABEL maintainer="AI Ad Video Generator"
LABEL description="AWS Lambda worker for video generation via SQS"
LABEL version="1.0.0"
