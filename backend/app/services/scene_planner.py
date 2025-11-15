"""Scene Planner Service - LLM-based scene generation.

This service takes a product brief and brand information, then uses GPT-4o-mini
to generate a structured scene plan for the video. It creates:
1. Scene descriptions (hook, showcase, social proof, CTA)
2. Style specification (global visual consistency)
3. Text overlay specifications
4. Timing information
"""

import json
import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class StyleSpec(BaseModel):
    """Global visual style for all scenes."""
    lighting_direction: str  # e.g., "soft left, rim lighting"
    camera_style: str  # e.g., "product showcase, 45-degree angle"
    texture_materials: str  # e.g., "soft matte textures, no glossy surfaces"
    mood_atmosphere: str  # e.g., "uplifting, modern, energetic"
    color_palette: List[str]  # e.g., ["#FF6B6B", "#4ECDC4", "#44AF69"]
    grade_postprocessing: str  # e.g., "warm tones, subtle vignette, 10% desaturation"


class TextOverlay(BaseModel):
    """Text overlay configuration for a scene."""
    text: str
    position: str  # "top", "bottom", "center"
    duration: float  # seconds
    font_size: int  # pixels
    color: str  # hex color
    animation: str  # "fade_in", "slide", "none"


class Scene(BaseModel):
    """Individual scene in the video."""
    scene_id: int
    role: str  # "hook", "showcase", "social_proof", "cta"
    background_prompt: str  # For Wān model
    duration: float  # seconds
    overlay: TextOverlay
    camera_movement: str  # e.g., "static", "slow_zoom_in", "pan_right"


class AdProjectPlan(BaseModel):
    """Complete ad video plan."""
    brief: str
    brand_name: str
    target_audience: str
    duration_total: float  # seconds
    style_spec: StyleSpec
    scenes: List[Scene]


# ============================================================================
# Scene Planner Service
# ============================================================================

class ScenePlanner:
    """Plans video scenes using LLM."""

    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    async def plan_scenes(
        self,
        brief: str,
        brand_name: str,
        brand_colors: List[str],
        target_audience: str,
        duration_total: float = 30.0,
        num_scenes: int = 4,
    ) -> AdProjectPlan:
        """
        Generate video scene plan.

        Args:
            brief: Product description and key benefits
            brand_name: Brand/product name
            brand_colors: Brand color palette (hex)
            target_audience: Target audience description
            duration_total: Total video duration in seconds (default 30)
            num_scenes: Number of scenes to generate (default 4)

        Returns:
            AdProjectPlan with scenes and style specification
        """
        logger.info(f"Planning {num_scenes} scenes for '{brand_name}' ({duration_total}s video)")

        # Generate scene plan via LLM
        scenes_json = await self._generate_scenes_via_llm(
            brief=brief,
            brand_name=brand_name,
            brand_colors=brand_colors,
            target_audience=target_audience,
            duration_total=duration_total,
            num_scenes=num_scenes,
        )

        # Generate style specification
        style_spec = await self._generate_style_spec(
            brief=brief,
            brand_name=brand_name,
            brand_colors=brand_colors,
        )

        # Parse scenes
        scenes = []
        for i, scene_dict in enumerate(scenes_json):
            overlay_dict = scene_dict.get("overlay", {})
            scene = Scene(
                scene_id=i,
                role=scene_dict.get("role", "showcase"),
                background_prompt=scene_dict.get("background_prompt", ""),
                duration=scene_dict.get("duration", duration_total / num_scenes),
                overlay=TextOverlay(
                    text=overlay_dict.get("text", ""),
                    position=overlay_dict.get("position", "bottom"),
                    duration=overlay_dict.get("duration", 1.0),
                    font_size=overlay_dict.get("font_size", 48),
                    color=overlay_dict.get("color", "#FFFFFF"),
                    animation=overlay_dict.get("animation", "fade_in"),
                ),
                camera_movement=scene_dict.get("camera_movement", "static"),
            )
            scenes.append(scene)

        plan = AdProjectPlan(
            brief=brief,
            brand_name=brand_name,
            target_audience=target_audience,
            duration_total=duration_total,
            style_spec=style_spec,
            scenes=scenes,
        )

        logger.info(f"✅ Generated plan with {len(scenes)} scenes")
        return plan

    async def _generate_scenes_via_llm(
        self,
        brief: str,
        brand_name: str,
        brand_colors: List[str],
        target_audience: str,
        duration_total: float,
        num_scenes: int,
    ) -> List[Dict[str, Any]]:
        """Generate scene specifications using GPT-4o-mini."""

        scene_duration = duration_total / num_scenes

        prompt = f"""You are an expert video producer creating an advertising video.

Product Brief: {brief}
Brand Name: {brand_name}
Target Audience: {target_audience}
Total Duration: {duration_total}s
Number of Scenes: {num_scenes}
Scene Duration: ~{scene_duration}s each
Brand Colors: {', '.join(brand_colors)}

Create a {num_scenes}-scene video structure. Each scene should have:
1. A clear role (hook, showcase, social_proof, or cta)
2. A detailed prompt for the background video generator
3. Text overlay that reinforces the scene's purpose
4. Camera movement suggestion

Return ONLY a valid JSON array with {num_scenes} objects. Example structure:
[
  {{
    "scene_id": 0,
    "role": "hook",
    "background_prompt": "luxurious lifestyle setting, modern minimalist aesthetic, warm lighting",
    "duration": {scene_duration},
    "overlay": {{
      "text": "Transform Your Daily Routine",
      "position": "top",
      "duration": 2.0,
      "font_size": 48,
      "color": "#FFFFFF",
      "animation": "fade_in"
    }},
    "camera_movement": "slow_zoom_in"
  }},
  ...
]

Guidelines:
- Hook: Grab attention immediately (surprising stat, compelling image)
- Showcase: Show product benefits in action (3-5 benefits per scene if multiple)
- Social Proof: Show happy customers or results (testimonials, before/after)
- CTA: Clear call to action (website, app store link, discount code)
- Prompts: Detailed enough for AI video generation (lighting, style, mood)
- Text: Short, punchy, on-brand (2-8 words optimal)
- Colors: Use brand colors from palette
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Extract JSON from response
            response_text = response.choices[0].message.content
            
            # Try to parse JSON directly
            try:
                scenes = json.loads(response_text)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON from markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    scenes = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                    scenes = json.loads(json_str)
                else:
                    raise ValueError("Could not extract JSON from response")

            logger.info(f"Generated {len(scenes)} scenes via LLM")
            return scenes

        except Exception as e:
            logger.error(f"Error generating scenes: {e}")
            raise

    async def _generate_style_spec(
        self,
        brief: str,
        brand_name: str,
        brand_colors: List[str],
    ) -> StyleSpec:
        """Generate global style specification using GPT-4o-mini."""

        prompt = f"""You are an expert cinematographer and color grader.

Product Brief: {brief}
Brand Name: {brand_name}
Brand Colors: {', '.join(brand_colors)}

Create a consistent visual style specification for a product video. Consider:
- The brand personality
- Target audience expectations
- Modern advertising trends
- Product category

Return ONLY a valid JSON object with exactly this structure:
{{
  "lighting_direction": "description of key light position and quality",
  "camera_style": "description of how camera frames the product",
  "texture_materials": "visual texture description",
  "mood_atmosphere": "overall emotional tone",
  "color_palette": ["#HEX1", "#HEX2", "#HEX3"],
  "grade_postprocessing": "color grading and effects description"
}}

Be specific and visual in descriptions. Example:
{{
  "lighting_direction": "soft diffused light from upper left, warm rim lighting on edges",
  "camera_style": "product-centric close-ups with shallow depth of field, 45-degree angles",
  "texture_materials": "matte surfaces, no harsh reflections, tactile feeling",
  "mood_atmosphere": "premium, sophisticated, aspirational",
  "color_palette": ["#F7DC6F", "#3498DB", "#E8DAEF"],
  "grade_postprocessing": "warm color temperature, lifted blacks, subtle vignette, 8% desaturation"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            response_text = response.choices[0].message.content

            # Parse JSON
            try:
                style_dict = json.loads(response_text)
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    style_dict = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                    style_dict = json.loads(json_str)
                else:
                    # Fallback to defaults
                    logger.warning("Could not parse style spec from LLM, using defaults")
                    style_dict = {
                        "lighting_direction": "soft natural light from upper left",
                        "camera_style": "product showcase, 45-degree angle, shallow focus",
                        "texture_materials": "clean, modern, tactile",
                        "mood_atmosphere": "uplifting, professional, modern",
                        "color_palette": brand_colors[:3]
                        if brand_colors
                        else ["#3498DB", "#2ECC71", "#E74C3C"],
                        "grade_postprocessing": "warm tones, lifted shadows, 5% desaturation",
                    }

            return StyleSpec(**style_dict)

        except Exception as e:
            logger.error(f"Error generating style spec: {e}")
            # Return reasonable defaults
            return StyleSpec(
                lighting_direction="soft diffused light from upper left",
                camera_style="product-centric, 45-degree angle",
                texture_materials="matte, modern, tactile",
                mood_atmosphere="professional, uplifting",
                color_palette=brand_colors[:3]
                if brand_colors
                else ["#3498DB", "#2ECC71", "#E74C3C"],
                grade_postprocessing="warm color temperature, lifted blacks",
            )

