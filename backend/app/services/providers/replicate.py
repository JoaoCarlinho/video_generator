"""Replicate Video Provider - ByteDance SeedAnce-1-Pro-Fast integration.

This provider encapsulates all Replicate API-specific logic for video generation,
implementing the BaseVideoProvider interface for pluggable provider architecture.

Uses HTTP API directly for:
- Better Python 3.14+ compatibility
- No Pydantic v1 conflicts
- Simpler, more direct control
"""

import logging
import time
import requests
import asyncio
from typing import Optional, Dict, Any

from backend.app.services.providers.base import BaseVideoProvider
from backend.app.services.style_manager import StyleManager

logger = logging.getLogger(__name__)

# Replicate API configuration
REPLICATE_API_URL = "https://api.replicate.com/v1/models/bytedance/seedance-1-pro-fast/predictions"


class ReplicateVideoProvider(BaseVideoProvider):
    """Replicate API provider for ByteDance SeedAnce-1-Pro-Fast video generation.

    This provider implements the BaseVideoProvider interface for Replicate's
    hosted inference platform, handling:
    - HTTP API communication with proper headers and polling
    - Prompt enhancement with style specifications
    - Error handling and logging
    - Fallback polling for async predictions

    The provider always returns True for health checks since Replicate is
    a managed external service with high availability SLAs.
    """

    def __init__(self, replicate_api_token: str):
        """Initialize Replicate provider with API credentials.

        Args:
            replicate_api_token: Replicate API authentication token.
                Get your token from https://replicate.com/account/api-tokens

        Raises:
            ValueError: If replicate_api_token is None or empty string
        """
        if not replicate_api_token:
            raise ValueError(
                "Replicate API token is required. "
                "Provide a valid token from https://replicate.com/account/api-tokens"
            )

        self.api_token = replicate_api_token

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
        """Generate background video using Replicate's SeedAnce model.

        This method handles the complete generation lifecycle:
        1. Enhance prompt with style specifications
        2. Create prediction via HTTP API with "Prefer: wait" header
        3. Handle synchronous or async responses
        4. Poll for completion if needed
        5. Extract and return video URL

        Args:
            prompt: Scene description prompt for video generation
            style_spec_dict: Style specification dictionary with visual guidelines
                (lighting_direction, camera_style, mood_atmosphere, grade_postprocessing)
            duration: Video duration in seconds (capped at 10s by API)
            aspect_ratio: Video aspect ratio (e.g., "16:9", "9:16", "1:1")
                Note: Currently hardcoded to "16:9" in API payload
            seed: Random seed for reproducibility (not used by SeedAnce model)
            extracted_style: Optional extracted style from reference image
                (colors, lighting, camera, mood, atmosphere, texture)
            style_override: Optional style preset override (cinematic, dark_premium, etc.)
                Applies predefined style keywords from StyleManager

        Returns:
            str: Publicly accessible URL to the generated video (valid for 24-48 hours)

        Raises:
            RuntimeError: If prediction fails or times out
            requests.exceptions.RequestException: If HTTP requests fail
        """
        logger.info(f"🎬 Generating video via Replicate: {prompt[:60]}...")

        try:
            # Apply style override or standard enhancement
            if style_override:
                logger.info(f"✅ Applying style override: {style_override}")
                enhanced_prompt = self._enhance_prompt_with_style(
                    prompt, style_spec_dict, extracted_style, style_override
                )
            else:
                enhanced_prompt = self._enhance_prompt_with_style(
                    prompt, style_spec_dict, extracted_style
                )

            # Create prediction via HTTP API (with "Prefer: wait" for sync response)
            prediction_data = await self._create_prediction(enhanced_prompt, int(duration))

            # Check if prediction is already complete (from "Prefer: wait" header)
            status = prediction_data.get("status")
            logger.debug(f"Prediction status: {status}")

            if status in ["succeeded", "completed"]:
                result = prediction_data
            else:
                # Fallback: poll if not complete (shouldn't happen with "Prefer: wait")
                prediction_id = prediction_data.get("id")
                logger.warning(f"⚠️ Prediction not complete, polling: {prediction_id}")
                result = await self._poll_prediction(prediction_id)

                if not result:
                    raise RuntimeError("Prediction failed or timed out")

            # Extract video URL from output
            output = result.get("output")
            if isinstance(output, list) and len(output) > 0:
                video_url = output[0]
            else:
                video_url = str(output)

            logger.info(f"✅ Generated video: {video_url}")
            return video_url

        except Exception as e:
            logger.error(f"❌ Error generating video via Replicate: {e}")
            raise

    def get_provider_name(self) -> str:
        """Return the provider identifier for logging and tracking.

        Returns:
            str: "replicate" - identifies this as the Replicate API provider
        """
        return "replicate"

    async def health_check(self) -> bool:
        """Check Replicate API availability.

        For Replicate (external managed service), we always return True since:
        - Replicate has 99.9%+ SLA as a hosted platform
        - Health check would consume API quota unnecessarily
        - Failures are better handled per-request with automatic failover

        Future enhancement: Could implement actual API ping if needed

        Returns:
            bool: Always True (Replicate is a managed service with high availability)
        """
        return True

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _enhance_prompt_with_style(
        self,
        prompt: str,
        style_spec_dict: dict,
        extracted_style: Optional[dict] = None,
        style_override: Optional[str] = None
    ) -> str:
        """Enhance prompt with style specifications and optional overrides.

        Combines multiple style sources in priority order:
        1. PHASE 7 style override (if provided)
        2. Extracted style from reference image (if provided)
        3. Base style specifications from style_spec_dict

        Args:
            prompt: Original scene description
            style_spec_dict: Base style specs (lighting, camera, mood, grade)
            extracted_style: Optional reference image style
            style_override: Optional predefined style preset

        Returns:
            str: Enhanced prompt with style keywords appended
        """
        style_parts = []

        # PHASE 7: Apply style override keywords if provided
        if style_override:
            logger.info(f"PHASE 7: Adding style override '{style_override}'")
            try:
                style_config = StyleManager.get_style_config(style_override)
                if style_config and "keywords" in style_config:
                    keywords = style_config["keywords"]
                    style_parts.append(f"Visual Style: {', '.join(keywords)}")
                    logger.debug(f"Added style keywords: {keywords}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to apply style override: {e}")

        # Add base style specifications
        if "lighting_direction" in style_spec_dict:
            style_parts.append(f"Lighting: {style_spec_dict['lighting_direction']}")

        if "camera_style" in style_spec_dict:
            style_parts.append(f"Camera: {style_spec_dict['camera_style']}")

        if "mood_atmosphere" in style_spec_dict:
            style_parts.append(f"Mood: {style_spec_dict['mood_atmosphere']}")

        if "grade_postprocessing" in style_spec_dict:
            style_parts.append(f"Grade: {style_spec_dict['grade_postprocessing']}")

        # Add extracted reference style (overrides/enhances base style)
        if extracted_style:
            logger.debug("🎨 Applying extracted reference style")

            colors = extracted_style.get("colors", [])
            if colors:
                style_parts.append(f"Colors: {', '.join(colors)}")

            for attr in ["lighting", "camera", "mood", "atmosphere", "texture"]:
                if extracted_style.get(attr):
                    style_parts.append(f"Reference {attr.title()}: {extracted_style[attr]}")

        # Combine prompt with style specifications
        style_string = ". ".join(style_parts)
        enhanced = f"{prompt}. {style_string}. Professional product video."

        logger.debug(f"Enhanced prompt: {enhanced}")
        return enhanced

    async def _create_prediction(self, prompt: str, duration: int) -> dict:
        """Create prediction via Replicate HTTP API.

        Uses "Prefer: wait" header to get synchronous responses when possible,
        avoiding polling overhead for fast predictions.

        Args:
            prompt: Enhanced prompt with style specifications
            duration: Video duration in seconds (will be capped at 10s)

        Returns:
            dict: Prediction response JSON with status and output

        Raises:
            requests.exceptions.RequestException: If HTTP request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait"  # Request synchronous response instead of polling
        }

        payload = {
            "input": {
                "fps": 24,
                "prompt": prompt,
                "duration": min(duration, 10),  # Cap at 10s (API limit)
                "resolution": "480p",  # 480p for good quality + faster generation
                "aspect_ratio": "16:9",
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
            logger.error(f"❌ Failed to create prediction: {e}")
            raise

    async def _poll_prediction(
        self,
        prediction_id: str,
        max_wait: int = 300
    ) -> Optional[dict]:
        """Poll prediction status until completion.

        Fallback method used when "Prefer: wait" doesn't return complete result.
        Polls every 5 seconds with a 300-second total timeout.

        Args:
            prediction_id: Replicate prediction ID to poll
            max_wait: Maximum time to poll in seconds (default: 300s = 5 minutes)

        Returns:
            dict: Completed prediction data, or None if failed/timed out

        Raises:
            requests.exceptions.RequestException: If HTTP polling request fails
        """
        headers = {"Authorization": f"Bearer {self.api_token}"}

        start_time = time.time()
        check_count = 0

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Prediction timeout after {max_wait}s")
                return None

            try:
                # Poll prediction status (use base predictions URL, not model-specific)
                poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
                response = requests.get(poll_url, headers=headers, timeout=10)
                response.raise_for_status()
                prediction = response.json()

                status = prediction.get("status")
                check_count += 1

                if status == "processing":
                    logger.debug(f"  [{check_count}] Processing ({elapsed:.0f}s)")
                    await asyncio.sleep(5)  # Poll every 5 seconds
                elif status == "succeeded":
                    logger.debug(f"  ✅ Succeeded ({elapsed:.0f}s)")
                    return prediction
                elif status == "failed":
                    logger.error(f"❌ Prediction failed: {prediction.get('error')}")
                    return None
                else:
                    logger.debug(f"  Status: {status}")
                    await asyncio.sleep(5)

            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Error polling prediction: {e}")
                raise
