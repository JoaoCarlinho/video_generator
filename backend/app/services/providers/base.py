"""Base abstract class for video generation providers.

This module defines the contract that all video generation providers must implement,
enabling swappable backends (Replicate API, ECS-hosted inference, etc.) with
automatic failover capabilities.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseVideoProvider(ABC):
    """Abstract base class defining the video provider interface.

    All video generation providers must inherit from this class and implement
    all abstract methods. This enables the VideoGenerator service to work with
    multiple backends through a consistent interface.

    The provider abstraction supports:
    - Multiple video generation backends (Replicate API, VPC-hosted Wan2.5, etc.)
    - Automatic failover when primary provider is unavailable
    - Health monitoring for proactive failover decisions
    - Provider identification for logging and cost tracking
    """

    @abstractmethod
    async def generate_scene_background(
        self,
        prompt: str,
        style_spec_dict: dict,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
        extracted_style: Optional[dict] = None,
        style_override: Optional[str] = None,
    ) -> str:
        """Generate a video background scene based on the provided parameters.

        This method is the core video generation interface. Implementations must
        handle the full generation lifecycle: request submission, polling for
        completion, and returning the final video URL.

        Args:
            prompt: Text description of the scene to generate.
                Example: "A serene beach sunset with palm trees"
            style_spec_dict: Dictionary containing style specifications including
                camera_movement, shot_type, lighting, color_palette, etc.
                These specs guide the visual aesthetic of the generated video.
            duration: Video duration in seconds. Default: 5.0
                Supported values depend on provider capabilities.
            aspect_ratio: Video aspect ratio as "width:height" string.
                Common values: "16:9" (landscape), "9:16" (portrait), "1:1" (square)
                Default: "16:9"
            seed: Optional random seed for reproducible generation.
                Use the same seed with identical parameters to get consistent results.
                Default: None (random seed)
            extracted_style: Optional dictionary of extracted style attributes
                from reference images or previous generations.
            style_override: Optional string to override style_spec_dict with
                a different style preset or custom style string.

        Returns:
            str: Publicly accessible URL to the generated video file.
                The URL should be valid for at least the duration needed for
                downstream processing (typically 24-48 hours).

        Raises:
            Exception: Provider-specific exceptions for generation failures.
                Implementations should raise descriptive exceptions that can
                be caught by failover logic.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider identifier string.

        This identifier is used for:
        - Logging and debugging (tracking which provider handled each request)
        - Cost tracking and analytics (comparing provider costs/performance)
        - Provider selection configuration

        Returns:
            str: Provider name identifier.
                Examples: "replicate", "ecs", "local"
                Should be lowercase, alphanumeric with hyphens.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available and healthy.

        This method enables proactive health monitoring and automatic failover.
        Implementations should perform a lightweight check of provider availability
        without consuming significant resources or credits.

        Health check guidelines:
        - Should complete within 5 seconds maximum
        - Should not count against usage quotas if possible
        - Can check connectivity, authentication, or service status
        - Should return False rather than raising exceptions when unhealthy

        Returns:
            bool: True if provider is available and healthy, False otherwise.
                True: Provider can accept generation requests
                False: Provider is unavailable (triggers failover if configured)

        Examples:
            - Replicate: Always returns True (cloud API with 99.9% SLA)
            - ECS: Checks ALB health endpoint and container availability
            - Local: Checks if GPU is available and model is loaded
        """
        pass
