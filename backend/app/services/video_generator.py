"""Video Generator Service - Scene background video generation.

This service orchestrates video generation through pluggable provider backends
(Replicate API, ECS-hosted Wan2.5, etc.) with automatic failover support.

CURRENT: ByteDance SeedAnce-1-Pro (text-to-video)
FUTURE: Google Veo S3 (image-to-video with product/text integration)

Provider Architecture:
- BaseVideoProvider interface for consistent provider API
- ReplicateVideoProvider for Replicate's hosted inference
- ECSVideoProvider for VPC-hosted Wan2.5 (future - Epic 3)
- Automatic failover from primary to fallback provider

Model: bytedance/seedance-1-pro-fast (fast, high-quality production model)
Optimized for: Professional ad video generation with excellent quality/speed balance

VEO S3 READINESS:
- Enhanced prompts from ScenePlanner (user-first + cinematography)
- Support for style overrides
- Prepared for image reference inputs (product/logo)
- Text integration instructions ready
"""

import logging
import os
import requests
import asyncio
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from app.services.style_manager import StyleManager

from app.services.providers import ReplicateVideoProvider

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Provider configuration
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
REPLICATE_API_URL = "https://api.replicate.com/v1/models/bytedance/seedance-1-pro/predictions"


class VideoGenerator:
    """Orchestrates video generation through pluggable provider backends.

    This service implements the provider abstraction pattern, enabling:
    - Multiple video generation backends (Replicate API, ECS, etc.)
    - Configuration-driven provider selection
    - Automatic failover between providers (Story 1.4)
    - Consistent interface regardless of backend

    The service delegates all video generation to provider instances,
    making it easy to swap backends without changing calling code.
    Generates background videos using ByteDance SeedAnce-1-Pro text-to-video model.
    
    Uses HTTP API directly (no SDK) for:
    - Better Python 3.14+ compatibility
    - No Pydantic v1 conflicts
    - Simpler, more direct control
    
    This is a professional-grade model optimized for high-quality ad video generation.
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
        # seed: Optional[int] = None,
        extracted_style: Optional[dict] = None,
        style_override: Optional[str] = None,
    ) -> str:
        """Generate background video for a scene using selected provider.

        This method delegates to the configured provider instance, enabling
        transparent backend switching without changing calling code.
        
        This method receives enhanced prompts from ScenePlanner with:
        - User-first creative concepts
        - Advanced cinematography vocabulary
        - Product visual language applied to user's vision

        Args:
            prompt: Enhanced scene description prompt (from ScenePlanner with Veo S3 optimizations)
            style_spec_dict: Style specification dict with visual guidelines
            duration: Video duration in seconds (typical: 2-5 seconds)
            aspect_ratio: Video aspect ratio (e.g., "16:9", "9:16", "1:1")
            seed: Random seed for reproducibility (optional, may not be used by all providers)
            extracted_style: Optional extracted style from reference image
            style_override: (PHASE 7) Override style selection (one of the 5 predefined styles)

        Returns:
            URL of generated video from the selected provider
        logger.info(f"Generating TikTok vertical background video: {prompt[:60]}...")
s
        Raises:
            Exception: Provider-specific exceptions for generation failures
        """
        try:
            logger.info(f"🎬 Generating video via {self.provider_name} provider: {prompt[:60]}...")

            # Apply chosen style to prompt if style_override provided
            # Delegate to provider

            if style_override:
                logger.info(f"Applying style override: {style_override}")
                enhanced_prompt = self._enhance_prompt_with_style(
                    # aspect_ratio=aspect_ratio,
                    prompt,
                    style_spec_dict,
                    extracted_style,
                    style_override
                    )
            else:
                enhanced_prompt = self._enhance_prompt_with_style(prompt, style_spec_dict, extracted_style)

            # Create prediction via HTTP API (hardcoded 9:16 for TikTok vertical)
            prediction_data = await self._create_prediction(enhanced_prompt, int(duration), "9:16")
            
            # With "Prefer: wait", the prediction should already be complete
            status = prediction_data.get("status")
            logger.debug(f"Prediction status: {status}")
            
            # Check if prediction is already complete (from "Prefer: wait")
            if status in ["succeeded", "completed"]:
                result = prediction_data
            else:
                # Fallback: poll if not complete yet (shouldn't happen with "Prefer: wait")
                prediction_id = prediction_data.get("id")
                logger.warning(f"Prediction not complete, polling: {prediction_id}")
                result = await self._poll_prediction(prediction_id)
                
                if not result:
                    raise RuntimeError("Prediction failed or timed out")
            
            # Extract video URL
            output = result.get("output")
            if isinstance(output, list) and len(output) > 0:
                video_url = output[0]
            else:
                video_url = str(output)


            logger.info(f"Generated video: {video_url}")
            return video_url

        except Exception as e:
            logger.error(f"Error generating video: {e}")
            raise

    def _enhance_prompt_with_style(self, prompt: str, style_spec_dict: dict, extracted_style: Optional[dict] = None, style_override: Optional[str] = None) -> str:
        """Enhance prompt with global style specifications, optional reference style, and style override."""
        style_parts = []

        # If style_override provided, use style keywords
        if style_override:
            logger.info(f"Adding style override '{style_override}' to prompt")
            try:
                style_config = StyleManager.get_style_config(style_override)
                if style_config and "keywords" in style_config:
                    keywords = style_config["keywords"]
                    style_parts.append(f"Visual Style Keywords: {', '.join(keywords)}")
                    logger.debug(f"Added style keywords: {keywords}")
            except Exception as e:
                logger.warning(f"Failed to apply style override: {e}")

        # Add base style specifications
        if "lighting_direction" in style_spec_dict:
            style_parts.append(f"Lighting: {style_spec_dict['lighting_direction']}")

        if "camera_style" in style_spec_dict:
            style_parts.append(f"Camera: {style_spec_dict['camera_style']}")

        if "mood_atmosphere" in style_spec_dict:
            style_parts.append(f"Mood: {style_spec_dict['mood_atmosphere']}")

        if "grade_postprocessing" in style_spec_dict:
            style_parts.append(f"Grade: {style_spec_dict['grade_postprocessing']}")

        # Add reference style if available (overrides/enhances base style)
        if extracted_style:
            logger.debug("Applying extracted reference style to video prompt")
            
            colors = extracted_style.get("colors", [])
            if colors:
                colors_str = ", ".join(colors)
                style_parts.append(f"Colors: {colors_str}")
            
            if extracted_style.get("lighting"):
                style_parts.append(f"Reference Lighting: {extracted_style['lighting']}")
            
            if extracted_style.get("camera"):
                style_parts.append(f"Reference Camera: {extracted_style['camera']}")
            
            if extracted_style.get("mood"):
                style_parts.append(f"Reference Mood: {extracted_style['mood']}")
            
            if extracted_style.get("atmosphere"):
                style_parts.append(f"Reference Atmosphere: {extracted_style['atmosphere']}")
            
            if extracted_style.get("texture"):
                style_parts.append(f"Reference Texture: {extracted_style['texture']}")

        # Combine original prompt with style
        style_string = ". ".join(style_parts)
        enhanced = f"{prompt}. {style_string}. Modern cinematic product commercial."

        logger.info(f"📝 Enhanced script sent to video generator: {enhanced}")
        return enhanced


    async def _create_prediction(self, prompt: str, duration: int, aspect_ratio: str = "9:16") -> dict:
        """Create a prediction via HTTP API using seedance-1-pro model (TikTok vertical)."""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait"  # Wait for the result instead of polling
        }
        
        payload = {
            "input": {
                "fps": 24,
                "prompt": prompt,
                "duration": min(duration, 10),  # Cap at 10s
                "resolution": "480p",  # 480p for faster generation, good quality
                "aspect_ratio": "9:16",  # Hardcoded TikTok vertical
                "camera_fixed": False
            }
        }
        
        try:
            response = requests.post(
                REPLICATE_API_URL,
                headers=headers,
                json=payload,
                timeout=120  # Increased timeout for "Prefer: wait"
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create prediction: {e}")
            raise

    async def _poll_prediction(self, prediction_id: str, max_wait: int = 300) -> Optional[dict]:
        """Poll prediction until it completes."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        start_time = time.time()
        check_count = 0
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                logger.error(f"Prediction timeout after {max_wait}s")
                return None
            
            try:
                # Polling uses base predictions URL, not model-specific URL
                poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
                response = requests.get(
                    poll_url,
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                prediction = response.json()
                
                status = prediction.get("status")
                check_count += 1
                
                if status == "processing":
                    logger.debug(f"  [{check_count}] Processing ({elapsed:.0f}s)")
                    await asyncio.sleep(5)
                elif status == "succeeded":
                    logger.debug(f"  Succeeded ({elapsed:.0f}s)")
                    return prediction
                elif status == "failed":
                    logger.error(f"Prediction failed: {prediction.get('error')}")
                    return None
                else:
                    logger.debug(f"  Status: {status}")
                    await asyncio.sleep(5)
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Error polling prediction: {e}")
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
            import asyncio

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

