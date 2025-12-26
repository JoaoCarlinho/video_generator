"""Video generation provider abstraction layer.

This package contains the base provider interface and concrete implementations
for video generation backends.

NOTE: Replicate provider is DISABLED. Only ECS provider is active.
"""

from app.services.providers.base import BaseVideoProvider
# REPLICATE DISABLED - Using ECS provider only
# from app.services.providers.replicate import ReplicateVideoProvider
from app.services.providers.ecs import ECSVideoProvider

__all__ = ["BaseVideoProvider", "ECSVideoProvider"]
# REPLICATE DISABLED: "ReplicateVideoProvider" removed from exports
