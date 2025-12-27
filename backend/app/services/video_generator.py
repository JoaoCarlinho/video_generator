"""Video Generator Service - Scene background video generation.

This service orchestrates video generation through pluggable provider backends.

Provider Architecture:
- BaseVideoProvider interface for consistent provider API
- ECSVideoProvider for VPC-hosted Wan2.5 inference
- ReplicateVideoProvider for Replicate API (SeedAnce model)

VEO S3 READINESS:
- Enhanced prompts from ScenePlanner (user-first + cinematography)
- Support for style overrides
- Prepared for image reference inputs (product/logo)
- Text integration instructions ready
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

from app.services.providers import ECSVideoProvider, ReplicateVideoProvider

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ECS Provider configuration
ECS_ENDPOINT_URL = os.environ.get("ECS_ENDPOINT_URL", "http://internal-adgen-ecs-alb-1719239824.us-east-1.elb.amazonaws.com")


class VideoGenerator:
    """Orchestrates video generation through pluggable provider backends.

    This service implements the provider abstraction pattern supporting:
    - ECS: VPC-hosted Wan2.5 model for GPU-accelerated video generation
    - Replicate: Cloud-hosted SeedAnce model via Replicate API
    """

    def __init__(
        self,
        provider: str = "ecs",
        api_token: Optional[str] = None
    ):
        """Initialize VideoGenerator with selected provider.

        Args:
            provider: Provider identifier - "ecs" or "replicate"
            api_token: API token for Replicate provider (ignored for ECS)

        Raises:
            ValueError: If provider is invalid or required config is missing
        """
        self.provider_name = provider

        if provider == "ecs":
            endpoint_url = ECS_ENDPOINT_URL
            if not endpoint_url:
                raise ValueError(
                    "ECS_ENDPOINT_URL not configured. "
                    "Set ECS_ENDPOINT_URL environment variable."
                )
            self.provider = ECSVideoProvider(endpoint_url=endpoint_url)
            logger.info(f"✅ VideoGenerator initialized with ECS provider: {endpoint_url}")

        elif provider == "replicate":
            if not api_token:
                raise ValueError(
                    "Replicate API token is required. "
                    "Provide api_token parameter or set REPLICATE_API_TOKEN."
                )
            self.provider = ReplicateVideoProvider(replicate_api_token=api_token)
            logger.info("✅ VideoGenerator initialized with Replicate provider")

        else:
            raise ValueError(
                f"Invalid provider: '{provider}'. "
                "Supported providers: 'ecs', 'replicate'"
            )

    async def generate_scene_background(
        self,
        prompt: str,
        style_spec_dict: dict,
        duration: float = 5.0,
        extracted_style: Optional[dict] = None,
        style_override: Optional[str] = None,
    ) -> str:
        """Generate background video for a scene using selected provider.

        This method delegates to the configured provider instance, enabling
        transparent backend switching without changing calling code.

        Args:
            prompt: Enhanced scene description prompt (from ScenePlanner)
            style_spec_dict: Style specification dict with visual guidelines
            duration: Video duration in seconds (typical: 2-5 seconds)
            extracted_style: Optional extracted style from reference image
            style_override: Override style selection (one of the 5 predefined styles)

        Returns:
            URL of generated video from the selected provider

        Raises:
            Exception: Provider-specific exceptions for generation failures
        """
        try:
            logger.info(f"🎬 Generating video via {self.provider_name} provider: {prompt[:60]}...")

            # Delegate to the configured provider
            video_url = await self.provider.generate_scene_background(
                prompt=prompt,
                style_spec_dict=style_spec_dict,
                duration=duration,
                extracted_style=extracted_style,
                style_override=style_override,
            )

            logger.info(f"✅ Generated video: {video_url}")
            return video_url

        except Exception as e:
            logger.error(f"Error generating video: {e}")
            raise

    async def generate_scene_batch(
        self,
        prompts: list,
        style_spec_dict: dict,
        durations: list,
        extracted_style: Optional[dict] = None,
        style_override: Optional[str] = None,
    ) -> list:
        """Generate multiple scene videos concurrently.

        Uses the configured provider for all generations, executing them
        in parallel for maximum throughput.

        Args:
            prompts: List of scene prompts
            style_spec_dict: Global style specification
            durations: Duration for each scene
            extracted_style: Optional extracted style from reference image
            style_override: Override style selection

        Returns:
            List of video URLs (or exceptions for failed generations)
        """
        logger.info(f"🎬 Batch generating {len(prompts)} videos via {self.provider_name}...")

        try:
            # Generate all scenes concurrently using the same provider
            tasks = [
                self.generate_scene_background(
                    prompt=prompts[i],
                    style_spec_dict=style_spec_dict,
                    duration=durations[i],
                    extracted_style=extracted_style,
                    style_override=style_override,
                )
                for i in range(len(prompts))
            ]

            # Execute concurrently
            videos = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            errors = [v for v in videos if isinstance(v, Exception)]
            if errors:
                logger.warning(f"{len(errors)} generation(s) failed")

            successful = [v for v in videos if not isinstance(v, Exception)]
            logger.info(f"Generated {len(successful)}/{len(prompts)} videos")

            return videos

        except Exception as e:
            logger.error(f"❌ Error in batch generation: {e}")
            raise

    async def generate_scene_videos_batch(
        self,
        scenes: List[Dict[str, Any]],
        num_variations: int,
        style_spec_dict: dict,
        extracted_style: Optional[dict] = None,
        style_override: Optional[str] = None,
    ) -> List[List[str]]:
        """
        Generate N variations of videos for scenes.
        
        For each variation:
        - Uses different seed for Replicate model (1000 + variation_index)
        - Applies variation-specific prompt suffix
        - Maintains style consistency
        
        Args:
            scenes: List of scene dictionaries with prompts and durations
            num_variations: Number of variations to generate (1-3)
            style_spec_dict: Global style specification
            extracted_style: Optional extracted style from reference image
            style_override: Override style selection
            
        Returns:
            List of video URL lists: [[urls_v1], [urls_v2], [urls_v3]]
        """
        logger.info(f"Generating {num_variations} video variations for {len(scenes)} scenes...")
        
        variation_videos = []
        
        for var_idx in range(num_variations):
            logger.info(f"Generating variation {var_idx + 1}/{num_variations}...")
            
            # Extract prompts and durations from scenes
            prompts = [scene.get("background_prompt", "") for scene in scenes]
            durations = [float(scene.get("duration", 5.0)) for scene in scenes]
            
            # Apply variation-specific style suffix
            variation_style_override = self._add_variation_suffix(style_override, var_idx)
            
            # Generate videos for this variation
            videos = await self.generate_scene_batch(
                prompts=prompts,
                style_spec_dict=style_spec_dict,
                durations=durations,
                extracted_style=extracted_style,
                style_override=variation_style_override,
            )
            
            variation_videos.append(videos)
            logger.info(f"Variation {var_idx + 1} complete: {len(videos)} videos")
        
        logger.info(f"Generated {len(variation_videos)} video variations")
        return variation_videos

    def _add_variation_suffix(self, style_override: Optional[str], var_idx: int) -> Optional[str]:
        """
        Add variation-specific modifiers to style override.
        
        Args:
            style_override: Original style override (e.g., "cinematic")
            var_idx: Variation index (0-based)
            
        Returns:
            Enhanced style override with variation suffix
        """
        # Define variation suffixes
        suffixes = [
            ", dramatic cinematic lighting, high contrast",
            ", minimal clean aesthetic, soft diffused lighting",
            ", warm atmospheric lighting, lifestyle narrative",
        ]
        
        suffix = suffixes[var_idx % len(suffixes)]
        
        if style_override:
            return f"{style_override}{suffix}"
        else:
            # If no style override, just return the suffix (will be applied to prompt)
            return None

