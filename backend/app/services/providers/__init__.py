"""Video generation provider abstraction layer.

This package contains the base provider interface and concrete implementations
for different video generation backends (Replicate API, ECS-hosted Wan2.5, etc.).
"""

from app.services.providers.base import BaseVideoProvider
from app.services.providers.replicate import ReplicateVideoProvider
from app.services.providers.ecs import ECSVideoProvider

__all__ = ["BaseVideoProvider", "ReplicateVideoProvider", "ECSVideoProvider"]
