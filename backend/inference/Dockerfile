# Story 2.3: Wan2.1 Inference Container Image
# GPU-accelerated video generation service using NVIDIA CUDA and PyTorch
# Optimized for g5.xlarge instances with NVIDIA A10G GPUs (24GB VRAM)

# Base image with CUDA 11.8 and cuDNN 8
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    CUDA_VISIBLE_DEVICES=0 \
    AWS_DEFAULT_REGION=us-east-1 \
    HF_HOME=/tmp/huggingface \
    TRANSFORMERS_CACHE=/tmp/huggingface

# Install system dependencies and Python 3.11
RUN apt-get update && apt-get install -y \
    software-properties-common \
    wget \
    curl \
    git \
    ffmpeg \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python3.11 get-pip.py \
    && rm get-pip.py \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Set working directory
WORKDIR /app

# Install PyTorch with CUDA support FIRST (large download, cache-friendly)
# Note: This is for CUDA 11.8 - adjust if using different CUDA version
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY serve.py .

# Create model cache directory
RUN mkdir -p /tmp/model /tmp/huggingface

# Expose FastAPI port
EXPOSE 8000

# Health check with extended start period for model download and loading
# Model download: ~2-3 min, Model loading: ~1-2 min
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI server with uvicorn
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
