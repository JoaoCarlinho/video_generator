"""Reference Image Style Extractor Service.

Analyzes uploaded reference images using vision LLM to extract visual style elements.
Extracts: colors, mood, lighting, camera style, atmosphere, texture.
"""

import logging
import json
from typing import Optional, Dict, Any
from pathlib import Path
import aiohttp
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ExtractedStyle:
    """Structured style extracted from reference image."""

    def __init__(
        self,
        colors: list[str],
        mood: str,
        lighting: str,
        camera: str,
        atmosphere: str,
        texture: str,
    ):
        self.colors = colors
        self.mood = mood
        self.lighting = lighting
        self.camera = camera
        self.atmosphere = atmosphere
        self.texture = texture

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "colors": self.colors,
            "mood": self.mood,
            "lighting": self.lighting,
            "camera": self.camera,
            "atmosphere": self.atmosphere,
            "texture": self.texture,
        }


class ReferenceImageStyleExtractor:
    """Extract visual style from reference images using OpenAI Vision."""

    def __init__(self, openai_client):
        """Initialize with OpenAI client.

        Args:
            openai_client: Initialized OpenAI client with vision capabilities
        """
        self.openai_client = openai_client

    async def extract_style(
        self,
        image_path: str,
        brand_name: str,
    ) -> ExtractedStyle:
        """Extract visual style from reference image using OpenAI Vision.

        Args:
            image_path: Local file path or HTTP(S) URL of image
            brand_name: Brand name for context

        Returns:
            ExtractedStyle object with colors, mood, lighting, etc.
        """
        logger.info(f"🎨 Extracting style from reference image: {image_path}")

        try:
            # 1. Get image data (from file or URL)
            image_data = await self._get_image_data(image_path)
            if not image_data:
                raise ValueError(f"Could not read image from {image_path}")

            logger.info(f"✅ Read {len(image_data)} bytes from image")

            # 2. Extract style using OpenAI Vision
            style = await self._extract_with_openai(image_data, brand_name)

            logger.info(f"✅ Extracted style: {json.dumps(style.to_dict(), indent=2)}")
            return style

        except Exception as e:
            logger.error(f"❌ Error extracting style: {e}")
            raise

    async def _get_image_data(self, image_path: str) -> Optional[bytes]:
        """Get image data from file path or URL."""
        try:
            # Check if local file
            if image_path.startswith("/") or image_path.startswith("."):
                logger.info(f"📂 Reading local file: {image_path}")
                file_path = Path(image_path)

                if not file_path.exists():
                    logger.error(f"❌ File not found: {image_path}")
                    return None

                with open(file_path, "rb") as f:
                    return f.read()

            # Otherwise treat as HTTP URL
            logger.info(f"🌐 Downloading image from URL: {image_path}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    image_path, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        logger.error(f"❌ HTTP error {resp.status}")
                        return None

        except Exception as e:
            logger.error(f"❌ Error reading image: {e}")
            return None

    async def _extract_with_openai(
        self, image_data: bytes, brand_name: str
    ) -> ExtractedStyle:
        """Extract style using OpenAI GPT-4 Vision API."""
        import base64

        # Encode image to base64
        image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

        prompt = f"""Analyze this reference image and extract visual style elements suitable for a {brand_name} promotional video.

Extract the following in JSON format:
{{
  "colors": ["#HEX1", "#HEX2", "#HEX3"],
  "mood": "descriptive mood (2-3 words)",
  "lighting": "lighting description",
  "camera": "camera style description",
  "atmosphere": "atmosphere description",
  "texture": "texture/material description"
}}

Only return the JSON, no additional text."""

        try:
            # Call OpenAI GPT-4 Vision API (gpt-4o for vision capability)
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            # Extract response
            response_text = response.choices[0].message.content
            logger.info(f"📝 OpenAI response: {response_text}")

            # Parse JSON (handle markdown code blocks)
            json_text = response_text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]  # Remove ```json
            if json_text.startswith("```"):
                json_text = json_text[3:]  # Remove ```
            if json_text.endswith("```"):
                json_text = json_text[:-3]  # Remove trailing ```
            json_text = json_text.strip()
            
            style_data = json.loads(json_text)

            return ExtractedStyle(
                colors=style_data.get("colors", ["#999999"]),
                mood=style_data.get("mood", "professional"),
                lighting=style_data.get("lighting", "studio lighting"),
                camera=style_data.get("camera", "professional"),
                atmosphere=style_data.get("atmosphere", "sophisticated"),
                texture=style_data.get("texture", "smooth"),
            )

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse OpenAI response as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ OpenAI API error: {e}")
            raise

