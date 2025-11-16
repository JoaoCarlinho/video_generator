"""Scene Planner Service - LLM-based scene generation with full creative freedom.

This service takes a creative prompt and brand information, then uses GPT-4o-mini
to generate a structured scene plan for the video with complete directorial freedom.

Key Features:
- Flexible scene count (3-6 scenes based on content)
- Variable scene durations (3-15s per scene)
- Smart asset placement (logo/product only when makes sense)
- Background type categorization for better compositing
- Camera movements and transitions
- Adaptive pacing based on narrative
"""

import json
import logging
from typing import List, Dict, Any, Optional
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
    music_mood: str  # e.g., "uplifting", "dramatic" - for audio generation


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
    role: str  # "hook", "build", "showcase", "proof", "cta"
    duration: int  # seconds (3-15 range)
    background_prompt: str  # For video generation model
    background_type: str  # "cinematic", "product_stage", "lifestyle", "abstract"
    use_product: bool  # Whether to composite product in this scene
    use_logo: bool  # Whether to show logo in this scene
    camera_movement: str  # e.g., "static", "slow_zoom_in", "pan_right"
    transition_to_next: str  # "cut", "fade", "zoom"
    overlay: TextOverlay


class AdProjectPlan(BaseModel):
    """Complete ad video plan."""
    creative_prompt: str
    brand_name: str
    target_audience: str
    total_duration: int  # Actual total duration (sum of scenes)
    style_spec: StyleSpec
    scenes: List[Scene]


# ============================================================================
# Scene Planner Service
# ============================================================================

class ScenePlanner:
    """Plans video scenes using LLM with full creative freedom."""

    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    async def plan_scenes(
        self,
        creative_prompt: str,
        brand_name: str,
        brand_description: Optional[str],
        brand_colors: List[str],
        brand_guidelines: Optional[str],
        target_audience: Optional[str],
        target_duration: int = 30,
        has_product: bool = False,
        has_logo: bool = False,
        aspect_ratio: str = "16:9",
    ) -> AdProjectPlan:
        """
        Generate video scene plan with full creative freedom.

        Args:
            creative_prompt: User's creative vision for the video
            brand_name: Brand/product name
            brand_description: Brand story, values, personality
            brand_colors: Brand color palette (hex)
            brand_guidelines: Brand guidelines text (optional)
            target_audience: Target audience description
            target_duration: Target total duration in seconds (flexible ±20%)
            has_product: Whether product image is available
            has_logo: Whether logo is available
            aspect_ratio: Video aspect ratio (9:16, 1:1, or 16:9) to optimize scene planning

        Returns:
            AdProjectPlan with scenes and style specification
        """
        logger.info(f"Planning video for '{brand_name}' (target: {target_duration}s)")
        logger.info(f"Assets available - Product: {has_product}, Logo: {has_logo}")

        # Generate scene plan via LLM
        scenes_json = await self._generate_scenes_via_llm(
            creative_prompt=creative_prompt,
            brand_name=brand_name,
            brand_description=brand_description,
            brand_colors=brand_colors,
            brand_guidelines=brand_guidelines,
            target_audience=target_audience or "general consumers",
            target_duration=target_duration,
            has_product=has_product,
            has_logo=has_logo,
            aspect_ratio=aspect_ratio,
        )

        # Generate style specification
        style_spec = await self._generate_style_spec(
            creative_prompt=creative_prompt,
            brand_name=brand_name,
            brand_description=brand_description,
            brand_colors=brand_colors,
            brand_guidelines=brand_guidelines,
        )

        # Parse scenes
        scenes = []
        total_duration = 0
        for scene_dict in scenes_json:
            overlay_dict = scene_dict.get("overlay", {})
            duration = scene_dict.get("duration", 5)
            total_duration += duration
            
            scene = Scene(
                scene_id=len(scenes),
                role=scene_dict.get("role", "showcase"),
                duration=duration,
                background_prompt=scene_dict.get("background_prompt", ""),
                background_type=scene_dict.get("background_type", "cinematic"),
                use_product=scene_dict.get("use_product", False),
                use_logo=scene_dict.get("use_logo", False),
                camera_movement=scene_dict.get("camera_movement", "static"),
                transition_to_next=scene_dict.get("transition_to_next", "cut"),
                overlay=TextOverlay(
                    text=overlay_dict.get("text", ""),
                    position=overlay_dict.get("position", "bottom"),
                    duration=overlay_dict.get("duration", 2.0),
                    font_size=overlay_dict.get("font_size", 48),
                    color=overlay_dict.get("color", brand_colors[0] if brand_colors else "#FFFFFF"),
                    animation=overlay_dict.get("animation", "fade_in"),
                ),
            )
            scenes.append(scene)

        plan = AdProjectPlan(
            creative_prompt=creative_prompt,
            brand_name=brand_name,
            target_audience=target_audience or "general consumers",
            total_duration=total_duration,
            style_spec=style_spec,
            scenes=scenes,
        )

        logger.info(f"✅ Generated plan with {len(scenes)} scenes (total: {total_duration}s)")
        return plan

    async def _generate_scenes_via_llm(
        self,
        creative_prompt: str,
        brand_name: str,
        brand_description: Optional[str],
        brand_colors: List[str],
        brand_guidelines: Optional[str],
        target_audience: str,
        target_duration: int,
        has_product: bool,
        has_logo: bool,
        aspect_ratio: str = "16:9",
    ) -> List[Dict[str, Any]]:
        """Generate scene specifications using GPT-4o-mini with full creative freedom."""

        # Build context about available assets
        asset_context = []
        if has_product:
            asset_context.append("- Product Image: Available for compositing")
        if has_logo:
            asset_context.append("- Brand Logo: Available for display")
        if not has_product and not has_logo:
            asset_context.append("- No product/logo images provided")
        
        asset_instructions = "\n".join(asset_context)

        # Build brand context
        brand_context = f"Brand: {brand_name}"
        if brand_description:
            brand_context += f"\nBrand Story: {brand_description}"
        if brand_guidelines:
            # Truncate if too long
            guidelines_preview = brand_guidelines[:500] + ("..." if len(brand_guidelines) > 500 else "")
            brand_context += f"\nBrand Guidelines: {guidelines_preview}"

        prompt = f"""You are a world-class video director and creative director creating an advertising video.

=== CREATIVE BRIEF ===
{creative_prompt}

=== BRAND INFORMATION ===
{brand_context}
Brand Colors: {', '.join(brand_colors)}
Target Audience: {target_audience}

=== PRODUCTION CONSTRAINTS ===
Target Duration: {target_duration}s (flexible ±20%)
Duration Range per Scene: 3-15 seconds
Recommended Scene Count: 3-6 scenes
Video Aspect Ratio: {aspect_ratio}
  - 16:9 (Horizontal): YouTube, Web, Presentations, Widescreen
  - 9:16 (Vertical): TikTok, Instagram Reels, Shorts (Portrait mode)
  - 1:1 (Square): Instagram Feed, Facebook, Pinterest

=== AVAILABLE ASSETS ===
{asset_instructions}

=== YOUR CREATIVE MISSION ===
Create a video that brings this creative vision to life with complete directorial freedom.

You decide:
• Number of scenes (3-6 recommended, but use what the story needs)
• Duration of each scene (vary for pacing - some short punchy scenes, some longer)
• When to show product/logo (strategic placement, not every scene)
• Camera movements and angles
• Scene transitions
• Background styles that complement the creative vision
• Text overlays that enhance the narrative

=== CREATIVE GUIDELINES ===
1. **Narrative Flow**: Create a story arc that feels natural, not choppy
2. **Strategic Asset Usage**:
   - Use product image in 1-3 scenes where it makes narrative sense (showcase, proof)
   - Use logo primarily in final scene (like professional commercials) or brand-building moments
   - Don't force assets into every scene - backgrounds alone can be powerful
3. **Background Types**:
   - "cinematic": Rich, atmospheric, story-driven visuals
   - "product_stage": Clean, simple backgrounds that complement product/logo overlays
   - "lifestyle": Real-world settings, relatable moments
   - "abstract": Motion graphics, textures, patterns, energetic
4. **Pacing**: Vary scene lengths for impact (quick cuts for energy, longer holds for emotion)
5. **Transitions**: Choose transitions that enhance flow:
   - "cut": Sharp, energetic, modern
   - "fade": Smooth, elegant, emotional
   - "zoom": Dynamic, attention-grabbing

=== SCENE ROLES ===
- **hook**: Grab attention immediately (3-7s)
- **build**: Build interest, set context (4-8s)
- **showcase**: Show product/benefit in action (5-10s)
- **proof**: Social proof, results, testimonials (4-8s)
- **cta**: Clear call to action (3-6s)

=== OUTPUT FORMAT ===
Return ONLY valid JSON array. Example structure:

[
  {{
    "scene_id": 0,
    "role": "hook",
    "duration": 5,
    "background_prompt": "Dynamic fast-paced urban environment at golden hour, young professionals walking confidently, modern architecture, shallow depth of field, cinematic look with warm tones and high contrast",
    "background_type": "lifestyle",
    "use_product": false,
    "use_logo": false,
    "camera_movement": "slow_zoom_in",
    "transition_to_next": "cut",
    "overlay": {{
      "text": "Transform Your Skin",
      "position": "center",
      "duration": 3.0,
      "font_size": 56,
      "color": "{brand_colors[0] if brand_colors else '#FFFFFF'}",
      "animation": "fade_in"
    }}
  }},
  {{
    "scene_id": 1,
    "role": "showcase",
    "duration": 8,
    "background_prompt": "Minimal clean white studio background with subtle gradient, soft diffused lighting from top-left, modern aesthetic, product-focused environment with gentle shadows",
    "background_type": "product_stage",
    "use_product": true,
    "use_logo": false,
    "camera_movement": "static",
    "transition_to_next": "fade",
    "overlay": {{
      "text": "Proven Results in 7 Days",
      "position": "bottom",
      "duration": 4.0,
      "font_size": 44,
      "color": "{brand_colors[0] if brand_colors else '#FFFFFF'}",
      "animation": "slide"
    }}
  }},
  {{
    "scene_id": 2,
    "role": "cta",
    "duration": 5,
    "background_prompt": "Abstract flowing gradient background with brand colors, smooth motion, modern and energetic feel, professional commercial aesthetic",
    "background_type": "abstract",
    "use_product": false,
    "use_logo": true,
    "camera_movement": "slow_zoom_out",
    "transition_to_next": "fade",
    "overlay": {{
      "text": "Get Yours Today",
      "position": "center",
      "duration": 3.0,
      "font_size": 52,
      "color": "{brand_colors[0] if brand_colors else '#FFFFFF'}",
      "animation": "fade_in"
    }}
  }}
]

=== IMPORTANT NOTES ===
- background_prompt should be 2-3 detailed sentences for AI video generation
- Include lighting, mood, camera angle, style descriptors
- Text overlays should be SHORT (2-8 words max)
- Camera movements: static, slow_zoom_in, slow_zoom_out, pan_left, pan_right
- Make sure total duration is roughly {target_duration}s (some variance is fine)
- Don't use product/logo in EVERY scene - be strategic

Create the video now!"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.8,  # Higher creativity
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert video director and creative strategist. You create compelling advertising videos with strong narratives and strategic visual choices. You output only valid JSON."
                    },
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

            # Validate scene count
            if len(scenes) < 2:
                raise ValueError(f"Too few scenes generated: {len(scenes)}")
            if len(scenes) > 8:
                logger.warning(f"Many scenes generated ({len(scenes)}), trimming to 8")
                scenes = scenes[:8]

            # Validate durations
            for scene in scenes:
                if not 3 <= scene.get("duration", 5) <= 15:
                    logger.warning(f"Scene {scene.get('scene_id')} duration out of range, clamping")
                    scene["duration"] = max(3, min(15, scene.get("duration", 5)))

            logger.info(f"Generated {len(scenes)} scenes via LLM")
            return scenes

        except Exception as e:
            logger.error(f"Error generating scenes: {e}")
            raise

    async def _generate_style_spec(
        self,
        creative_prompt: str,
        brand_name: str,
        brand_description: Optional[str],
        brand_colors: List[str],
        brand_guidelines: Optional[str],
    ) -> StyleSpec:
        """Generate global style specification using GPT-4o-mini."""

        # Build brand context
        brand_context = f"Brand: {brand_name}"
        if brand_description:
            brand_context += f"\nBrand Personality: {brand_description}"
        if brand_guidelines:
            guidelines_preview = brand_guidelines[:500] + ("..." if len(brand_guidelines) > 500 else "")
            brand_context += f"\nGuidelines: {guidelines_preview}"

        prompt = f"""You are an expert cinematographer and color grader creating a consistent visual style.

=== CREATIVE VISION ===
{creative_prompt}

=== BRAND CONTEXT ===
{brand_context}
Brand Colors: {', '.join(brand_colors)}

=== YOUR TASK ===
Create a visual style specification that ensures all scenes look cohesive and professional.
This style will be applied to ALL video generation, so be specific and consistent.

Consider:
- The creative vision and emotional tone
- Brand personality and values
- Target audience expectations
- Modern advertising aesthetics

=== OUTPUT FORMAT ===
Return ONLY valid JSON with this exact structure:

{{
  "lighting_direction": "describe key light position, quality, and mood (e.g., 'soft diffused from upper left with subtle rim light, warm and inviting')",
  "camera_style": "describe framing and movement approach (e.g., 'close-ups with shallow depth of field, 45-degree product angles, smooth movements')",
  "texture_materials": "describe surface qualities (e.g., 'matte surfaces, tactile textures, no harsh reflections, natural materials')",
  "mood_atmosphere": "overall emotional tone (e.g., 'uplifting, modern, aspirational, confident')",
  "color_palette": ["{brand_colors[0] if brand_colors else '#3498DB'}", "{brand_colors[1] if len(brand_colors) > 1 else '#2ECC71'}", "{brand_colors[2] if len(brand_colors) > 2 else '#E74C3C'}"],
  "grade_postprocessing": "color grading description (e.g., 'warm color temperature, lifted blacks, subtle vignette, 8% desaturation, film grain')",
  "music_mood": "single word mood for background music (e.g., 'uplifting', 'dramatic', 'energetic', 'calm', 'luxurious', 'playful')"
}}

Be specific and visual in all descriptions. Think like a professional cinematographer."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cinematographer. You create detailed visual style specifications. You output only valid JSON."
                    },
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
                    style_dict = self._get_default_style_spec(brand_colors)

            # Ensure music_mood is present
            if "music_mood" not in style_dict:
                style_dict["music_mood"] = "uplifting"

            return StyleSpec(**style_dict)

        except Exception as e:
            logger.error(f"Error generating style spec: {e}")
            # Return reasonable defaults
            return StyleSpec(**self._get_default_style_spec(brand_colors))

    def _get_default_style_spec(self, brand_colors: List[str]) -> Dict[str, Any]:
        """Get default style spec as fallback."""
        return {
            "lighting_direction": "soft diffused light from upper left with gentle rim lighting",
            "camera_style": "product-centric close-ups with shallow depth of field, 45-degree angles",
            "texture_materials": "clean modern surfaces, tactile feeling, matte finishes",
            "mood_atmosphere": "professional, uplifting, modern",
            "color_palette": brand_colors[:3] if brand_colors else ["#3498DB", "#2ECC71", "#E74C3C"],
            "grade_postprocessing": "warm color temperature, lifted blacks, subtle vignette",
            "music_mood": "uplifting",
        }
