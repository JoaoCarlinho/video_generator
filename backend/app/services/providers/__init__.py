"""Video generation provider abstraction layer.

This package contains the base provider interface and concrete implementations
for video generation backends:
- ECSVideoProvider: VPC-hosted Wan2.5 inference
- ReplicateVideoProvider: Replicate API (SeedAnce model)
"""

from app.services.providers.base import BaseVideoProvider
from app.services.providers.ecs import ECSVideoProvider
from app.services.providers.replicate import ReplicateVideoProvider

__all__ = ["BaseVideoProvider", "ECSVideoProvider", "ReplicateVideoProvider"]
