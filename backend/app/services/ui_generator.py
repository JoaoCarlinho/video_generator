"""UI Generator Service - Generates mobile app UI mockups from descriptions.

This service creates realistic UI mockup images for mobile app products when
screenshots are not provided. Uses OpenAI's DALL-E 3 for image generation
and uploads results to S3.

Key Features:
- 5 visual styles (modern_minimal, dark_mode, vibrant_colorful, etc.)
- 4 screen types per generation (hero, feature showcase, settings, empty state)
- S3 integration for generated image storage
- Error handling with graceful degradation
"""

import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI

from app.services.storage import storage_service
from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Models
# ============================================================================

class UIGeneratorConfig(BaseModel):
    """Configuration for UI generation."""
    app_description: str
    key_features: List[str] = []
    visual_style: str = "modern_minimal"
    num_screens: int = 4
    app_name: Optional[str] = None


# ============================================================================
# UI Generator Service
# ============================================================================

class UIGenerator:
    """Generates mobile app UI mockup images from text descriptions.

    This service creates realistic UI screenshots for mobile app products
    when users choose the 'generated' input mode instead of uploading
    actual screenshots.

    The generator creates 4 distinct screen types:
    - Hero/main dashboard
    - Feature showcase screen
    - Settings/profile screen
    - Empty state or onboarding screen

    Each generated image is uploaded to S3 and the URL is returned.
    """

    # Visual style specifications for UI generation
    STYLE_SPECS: Dict[str, Dict[str, Any]] = {
        "modern_minimal": {
            "name": "Modern Minimal",
            "description": "Clean, minimalist design with ample whitespace",
            "colors": "white backgrounds, subtle grays, single accent color",
            "typography": "thin sans-serif fonts, generous spacing",
            "elements": "rounded corners, subtle shadows, flat icons",
            "mood": "clean, professional, uncluttered"
        },
        "dark_mode": {
            "name": "Dark Mode",
            "description": "Dark UI optimized for OLED screens",
            "colors": "deep blacks, dark grays, vibrant accent colors",
            "typography": "medium weight sans-serif, high contrast",
            "elements": "subtle glows, card elevations, neon accents",
            "mood": "premium, focused, contemporary"
        },
        "vibrant_colorful": {
            "name": "Vibrant Colorful",
            "description": "Bold, energetic design with rich colors",
            "colors": "gradient backgrounds, bright primary colors, colorful accents",
            "typography": "bold headings, playful fonts",
            "elements": "rounded shapes, colorful icons, gradient buttons",
            "mood": "energetic, playful, engaging"
        },
        "professional_corporate": {
            "name": "Professional Corporate",
            "description": "Business-oriented, trustworthy design",
            "colors": "blues, whites, conservative palette",
            "typography": "traditional sans-serif, formal hierarchy",
            "elements": "structured layouts, data visualizations, charts",
            "mood": "trustworthy, efficient, professional"
        },
        "playful_friendly": {
            "name": "Playful Friendly",
            "description": "Fun, approachable design for casual apps",
            "colors": "soft pastels, warm tones, friendly palette",
            "typography": "rounded fonts, friendly weights",
            "elements": "illustrations, emoji, rounded everything",
            "mood": "friendly, welcoming, approachable"
        }
    }

    # Screen types to generate for each app
    SCREEN_TYPES: List[Dict[str, str]] = [
        {
            "id": "hero_dashboard",
            "name": "Hero Dashboard",
            "description": "Main dashboard or home screen showing key features",
            "prompt_suffix": "main dashboard view with key metrics and navigation"
        },
        {
            "id": "feature_showcase",
            "name": "Feature Showcase",
            "description": "Screen highlighting primary app functionality",
            "prompt_suffix": "feature screen showing the main functionality in action"
        },
        {
            "id": "settings_profile",
            "name": "Settings/Profile",
            "description": "Settings or user profile screen",
            "prompt_suffix": "settings or profile screen with user preferences"
        },
        {
            "id": "empty_onboarding",
            "name": "Empty/Onboarding State",
            "description": "Onboarding or empty state with helpful guidance",
            "prompt_suffix": "onboarding or empty state with helpful illustrations"
        }
    ]

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize UI Generator with OpenAI client.

        Args:
            openai_api_key: OpenAI API key. If not provided, uses settings.
        """
        api_key = openai_api_key or settings.openai_api_key
        if not api_key:
            logger.warning("OpenAI API key not configured for UI generation")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)

        self.storage = storage_service
        logger.info("UIGenerator initialized")

    @classmethod
    def get_available_styles(cls) -> List[Dict[str, str]]:
        """Get list of available visual styles for frontend display.

        Returns:
            List of style dictionaries with id, name, and description
        """
        return [
            {
                "id": style_id,
                "name": spec["name"],
                "description": spec["description"]
            }
            for style_id, spec in cls.STYLE_SPECS.items()
        ]

    async def generate_ui_screens(
        self,
        app_description: str,
        key_features: Optional[List[str]] = None,
        visual_style: str = "modern_minimal",
        app_name: Optional[str] = None,
        user_id: str = "system"
    ) -> List[str]:
        """Generate UI mockup images for a mobile app.

        Creates 4 UI screens based on the app description and style,
        uploads them to S3, and returns the URLs.

        Args:
            app_description: Description of the app and its purpose
            key_features: List of key features to showcase (max 10)
            visual_style: One of the 5 visual styles
            app_name: App name for branding in mockups
            user_id: User ID for S3 path organization

        Returns:
            List of 4 S3 URLs for the generated UI images
        """
        if not self.client:
            logger.error("OpenAI client not initialized - cannot generate UI")
            return []

        # Validate style
        if visual_style not in self.STYLE_SPECS:
            logger.warning(
                f"Invalid visual_style '{visual_style}', "
                f"using 'modern_minimal'"
            )
            visual_style = "modern_minimal"

        # Limit features
        features = (key_features or [])[:10]

        logger.info(
            f"Generating {len(self.SCREEN_TYPES)} UI screens for app: "
            f"{app_description[:50]}... (style: {visual_style})"
        )

        # Build prompts for each screen type
        prompts = self._build_screen_prompts(
            app_description=app_description,
            key_features=features,
            visual_style=visual_style,
            app_name=app_name
        )

        # Generate screens concurrently
        tasks = [
            self._generate_screen(prompt, screen_type, user_id)
            for prompt, screen_type in zip(prompts, self.SCREEN_TYPES)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        screen_urls = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to generate screen '{self.SCREEN_TYPES[i]['id']}': "
                    f"{result}"
                )
            elif result:
                screen_urls.append(result)

        logger.info(
            f"Generated {len(screen_urls)}/{len(self.SCREEN_TYPES)} "
            f"UI screens successfully"
        )

        return screen_urls

    def _build_screen_prompts(
        self,
        app_description: str,
        key_features: List[str],
        visual_style: str,
        app_name: Optional[str]
    ) -> List[str]:
        """Build image generation prompts for each screen type.

        Args:
            app_description: App description
            key_features: List of features to showcase
            visual_style: Visual style ID
            app_name: Optional app name

        Returns:
            List of prompts for each screen type
        """
        style_spec = self.STYLE_SPECS[visual_style]
        features_str = ", ".join(key_features) if key_features else "core features"

        prompts = []
        for screen in self.SCREEN_TYPES:
            prompt = self._build_single_prompt(
                app_description=app_description,
                features_str=features_str,
                style_spec=style_spec,
                screen=screen,
                app_name=app_name
            )
            prompts.append(prompt)

        return prompts

    def _build_single_prompt(
        self,
        app_description: str,
        features_str: str,
        style_spec: Dict[str, Any],
        screen: Dict[str, str],
        app_name: Optional[str]
    ) -> str:
        """Build a single DALL-E prompt for one screen.

        Args:
            app_description: App description
            features_str: Comma-separated features
            style_spec: Style specification dictionary
            screen: Screen type configuration
            app_name: Optional app name

        Returns:
            Formatted prompt string
        """
        app_name_text = f"App name: {app_name}. " if app_name else ""

        prompt = f"""Create a professional mobile app UI screenshot in vertical 9:16 aspect ratio.

App: {app_description}
{app_name_text}Features: {features_str}

Screen Type: {screen['name']} - {screen['prompt_suffix']}

Visual Style: {style_spec['name']}
- Colors: {style_spec['colors']}
- Typography: {style_spec['typography']}
- UI Elements: {style_spec['elements']}
- Mood: {style_spec['mood']}

Requirements:
- Ultra-realistic mobile app screenshot
- Modern iOS/Android design patterns
- Clean, polished UI with proper spacing
- Readable text and clear iconography
- No device frame (screen content only)
- Professional quality suitable for marketing
- {screen['description']}

Style: {style_spec['description']}"""

        return prompt

    async def _generate_screen(
        self,
        prompt: str,
        screen_type: Dict[str, str],
        user_id: str
    ) -> Optional[str]:
        """Generate a single UI screen and upload to S3.

        Args:
            prompt: DALL-E prompt for the screen
            screen_type: Screen type configuration
            user_id: User ID for S3 organization

        Returns:
            S3 URL of the generated image, or None on failure
        """
        try:
            logger.debug(f"Generating screen: {screen_type['id']}")

            # Generate image using DALL-E 3
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # Vertical for mobile (closest to 9:16)
                quality="hd",
                n=1
            )

            image_url = response.data[0].url

            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        raise Exception(
                            f"Failed to download image: HTTP {resp.status}"
                        )
                    image_data = await resp.read()

            # Upload to S3
            filename = f"ui_screen_{screen_type['id']}.png"
            s3_url = await self.storage.upload_file(
                file_content=image_data,
                folder="generated_ui",
                filename=filename,
                content_type="image/png",
                user_id=user_id
            )

            if s3_url:
                logger.info(
                    f"Generated and uploaded screen '{screen_type['id']}': "
                    f"{s3_url[:60]}..."
                )
                return s3_url
            else:
                logger.error(f"Failed to upload screen '{screen_type['id']}' to S3")
                return None

        except Exception as e:
            logger.error(
                f"Error generating screen '{screen_type['id']}': {e}"
            )
            return None
