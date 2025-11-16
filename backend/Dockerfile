# AWS Lambda Docker image for video generation worker
# Based on official AWS Lambda Python runtime
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
# FFmpeg is required for video processing
# wget, tar, xz for downloading FFmpeg static build
# gcc-c++, cmake for building Python packages with C++ extensions (like soxr)
# Development tools for building audio libraries
RUN yum update -y && \
    yum install -y wget tar xz gcc gcc-c++ cmake make && \
    yum clean all

# Install FFmpeg (static build - no dependencies)
# Using John Van Sickle's static FFmpeg builds (trusted source)
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ && \
    mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg-* && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

# Verify FFmpeg installation
RUN ffmpeg -version && ffprobe -version

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

# Copy Lambda handler
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set Lambda handler
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
