"""Video Generator Service - Scene background video generation.

This service orchestrates video generation through pluggable provider backends
(Replicate API, ECS-hosted Wan2.5, etc.) with automatic failover support.

Provider Architecture:
- BaseVideoProvider interface for consistent provider API
- ReplicateVideoProvider for Replicate's hosted inference
- ECSVideoProvider for VPC-hosted Wan2.5 (future - Epic 3)
- Automatic failover from primary to fallback provider

Model: bytedance/seedance-1-pro-fast (fast, high-quality production model)
Optimized for: Professional ad video generation with excellent quality/speed balance
"""

import logging
import os
from typing import Optional
from dotenv import load_dotenv

from backend.app.services.providers import ReplicateVideoProvider

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Provider configuration
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")


# ============================================================================
# Video Generator Service
# ============================================================================

class VideoGenerator:
    """Orchestrates video generation through pluggable provider backends.

    This service implements the provider abstraction pattern, enabling:
    - Multiple video generation backends (Replicate API, ECS, etc.)
    - Configuration-driven provider selection
    - Automatic failover between providers (Story 1.4)
    - Consistent interface regardless of backend

    The service delegates all video generation to provider instances,
    making it easy to swap backends without changing calling code.
    """

    def __init__(
        self,
        provider: str = "replicate",
        api_token: Optional[str] = None
    ):
        """Initialize VideoGenerator with selected provider.

        Args:
            provider: Provider identifier ("replicate" or "ecs").
                Defaults to "replicate" for backward compatibility.
            api_token: Replicate API token. If None, uses REPLICATE_API_TOKEN env var.
                Only used when provider="replicate".

        Raises:
            ValueError: If provider is invalid or required credentials missing.
        """
        self.provider_name = provider

        # Instantiate provider based on selection
        if provider == "replicate":
            token = api_token or REPLICATE_API_TOKEN
            if not token:
                raise ValueError(
                    "Replicate API token not provided. "
                    "Set REPLICATE_API_TOKEN environment variable or pass api_token parameter."
                )
            self.provider = ReplicateVideoProvider(replicate_api_token=token)
            logger.info("✅ VideoGenerator initialized with Replicate provider")

        elif provider == "ecs":
            # ECS provider will be implemented in Epic 3
            raise NotImplementedError(
                "ECS provider not yet implemented. "
                "Use provider='replicate' or wait for Epic 3 completion."
            )

        else:
            raise ValueError(
                f"Invalid provider: '{provider}'. "
                "Valid options: 'replicate', 'ecs'"
            )

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
        """Generate background video for a scene using selected provider.

        This method delegates to the configured provider instance, enabling
        transparent backend switching without changing calling code.

        Args:
            prompt: Scene description prompt
            style_spec_dict: Style specification dict with visual guidelines
            duration: Video duration in seconds (typical: 2-5 seconds)
            aspect_ratio: Video aspect ratio (e.g., "16:9", "9:16", "1:1")
            seed: Random seed for reproducibility (optional, may not be used by all providers)
            extracted_style: Optional extracted style from reference image
            style_override: (PHASE 7) Override style selection (one of the 5 predefined styles)

        Returns:
            URL of generated video from the selected provider

        Raises:
            Exception: Provider-specific exceptions for generation failures
        """
        logger.info(f"🎬 Generating video via {self.provider_name} provider: {prompt[:60]}...")

        # Delegate to provider
        video_url = await self.provider.generate_scene_background(
            prompt=prompt,
            style_spec_dict=style_spec_dict,
            duration=duration,
            aspect_ratio=aspect_ratio,
            seed=seed,
            extracted_style=extracted_style,
            style_override=style_override
        )

        logger.info(f"✅ Video generated successfully: {video_url}")
        return video_url

    async def generate_scene_batch(
        self,
        prompts: list,
        style_spec_dict: dict,
        duration: float = 5.0,
    ) -> list:
        """Generate multiple scene videos concurrently.

        Uses the configured provider for all generations, executing them
        in parallel for maximum throughput.

        Args:
            prompts: List of scene prompts
            style_spec_dict: Global style specification
            duration: Duration for each scene

        Returns:
            List of video URLs (or exceptions for failed generations)
        """
        logger.info(f"🎬 Batch generating {len(prompts)} videos via {self.provider_name}...")

        try:
            # Generate all scenes concurrently using the same provider
            import asyncio

            tasks = [
                self.generate_scene_background(
                    prompt=prompt,
                    style_spec_dict=style_spec_dict,
                    duration=duration,
                )
                for prompt in prompts
            ]

            # Execute concurrently
            videos = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            errors = [v for v in videos if isinstance(v, Exception)]
            if errors:
                logger.warning(f"⚠️  {len(errors)} generation(s) failed")

            successful = [v for v in videos if not isinstance(v, Exception)]
            logger.info(f"✅ Generated {len(successful)}/{len(prompts)} videos")

            return videos

        except Exception as e:
            logger.error(f"❌ Error in batch generation: {e}")
            raise
