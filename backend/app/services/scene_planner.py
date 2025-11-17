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
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.services.style_manager import StyleManager

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
        selected_style: Optional[str] = None,
        extracted_style: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate video scene plan with full creative freedom and PHASE 7 style consistency.

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
            selected_style: (PHASE 7) User-selected or LLM-inferred style name or None

        Returns:
            Dictionary with scenes, style_spec, chosenStyle, styleSource
        """
        logger.info(f"Planning video for '{brand_name}' (target: {target_duration}s)")
        logger.info(f"Assets available - Product: {has_product}, Logo: {has_logo}")
        
        # STEP 1: Derive tone from target audience (Task 2)
        tone = await self._derive_tone_from_audience(
            target_audience=target_audience or "general consumers",
            brand_description=brand_description
        )
        logger.info(f"📊 Derived tone: '{tone}' from audience '{target_audience or 'general consumers'}'")
        
        # STEP 2: PHASE 7 - Determine the ONE style for entire video
        if selected_style:
            # User provided style
            chosen_style = selected_style
            style_source = "user_selected"
            logger.info(f"Using user-selected style: {chosen_style}")
        else:
            # LLM chooses from 5 styles based on brief + brand
            logger.info("No style selected - LLM will choose from 5 styles")
            chosen_style, style_source = await self._llm_choose_style(
                creative_prompt=creative_prompt,
                brand_name=brand_name,
                brand_description=brand_description,
                target_audience=target_audience or "general consumers"
            )

        # STEP 3: Generate scene plan via LLM (with tone context)
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
            chosen_style=chosen_style,
        )

        style_to_background = {
            "cinematic": "cinematic",
            "dark_premium": "product_stage",
            "minimal_studio": "product_stage",
            "lifestyle": "lifestyle",
            "2d_animated": "abstract",
        }

        forced_background_type = style_to_background.get(chosen_style, "cinematic")

        for scene_dict in scenes_json:
            role = scene_dict.get("role")

            # 3) Enforce unified background_type
            scene_dict["background_type"] = forced_background_type

            # 4) Limit product usage — only hook & showcase
            if role not in ["hook", "showcase"]:
                scene_dict["use_product"] = False
                scene_dict["product_position"] = None
                scene_dict["product_scale"] = None

            # 4) Limit logo usage — only hook & CTA
            if role not in ["hook", "cta"]:
                scene_dict["use_logo"] = False
                scene_dict["logo_position"] = None
                scene_dict["logo_scale"] = None

            # 5) Remove text overlays except hook & CTA
            if role not in ["hook", "cta"]:
                if "overlay" in scene_dict:
                    scene_dict["overlay"]["text"] = ""

        # 6) Ensure last scene ends smoothly (CTA)
        last_scene = scenes_json[-1]
        last_scene["transition_to_next"] = "fade"
        last_scene["camera_movement"] = "slow_zoom_out"

        # STEP 4: Generate style specification (with derived tone)
        if extracted_style:
            logger.info("Applying extracted style override from reference image")
            style_spec = StyleSpec(
                lighting_direction=extracted_style.get("lighting_direction", ""),
                camera_style=extracted_style.get("camera_style", ""),
                texture_materials=extracted_style.get("texture_materials", ""),
                mood_atmosphere=extracted_style.get("mood_atmosphere", ""),
                color_palette=extracted_style.get("color_palette", brand_colors[:3]),
                grade_postprocessing=extracted_style.get("grade_postprocessing", ""),
                music_mood=extracted_style.get("music_mood", "ambient")
            )
        else:
            style_spec = await self._generate_style_spec(
                creative_prompt=creative_prompt,
                brand_name=brand_name,
                brand_description=brand_description,
                brand_colors=brand_colors,
                brand_guidelines=brand_guidelines,
                derived_tone=tone,
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

        # PHASE 7: CRITICAL - All scenes MUST use the same style
        # Enforce this by adding style to each scene
        scenes_dict = []
        for scene in scenes:
            scene_data = scene.model_dump()
            scene_data['style'] = chosen_style  # Force same style on all scenes
            scenes_dict.append(scene_data)
        
        # Validate: all scenes have same style
        for i, scene_data in enumerate(scenes_dict):
            if scene_data.get('style') != chosen_style:
                logger.warning(f"Scene {i} tried different style: {scene_data.get('style')} → forcing {chosen_style}")
                scene_data['style'] = chosen_style
        
        assert all(s.get('style') == chosen_style for s in scenes_dict), \
            f"Style consistency violated! All scenes must use {chosen_style}"
        
        logger.info(f"✅ Generated plan with {len(scenes)} scenes (total: {total_duration}s, style: {chosen_style})")
        logger.info(f"✅ CRITICAL: All {len(scenes)} scenes enforced to use SAME style: {chosen_style}")

        # PHASE 7 + Task 2: Return dict with style information and derived tone
        return {
            "scenes": scenes_dict,
            "style_spec": style_spec.model_dump(),
            "chosenStyle": chosen_style,  # The ONE style used for entire video
            "styleSource": style_source,  # "user_selected" or "llm_inferred"
            "derivedTone": tone,  # Task 2: Derived tone from audience
            "creative_prompt": creative_prompt,
            "brand_name": brand_name,
            "target_audience": target_audience or "general consumers",
            "total_duration": total_duration,
        }

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
        chosen_style: Optional[str] = None,
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

        prompt = f"""You are a world-class video director and creative director creating a **modern, cinematic product-first advertising video**.
Think of the visual language used by brands like Apple, Nike, and Tesla: minimal, design-driven, and emotionally powerful, with the product as the hero.

By default, avoid generic “people enjoying the product” shots and cliché stock-style scenes.
If the creative prompt explicitly calls for people, use them sparingly, in stylized, cinematic ways (silhouettes, hands, partial figures), not staged group shots.

=== CREATIVE BRIEF ===
{creative_prompt}

=== BRAND INFORMATION ===
{brand_context}
Brand Colors: {', '.join(brand_colors)}
Target Audience: {target_audience}

If any style or tone is implied (e.g. cinematic, dark premium, minimal studio, lifestyle, 2D animated), you MUST reflect that in background_prompt, lighting, and mood.

**CRITICAL BRAND NAME RULE:**
- The FIRST scene (hook/intro) should mention or reference "{brand_name}"
- The FINAL scene (CTA) MUST include "{brand_name}" in the text overlay
- Example final overlay: "Try {brand_name} Today" or "Shop {brand_name} Now" or "Get {brand_name}"

=== PRODUCTION CONSTRAINTS ===
Target Duration: {target_duration}s (flexible ±20%)
Duration Range per Scene: 3-12 seconds
Recommended Scene Count: 3-6 scenes
Video Aspect Ratio: {aspect_ratio}
  - 16:9 (Horizontal): YouTube, Web, Presentations, Widescreen
  - 9:16 (Vertical): TikTok, Instagram Reels, Shorts (Portrait mode)
  - 1:1 (Square): Instagram Feed, Facebook, Pinterest

=== AVAILABLE ASSETS ===
{asset_instructions}

=== YOUR CREATIVE MISSION ===
Create a **modern, cinematic, product-centric** video that brings this creative vision to life.

You decide:
• Number of scenes (3-6 recommended, but use what the story needs)
• Duration of each scene (vary for pacing - some short punchy scenes, some longer)
• When to show product/logo (strategic placement, not every scene)
• When to use text overlays (only when they add clarity or impact)
• Camera movements and angles (modern, cinematic framing)
• Scene transitions
• Background styles that complement the creative vision and chosen style
• You MUST generate every background_prompt using the CHOSEN STYLE: {chosen_style}. 
  Do not mix styles. Every scene must visually belong to the same style category.
• Text overlays that enhance the narrative without clutter

=== MODERN CREATIVE PRINCIPLES ===
1. **Product-First Cinematic Approach**
   - The product should feel like the “hero object” of the film.
   - Use strong composition, macro close-ups, slow motion, controlled lighting, and negative space.
   - Avoid outdated montages of random people smiling at the camera or using the product in a generic way.

2. **Minimal Use of People (Default)**
   - By default, do NOT include visible faces or crowds.
   - If people are required by the brief, treat them as **cinematic elements** (silhouettes, hands interacting with product, reflections, partial figures) rather than the main subject.

3. **Coherent Visual Language (All Scenes Must Fit Together)**
   - All scenes should feel like parts of the SAME film, not random clips.
   - Maintain consistent:
     - Overall style (cinematic / dark premium / minimal studio / lifestyle / 2D animated)
     - Color palette and lighting mood
     - Level of realism and rendering quality
   - Reuse visual motifs (lighting direction, environment type, product presentation) so cuts feel natural and intentional.

4. **Use of Style**
    - CHOSEN STYLE FOR ENTIRE VIDEO: {chosen_style} (or extracted style if provided)

    - ALL SCENES MUST FOLLOW THIS STYLE.
    - THIS IS CRITICAL — DO NOT MIX STYLES.

    - EXAMPLES:
        - cinematic → dramatic lighting, depth of field, premium realism  
        - dark_premium → black studio, rim lighting, contrast-heavy  
        - minimal_studio → bright white background, soft daylight, clean shadows  
        - lifestyle → real environments, warm lighting, natural textures  
        - 2d_animated → vector motion graphics, flat shading, illustrated look  

=== CREATIVE GUIDELINES ===
1. **Narrative Flow**
   - Create a clear visual arc: strong hook → build → showcase → proof/credibility → clean CTA.
   - The story should feel like one continuous cinematic piece, not a set of disconnected shots.
   - Ensure that each scene transitions smoothly into the next in tone, style, and visual language.

2. **Strategic Asset Usage (Modern Product Style)**
   - Use the product image in scenes where it strengthens the story (hero shots, feature highlights, key moments), not mechanically in every scene.
   - Use logo in the **intro** (subtle) and **CTA** (clear), and optionally in one brand-building moment.
   - Text overlay, product placement, and logo are **NOT required in every scene**. Some scenes can be purely visual and atmospheric.

3. **Background Types (Refined for Modern Ads)**
   - "cinematic": Highly crafted visual environments, dramatic lighting, shallow depth of field, strong compositions, product integrated into the scene.
   - "product_stage": Minimal, studio-like setups (dark or light), pedestals, soft gradients, controlled shadows; the product is the main focus.
   - "lifestyle": Real-world or stylized environments that hint at use-case, but still keep product as hero. People optional and subtle.
   - "abstract": Motion graphics, light streaks, gradients, textures, and product silhouettes that evoke brand feeling rather than literal scenes.

4. **Pacing**
   - Vary scene lengths for rhythm: quick, impactful moments mixed with longer, lingering shots on the product.
   - Hooks are shorter and punchy; hero product shots and macro close-ups can hold longer for impact.
   - Ensure the pacing across scenes feels intentional and smooth, not chaotic.

5. **Transitions**
   - Use modern, confident transitions:
     - "cut": Clean, decisive, modern.
     - "fade": Elegant, premium, often between emotional or tonal shifts.
     - "zoom": Use sparingly for emphasis (e.g. reveal, hero moment).
   - Transitions should support flow. Avoid jarring, random-feeling changes.
   - The **final scene must end smoothly**: the composition should resolve and the movement should naturally slow or fade out rather than an abrupt or random cut.

6. **Camera & Framing**
   - Emphasize modern product cinematography:
     - Macro close-ups of materials, edges, textures, and logos.
     - Slow, deliberate camera motion (slow_zoom_in / slow_zoom_out / pan_left / pan_right).
     - Use negative space and center-weighted framing for iconic hero shots.
   - Avoid chaotic or handheld wobble unless explicitly justified by the concept.

=== SCENE ROLES (MODERN INTERPRETATION) ===
- **hook**: Immediate, striking visual of the product or its silhouette. Strong lighting and composition that feels premium (3-7s).
- **build**: Expand the world around the product: variations of angles, context, or features (4-8s).
- **showcase**: Highlight specific benefits or design features with macro details and slow motion (5-10s).
- **proof**: Use visual proof (comparisons, feature demos, UI overlays, numbers, or abstract visual metaphors) instead of cheesy testimonials (4-8s).
- **cta**: Clean, minimal end card with product + logo + very short CTA text (3-6s). The final moment should feel like a natural conclusion, not a hard, random cut.

=== OUTPUT FORMAT ===
Return ONLY valid JSON array. Example structure:

[
  {{
    "scene_id": 0,
    "role": "hook",
    "duration": 5,
    "background_prompt": "Ultra-minimal dark studio with a single spotlight revealing the edge of the shoe, subtle fog, high contrast, shallow depth of field, premium cinematic commercial lighting",
    "background_type": "product_stage",
    "use_product": true,
    "product_position": "center",
    "product_scale": 0.5,
    "use_logo": true,
    "logo_position": "top_right",
    "logo_scale": 0.10,
    "camera_movement": "slow_zoom_in",
    "transition_to_next": "cut",
    "overlay": {{
      "text": "{brand_name}",
      "position": "bottom",
      "duration": 3.0,
      "font_size": 48,
      "color": "{brand_colors[0] if brand_colors else '#FFFFFF'}",
      "animation": "fade_in"
    }}
  }},
  {{
    "scene_id": 1,
    "role": "showcase",
    "duration": 8,
    "background_prompt": "Clean white studio with soft natural light, the product on a floating pedestal, gentle shadows, modern high-end product photography aesthetic, macro focus on materials and logo",
    "background_type": "product_stage",
    "use_product": true,
    "product_position": "center",
    "product_scale": 0.45,
    "use_logo": false,
    "logo_position": null,
    "logo_scale": null,
    "camera_movement": "pan_left",
    "transition_to_next": "fade",
    "overlay": {{
      "text": "Design That Moves",
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
    "background_prompt": "Abstract, softly animated gradient background using brand colors, subtle particles, product in silhouette or clean outline, premium minimal end card design",
    "background_type": "abstract",
    "use_product": false,
    "product_position": null,
    "product_scale": null,
    "use_logo": true,
    "logo_position": "bottom_center",
    "logo_scale": 0.15,
    "camera_movement": "slow_zoom_out",
    "transition_to_next": "fade",
    "overlay": {{
      "text": "Get {brand_name}",
      "position": "center",
      "duration": 3.0,
      "font_size": 52,
      "color": "{brand_colors[0] if brand_colors else '#FFFFFF'}",
      "animation": "fade_in"
    }}
  }}
]

=== PRODUCT & LOGO POSITIONING GUIDELINES ===
   IMPORTANT: DO NOT place product in every scene. DO NOT place logo in every scene.
1. **Product Positioning** (when use_product=true):
   - "center": Hero shots, product-focused scenes (product_scale: 0.4-0.6)
   - "bottom_right": Scenes where text or graphics occupy top/left (product_scale: 0.25-0.35)
   - "left" or "right": Side placement when text or secondary visuals occupy the opposite side (product_scale: 0.3-0.4)
   - Set product_position and product_scale explicitly in JSON
   - If use_product=false, set product_position=null and product_scale=null

2. **Logo Positioning** (when use_logo=true):
   - First scene (intro): "top_left" or "top_right" subtle branding (logo_scale: 0.08-0.12)
   - Final scene (CTA): "bottom_center" or near CTA text (logo_scale: 0.12-0.18)
   - Don't use logo in EVERY scene - intro + CTA are usually enough for modern premium ads
   - Set logo_position and logo_scale explicitly in JSON
   - If use_logo=false, set logo_position=null and logo_scale=null

3. **Avoid Conflicts**:
   - If product in "bottom_right", put logo in "top_left" or "top_right"
   - If text overlay at "bottom", avoid product/logo at "bottom_center"
   - Product and logo should not overlap each other

**CRITICAL**: Output product_position, product_scale, logo_position, logo_scale fields explicitly for EVERY scene!

=== IMPORTANT NOTES ===
- background_prompt should be 2-3 detailed sentences optimized for AI video generation.
- Always include lighting, mood, camera perspective, and style descriptors.
- Text overlays should be SHORT (2-8 words max) and used only in scenes where they genuinely add value.
- Some scenes can have no text overlay at all; when no overlay is needed, you may set overlay text to an empty string or keep it extremely minimal.
- Camera movements: static, slow_zoom_in, slow_zoom_out, pan_left, pan_right.
- Make sure total duration is roughly {target_duration}s (some variance is fine).
- Don't use product/logo/text overlay in EVERY scene - be strategic, cinematic, and modern.
- Ensure all scenes feel stylistically consistent and that the **final scene ends smoothly**, with a natural visual resolution rather than a random or abrupt cut.
- The final CTA must end smoothly with slow zoom out + fade.
- Most scenes should have NO text overlay. Only hook + CTA should include text.

Plan the scene now!"""


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

    async def _llm_choose_style(
        self,
        creative_prompt: str,
        brand_name: str,
        brand_description: Optional[str],
        target_audience: str,
    ) -> Tuple[str, str]:
        """
        PHASE 7: LLM chooses best style from 5 predefined styles based on brief and brand.
        
        Returns:
            Tuple of (chosen_style, style_source) where chosen_style is one of the 5 styles
        """
        try:
            prompt = f"""You are a creative director analyzing a brand and creative brief to select the best visual style for an advertising video.

Based on the following information, choose the BEST visual style from these 5 options:

1. cinematic - High-quality camera feel, dramatic lighting, depth of field, professional cinematography
2. dark_premium - Black background, rim lighting, contrast-heavy, product floating or rotating, luxury aesthetic
3. minimal_studio - Minimal, bright, Apple-style, clean compositions, professional simplicity
4. lifestyle - Product used in real-world scenarios, authentic moments, relatable contexts
5. 2d_animated - Modern vector-style animation, motion graphics, playful, modern

=== BRAND & BRIEF ===
Brand: {brand_name}
{f"Brand Description: {brand_description}" if brand_description else ""}
Target Audience: {target_audience}
Creative Brief: {creative_prompt}

=== YOUR TASK ===
Analyze the brand, audience, and creative brief. Choose ONE style that best fits.
Return ONLY the style ID (e.g., "cinematic") - nothing else, just the ID.

Remember:
- cinematic: Premium, professional, sophisticated brands
- dark_premium: Luxury, high-end, exclusive products
- minimal_studio: Clean, modern, tech, wellness brands
- lifestyle: Authentic, relatable, everyday use cases
- 2d_animated: Tech startups, SaaS, playful, modern

Choose wisely. Return ONLY the style ID."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=10,
            )
            
            chosen_style = response.choices[0].message.content.strip().lower()
            
            # Validate the chosen style
            valid_styles = ["cinematic", "dark_premium", "minimal_studio", "lifestyle", "2d_animated"]
            if chosen_style not in valid_styles:
                logger.warning(f"LLM returned invalid style '{chosen_style}', using 'cinematic' as default")
                chosen_style = "cinematic"
            
            logger.info(f"✅ LLM chose style: {chosen_style}")
            return chosen_style, "llm_inferred"
            
        except Exception as e:
            logger.error(f"Error in LLM style selection: {e}, using 'cinematic' as fallback")
            return "cinematic", "llm_inferred"

    async def _derive_tone_from_audience(
        self,
        target_audience: str,
        brand_description: Optional[str] = None,
    ) -> str:
        """
        Derive emotional tone from target audience using LLM.
        
        This tone influences:
        - Scene pacing and messaging
        - StyleSpec mood
        - Music mood selection
        
        Args:
            target_audience: Target audience description
            brand_description: Brand personality (optional)
            
        Returns:
            Tone descriptor (e.g., "warm and reassuring", "energetic and youthful")
        """
        prompt = f"""You are a brand strategist.

Target Audience: {target_audience}
{f'Brand Personality: {brand_description}' if brand_description else ''}

Based on the target audience, what emotional TONE should the video have?

Return ONLY a 2-4 word tone descriptor.

Examples:
- "mature skin consumers" → "warm and reassuring"
- "Gen Z tech enthusiasts" → "energetic and playful"
- "busy professionals" → "confident and efficient"
- "luxury shoppers" → "sophisticated and exclusive"
- "fitness enthusiasts" → "motivating and energetic"
- "parents with young children" → "caring and supportive"

Respond with ONLY the tone descriptor, nothing else."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=20,
            )
            
            tone = response.choices[0].message.content.strip().lower()
            logger.info(f"✅ Derived tone from audience '{target_audience}': {tone}")
            return tone
            
        except Exception as e:
            logger.warning(f"Failed to derive tone: {e}, using default")
            return "professional and engaging"

    async def _generate_style_spec(
        self,
        creative_prompt: str,
        brand_name: str,
        brand_description: Optional[str],
        brand_colors: List[str],
        brand_guidelines: Optional[str],
        derived_tone: Optional[str] = None,
    ) -> StyleSpec:
        """Generate global style specification using GPT-4o-mini."""

        # Build brand context
        brand_context = f"Brand: {brand_name}"
        if brand_description:
            brand_context += f"\nBrand Personality: {brand_description}"
        if brand_guidelines:
            guidelines_preview = brand_guidelines[:500] + ("..." if len(brand_guidelines) > 500 else "")
            brand_context += f"\nGuidelines: {guidelines_preview}"
        if derived_tone:
            brand_context += f"\nDerived Tone: {derived_tone}"

        prompt = f"""You are an expert cinematographer and color grader creating a consistent visual style.

=== CREATIVE VISION ===
{creative_prompt}

=== BRAND CONTEXT ===
{brand_context}
Brand Colors: {', '.join(brand_colors)}
{f"Target Emotional Tone: {derived_tone}" if derived_tone else ""}

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
            
            # Normalize field names - handle LLM variations
            normalized_dict = {
                'lighting_direction': style_dict.get('lighting_direction') or style_dict.get('lighting', ''),
                'camera_style': style_dict.get('camera_style', ''),
                'texture_materials': style_dict.get('texture_materials') or style_dict.get('texture', ''),
                'mood_atmosphere': style_dict.get('mood_atmosphere') or style_dict.get('mood', ''),
                'color_palette': style_dict.get('color_palette', []),
                'grade_postprocessing': style_dict.get('grade_postprocessing') or style_dict.get('grade', ''),
                'music_mood': style_dict.get('music_mood', 'uplifting'),
            }
            
            # Ensure all required fields have values
            if not normalized_dict['lighting_direction']:
                normalized_dict['lighting_direction'] = self._get_default_style_spec([])['lighting_direction']
            if not normalized_dict['texture_materials']:
                normalized_dict['texture_materials'] = self._get_default_style_spec([])['texture_materials']
            if not normalized_dict['mood_atmosphere']:
                normalized_dict['mood_atmosphere'] = self._get_default_style_spec([])['mood_atmosphere']

            return StyleSpec(**normalized_dict)

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
