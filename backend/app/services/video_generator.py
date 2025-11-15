"""Video Generator Service - Scene background video generation.

This service uses ByteDance SeedAnce-1-lite model for cost-effective text-to-video
generation via HTTP API (no SDK dependency).

Uses HTTP API directly for:
- Better compatibility (works with all Python versions)
- No SDK version conflicts
- Simpler error handling
- Direct control over parameters

Model: bytedance/seedance-1-lite (lite/fast version, suitable for testing)
Production upgrade path: Full SeedAnce-1 or other text-to-video models
"""

import logging
import time
import os
import requests
import asyncio
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Replicate API configuration
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"


# ============================================================================
# Video Generator Service
# ============================================================================

class VideoGenerator:
    """Generates background videos using ByteDance SeedAnce-1-lite text-to-video model.
    
    Uses HTTP API directly (no SDK) for:
    - Better Python 3.14+ compatibility
    - No Pydantic v1 conflicts
    - Simpler, more direct control
    
    This is a cost-effective model perfect for MVP testing. For production, can upgrade
    to full SeedAnce-1 or other premium text-to-video models.
    """

    def __init__(self, api_token: Optional[str] = None):
        """Initialize with Replicate API token.
        
        Args:
            api_token: Replicate API token. If None, uses REPLICATE_API_TOKEN env var.
        """
        self.api_token = api_token or REPLICATE_API_TOKEN
        if not self.api_token:
            raise ValueError(
                "Replicate API token not provided. "
                "Set REPLICATE_API_TOKEN environment variable or pass api_token parameter."
            )

    async def generate_scene_background(
        self,
        prompt: str,
        style_spec_dict: dict,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
    ) -> str:
        """
        Generate background video for a scene via HTTP API.

        Args:
            prompt: Scene description prompt
            style_spec_dict: Style specification dict with visual guidelines
            duration: Video duration in seconds (typical: 2-5 seconds)
            aspect_ratio: Video aspect ratio (e.g., "16:9", "9:16", "1:1")
            seed: Random seed for reproducibility (optional, not used by SeedAnce)

        Returns:
            URL of generated video from Replicate
        """
        logger.info(f"Generating background video: {prompt[:60]}...")

        try:
            # Enhance prompt with style specification
            enhanced_prompt = self._enhance_prompt_with_style(prompt, style_spec_dict)

            # Create prediction via HTTP API
            prediction_data = await self._create_prediction(enhanced_prompt, int(duration))
            prediction_id = prediction_data.get("id")
            logger.debug(f"Created prediction: {prediction_id}")

            # Poll until complete
            result = await self._poll_prediction(prediction_id)
            
            if not result:
                raise RuntimeError("Prediction failed or timed out")
            
            # Extract video URL
            output = result.get("output")
            if isinstance(output, list) and len(output) > 0:
                video_url = output[0]
            else:
                video_url = str(output)

            logger.info(f"✅ Generated video: {video_url}")
            return video_url

        except Exception as e:
            logger.error(f"Error generating video: {e}")
            raise

    def _enhance_prompt_with_style(self, prompt: str, style_spec_dict: dict) -> str:
        """Enhance prompt with global style specifications."""
        style_parts = []

        if "lighting_direction" in style_spec_dict:
            style_parts.append(f"Lighting: {style_spec_dict['lighting_direction']}")

        if "camera_style" in style_spec_dict:
            style_parts.append(f"Camera: {style_spec_dict['camera_style']}")

        if "mood_atmosphere" in style_spec_dict:
            style_parts.append(f"Mood: {style_spec_dict['mood_atmosphere']}")

        if "grade_postprocessing" in style_spec_dict:
            style_parts.append(f"Grade: {style_spec_dict['grade_postprocessing']}")

        # Combine original prompt with style
        style_string = ". ".join(style_parts)
        enhanced = f"{prompt}. {style_string}. Professional product video."

        logger.debug(f"Enhanced prompt: {enhanced}")
        return enhanced


    async def _create_prediction(self, prompt: str, duration: int) -> dict:
        """Create a prediction via HTTP API."""
        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "version": "bytedance/seedance-1-lite",  # Model identifier
            "input": {
                "fps": 24,
                "prompt": prompt,
                "duration": min(duration, 10),  # Cap at 10s
                "resolution": "720p",
                "aspect_ratio": "16:9",
                "camera_fixed": False
            }
        }
        
        try:
            response = requests.post(
                REPLICATE_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create prediction: {e}")
            raise

    async def _poll_prediction(self, prediction_id: str, max_wait: int = 300) -> Optional[dict]:
        """Poll prediction until it completes."""
        headers = {"Authorization": f"Token {self.api_token}"}
        
        start_time = time.time()
        check_count = 0
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                logger.error(f"Prediction timeout after {max_wait}s")
                return None
            
            try:
                response = requests.get(
                    f"{REPLICATE_API_URL}/{prediction_id}",
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                prediction = response.json()
                
                status = prediction.get("status")
                check_count += 1
                
                if status == "processing":
                    logger.debug(f"  [{check_count}] Processing ({elapsed:.0f}s)")
                    await asyncio.sleep(5)  # Check every 5 seconds
                elif status == "succeeded":
                    logger.debug(f"  ✅ Succeeded ({elapsed:.0f}s)")
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
        duration: float = 5.0,
    ) -> list:
        """
        Generate multiple scene videos concurrently.

        Args:
            prompts: List of scene prompts
            style_spec_dict: Global style specification
            duration: Duration for each scene

        Returns:
            List of video URLs
        """
        logger.info(f"Generating {len(prompts)} scene videos in parallel...")

        try:
            # Generate all scenes concurrently
            tasks = [
                self.generate_scene_background(
                    prompt=prompt,
                    style_spec_dict=style_spec_dict,
                    duration=duration,
                )
                for prompt in prompts
            ]

            # Execute concurrently
            import asyncio

            videos = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            errors = [v for v in videos if isinstance(v, Exception)]
            if errors:
                logger.warning(f"⚠️  {len(errors)} generation(s) failed")

            successful = [v for v in videos if not isinstance(v, Exception)]
            logger.info(f"✅ Generated {len(successful)}/{len(prompts)} videos")

            return videos

        except Exception as e:
            logger.error(f"Error in batch generation: {e}")
            raise

