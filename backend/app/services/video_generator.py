"""Video Generator Service - Scene background video generation.

This service uses ByteDance SeedAnce-1-Pro model for high-quality text-to-video
generation via HTTP API (no SDK dependency).

Uses HTTP API directly for:
- Better compatibility (works with all Python versions)
- No SDK version conflicts
- Simpler error handling
- Direct control over parameters

Model: bytedance/seedance-1-pro (high-quality production model)
Optimized for: Professional ad video generation
"""

import logging
import time
import os
import requests
import asyncio
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from app.services.style_manager import StyleManager

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Replicate API configuration
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
REPLICATE_API_URL = "https://api.replicate.com/v1/models/bytedance/seedance-1-pro/predictions"


class VideoGenerator:
    """Generates background videos using ByteDance SeedAnce-1-Pro text-to-video model.
    
    Uses HTTP API directly (no SDK) for:
    - Better Python 3.14+ compatibility
    - No Pydantic v1 conflicts
    - Simpler, more direct control
    
    This is a professional-grade model optimized for high-quality ad video generation.
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
        seed: Optional[int] = None,
        extracted_style: Optional[dict] = None,
        style_override: Optional[str] = None,
    ) -> str:
        """
        Generate background video for a scene via HTTP API (TikTok vertical 9:16).

        Args:
            prompt: Scene description prompt
            style_spec_dict: Style specification dict with visual guidelines
            duration: Video duration in seconds (typical: 2-5 seconds)
            seed: Random seed for reproducibility (optional, not used by SeedAnce)
            extracted_style: Optional extracted style from reference image
            style_override: Override style selection (one of the 3 perfume styles)

        Returns:
            URL of generated video from Replicate
        """
        logger.info(f"Generating TikTok vertical background video: {prompt[:60]}...")

        try:
            # Apply chosen style to prompt if style_override provided
            if style_override:
                logger.info(f"Applying style override: {style_override}")
                enhanced_prompt = self._enhance_prompt_with_style(prompt, style_spec_dict, extracted_style, style_override)
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
        """
        Generate multiple scene videos concurrently (TikTok vertical 9:16).

        Args:
            prompts: List of scene prompts
            style_spec_dict: Global style specification
            durations: Duration for each scene
            extracted_style: Optional extracted style from reference image
            style_override: Override style selection

        Returns:
            List of video URLs
        """
        logger.info(f"Generating {len(prompts)} TikTok vertical scene videos in parallel...")

        try:
            # Generate all scenes concurrently (all 9:16)

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

            videos = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            errors = [v for v in videos if isinstance(v, Exception)]
            if errors:
                logger.warning(f"{len(errors)} generation(s) failed")

            successful = [v for v in videos if not isinstance(v, Exception)]
            logger.info(f"Generated {len(successful)}/{len(prompts)} videos")

            return videos

        except Exception as e:
            logger.error(f"Error in batch generation: {e}")
            raise

