"""Scene Planner Service - LLM-based scene generation with perfume shot grammar constraints.

This service takes a creative prompt and brand information, then uses GPT-4o-mini
to generate a structured scene plan for LUXURY PERFUME videos with strict shot grammar constraints.

Key Features:
- CONSTRAINED scene generation (only allowed perfume shot types)
- Scene count based on duration (3-5 scenes for 15-60s videos)
- Perfume-specific visual language (macro bottles, luxury B-roll, atmospheric)
- 3-retry system with fallback to predefined templates
- TikTok vertical optimization (9:16 only)
- Style consistency enforcement across all scenes
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.services.style_manager import StyleManager
from app.services.perfume_grammar_loader import PerfumeGrammarLoader

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
    """Plans LUXURY PERFUME video scenes using LLM with shot grammar constraints."""

    def __init__(self, api_key: str):
        """Initialize with OpenAI API key and perfume grammar constraints."""
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-5.1"
        self.grammar_loader = PerfumeGrammarLoader()
        logger.info("✅ ScenePlanner initialized with perfume shot grammar constraints")

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
        selected_style: Optional[str] = None,
        extracted_style: Optional[Dict[str, Any]] = None,
        perfume_name: Optional[str] = None,
        perfume_gender: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate TikTok vertical video scene plan with perfume grammar constraints.

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
            selected_style: (PHASE 7) User-selected or LLM-inferred style name or None
            extracted_style: Optional extracted style from reference image
            perfume_name: Perfume product name (e.g., "Noir Élégance")
            perfume_gender: Perfume gender ('masculine', 'feminine', or 'unisex')

        Returns:
            Dictionary with scenes, style_spec, chosenStyle, styleSource
        """
        # Use perfume_name if provided, otherwise fallback to brand_name
        actual_perfume_name = perfume_name or brand_name
        logger.info(f"Planning video for '{brand_name}' / Perfume: '{actual_perfume_name}' (target: {target_duration}s)")
        logger.info(f"Assets available - Product: {has_product}, Logo: {has_logo}")
        if perfume_gender:
            logger.info(f"Perfume gender: {perfume_gender}")
        
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

        # STEP 3: Generate scene plan via LLM with PERFUME GRAMMAR CONSTRAINTS
        scenes_json = await self._generate_perfume_scenes_with_grammar(
            creative_prompt=creative_prompt,
            brand_name=brand_name,
            perfume_name=actual_perfume_name,
            brand_description=brand_description,
            brand_colors=brand_colors,
            brand_guidelines=brand_guidelines,
            target_audience=target_audience or "general consumers",
            target_duration=target_duration,
            chosen_style=chosen_style,
            perfume_gender=perfume_gender,
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
        # CRITICAL: Preserve shot_type and shot_variation from original scene_dict
        scenes_dict = []
        for i, scene in enumerate(scenes):
            scene_data = scene.model_dump()
            scene_data['style'] = chosen_style  # Force same style on all scenes
            
            # CRITICAL: Preserve perfume grammar fields from original scene_dict
            original_dict = scenes_json[i]
            if 'shot_type' in original_dict:
                scene_data['shot_type'] = original_dict['shot_type']
            if 'shot_variation' in original_dict:
                scene_data['shot_variation'] = original_dict['shot_variation']
            
            scenes_dict.append(scene_data)
        
        # Validate: all scenes have same style
        for i, scene_data in enumerate(scenes_dict):
            if scene_data.get('style') != chosen_style:
                logger.warning(f"Scene {i} tried different style: {scene_data.get('style')} → forcing {chosen_style}")
                scene_data['style'] = chosen_style
        
        assert all(s.get('style') == chosen_style for s in scenes_dict), \
            f"Style consistency violated! All scenes must use {chosen_style}"
        
        logger.info(f"✅ Generated plan with {len(scenes)} scenes (total: {total_duration}s, style: {chosen_style})")
        
        # LOG: Show final scene scripts after all processing
        logger.info(f"📝 Final scene scripts:")
        for i, scene_data in enumerate(scenes_dict):
            background_prompt = scene_data.get('background_prompt', 'MISSING')
            logger.info(f"   Scene {i+1} script: {background_prompt}")

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
        chosen_style: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate scene specifications using GPT-4o-mini (legacy method - not used for perfume)."""

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

By default, avoid generic "people enjoying the product" shots and cliché stock-style scenes.
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
Video Aspect Ratio: 9:16 (TikTok vertical - hardcoded)

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

    async def _generate_perfume_scenes_with_grammar(
        self,
        creative_prompt: str,
        brand_name: str,
        perfume_name: str,
        brand_description: Optional[str],
        brand_colors: List[str],
        brand_guidelines: Optional[str],
        target_audience: str,
        target_duration: int,
        chosen_style: str,
        perfume_gender: Optional[str] = None,
        retry_count: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Generate PERFUME SCENE PLAN using STRICT SHOT GRAMMAR CONSTRAINTS.
        
        This method constrains LLM to ONLY generate scenes using allowed perfume shot types.
        If LLM violates grammar, retry up to 3 times. After 3 failures, use predefined template.
        
        Args:
            creative_prompt: User's creative vision
            brand_name: Brand name
            perfume_name: Perfume product name
            brand_description: Brand story
            brand_colors: Brand colors
            brand_guidelines: Brand guidelines
            target_audience: Target audience
            target_duration: Target duration
            chosen_style: Perfume style (gold_luxe, dark_elegance, romantic_floral)
            perfume_gender: Perfume gender ('masculine', 'feminine', or 'unisex')
            retry_count: Current retry attempt (0-3)
            
        Returns:
            List of scene dictionaries conforming to perfume grammar
        """
        
        # Get grammar constraints
        shot_types = self.grammar_loader.get_allowed_shot_types()
        scene_count = self.grammar_loader.get_scene_count_for_duration(target_duration)
        flow_rules = self.grammar_loader.get_flow_rules()
        
        # Get allowed shot type IDs (for validation)
        allowed_shot_ids = self.grammar_loader.get_shot_type_ids()
        
        logger.info(f"🎬 Generating perfume scenes (attempt {retry_count + 1}/3)")
        logger.info(f"   Shot count: {scene_count}, Duration: {target_duration}s, Style: {chosen_style}")
        
        # Build shot type descriptions for LLM
        # CRITICAL: Use the 'id' field from config, NOT the dictionary key
        shot_descriptions = []
        allowed_ids = []  # Track allowed IDs for validation
        for type_key, config in shot_types.items():
            shot_id = config.get("id")  # Get the actual ID (e.g., "macro_bottle")
            allowed_ids.append(shot_id)
            variations = ", ".join(config["variations"][:3]) + ", ..."  # Show first 3
            shot_descriptions.append(
                f"**{config['display_name']} (shot_type ID: '{shot_id}')**\n"
                f"  {config['description']}\n"
                f"  Duration: {config['duration_range'][0]}-{config['duration_range'][1]}s\n"
                f"  Variations: {variations}\n"
                f"  ⚠️ YOU MUST USE THIS EXACT ID: '{shot_id}' (NOT '{type_key}')"
            )
        
        # Build gender-specific visual language guidance
        gender_guidance = ""
        if perfume_gender:
            if perfume_gender == "masculine":
                gender_guidance = """
🎯 GENDER-SPECIFIC VISUAL LANGUAGE (MASCULINE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is a MASCULINE perfume. Apply these visual characteristics:
- **Colors**: Darker tones (deep blacks, charcoal, navy, burgundy), bold contrasts
- **Lighting**: Stronger, more dramatic lighting with deeper shadows
- **Mood**: Confident, powerful, sophisticated, bold
- **Textures**: Rugged materials, leather, metal accents, strong geometric shapes
- **Camera**: More dynamic movements, stronger angles, bolder compositions
- **Atmosphere**: Premium, commanding, assertive, refined strength
"""
            elif perfume_gender == "feminine":
                gender_guidance = """
🎯 GENDER-SPECIFIC VISUAL LANGUAGE (FEMININE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is a FEMININE perfume. Apply these visual characteristics:
- **Colors**: Softer tones (rose gold, blush, lavender, soft pastels), elegant gradients
- **Lighting**: Softer, more diffused lighting with gentle highlights
- **Mood**: Elegant, graceful, delicate, refined, romantic
- **Textures**: Silk, satin, flowers, soft fabrics, flowing movements
- **Camera**: More gentle movements, softer angles, elegant compositions
- **Atmosphere**: Luxurious, graceful, sophisticated elegance, refined beauty
"""
            elif perfume_gender == "unisex":
                gender_guidance = """
🎯 GENDER-SPECIFIC VISUAL LANGUAGE (UNISEX)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is a UNISEX perfume. Apply these visual characteristics:
- **Colors**: Balanced palette (neutral tones, sophisticated grays, balanced warm/cool)
- **Lighting**: Balanced lighting, neither too harsh nor too soft
- **Mood**: Modern, sophisticated, versatile, inclusive, contemporary
- **Textures**: Clean modern materials, minimalist surfaces, balanced compositions
- **Camera**: Balanced movements, neutral angles, modern compositions
- **Atmosphere**: Contemporary luxury, inclusive elegance, modern sophistication
"""
        
        # Build perfume-specific prompt with STRICT grammar
        prompt = f"""You are a LUXURY PERFUME COMMERCIAL DIRECTOR creating a TikTok vertical video (9:16).

🎯 PERFUME INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand: {brand_name}
Perfume Name: {perfume_name}
Brand Description: {brand_description or 'Luxury perfume brand'}
Target Audience: {target_audience}
{f"Brand Guidelines: {brand_guidelines[:300]}" if brand_guidelines else ""}
{gender_guidance}

🎨 CREATIVE VISION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{creative_prompt}

🎬 PLATFORM & STYLE CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Platform: TikTok Vertical (9:16, 1080×1920)
Video Style: {chosen_style}
Duration: ~{target_duration}s
Scene Count: EXACTLY {scene_count} scenes
Aspect Ratio: Always 9:16 (portrait mode only)
{f"Gender: {perfume_gender.upper()}" if perfume_gender else ""}

🔒 CRITICAL - PERFUME SHOT GRAMMAR (YOU MUST FOLLOW EXACTLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST use ONLY these allowed shot types. DO NOT invent new types.

{chr(10).join(shot_descriptions)}

📋 MANDATORY RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Generate EXACTLY {scene_count} scenes (no more, no less)
2. FIRST scene must be: {flow_rules.get('first_scene_must_be', ['macro_bottle', 'atmospheric'])} shot type
3. LAST scene must be: {flow_rules.get('last_scene_must_be', ['brand_moment'])} shot type
4. Product must appear in {flow_rules['product_visibility_rules']['minimum_product_scenes']}-{flow_rules['product_visibility_rules']['maximum_product_scenes']} scenes
5. Total duration should be ±{int(target_duration * 0.15)}s from {target_duration}s
6. ALL scenes must use ONLY transitions: {', '.join(flow_rules.get('transition_rules', {}).get('allowed_transitions', ['fade', 'cut']))}
7. FINAL scene MUST include text with perfume name "{perfume_name}" + brand name "{brand_name}"
8. ALL scenes must match style: {chosen_style}
9. **CRITICAL**: Use the PERFUME NAME "{perfume_name}" (not brand name) in scene descriptions and text overlays when referring to the product
10. **CRITICAL**: Apply gender-specific visual language ({perfume_gender.upper() if perfume_gender else 'UNISEX'}) to all scene descriptions - colors, lighting, mood, textures, camera movements, and atmosphere must reflect the gender aesthetic

✅ PERFUME SHOT TYPE REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each scene MUST have:
- shot_type: (MUST be one of the allowed IDs above)
- shot_variation: (MUST be from the allowed variations for that type)
- role: (hook, showcase, cta, etc.)
- duration: (within allowed range)
- background_prompt: (detailed visual description using {chosen_style} aesthetic)
- use_product: (true/false based on shot type)
- camera_movement: (from allowed movements)
- transition_to_next: (fade or cut only)

⚠️ CRITICAL VALIDATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ EVERY shot_type MUST be EXACTLY one of these IDs: {', '.join(allowed_ids)}
✓ DO NOT use dictionary keys like 'macro_bottle_shots' - use the ID 'macro_bottle' instead
✓ EVERY shot_variation must be in the allowed list for that type
✓ NO shot types that are not in the allowed list above
✓ NO "generic" or invented shot types
✓ Product positioning: ONLY in macro_bottle, human_silhouette, brand_moment
✓ NO multi-product scenes (perfume bottles only)
✓ NO conflicting rules (follow grammar EXACTLY)

🚨 EXACT SHOT TYPE IDs YOU MUST USE:
{', '.join([f"'{id}'" for id in allowed_ids])}

DO NOT USE THESE (they are wrong):
- 'macro_bottle_shots' → USE 'macro_bottle'
- 'luxury_aesthetic_broll' → USE 'aesthetic_broll'
- 'atmospheric_scenes' → USE 'atmospheric'
- 'final_brand_moment' → USE 'brand_moment'

📄 OUTPUT FORMAT (STRICT JSON)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON array with {scene_count} scene objects:

[
  {{
    "scene_id": 0,
    "shot_type": "macro_bottle",
    "shot_variation": "extreme_closeup_cap",
    "role": "hook",
    "duration": 6,
    "background_prompt": "Extreme close-up of perfume bottle cap with engraved logo, soft golden rim lighting, black background, premium commercial aesthetic",
    "use_product": true,
    "product_position": "center",
    "product_scale": 0.6,
    "camera_movement": "slow_zoom_in",
    "transition_to_next": "fade",
    "overlay": {{
      "text": "{perfume_name}",
      "position": "bottom",
      "duration": 2.0,
      "font_size": 48,
      "color": "{brand_colors[0] if brand_colors else '#FFFFFF'}",
      "animation": "fade_in"
    }}
  }},
  ...
]

⚠️ DO NOT DEVIATE FROM GRAMMAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ DO NOT use shot types not in the list
❌ DO NOT use variations not in the shot type
❌ DO NOT ignore scene count requirement
❌ DO NOT mix styles or aesthetics
❌ DO NOT create more than {scene_count} scenes
❌ DO NOT create fewer than {scene_count} scenes

✅ FOLLOW GRAMMAR RULES EXACTLY AND GENERATE NOW"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.5,  # Lower temperature for stricter grammar compliance
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a luxury perfume commercial director. You MUST follow perfume shot grammar constraints EXACTLY.

CRITICAL RULES:
1. Use ONLY these exact shot_type IDs: {', '.join(allowed_ids)}
2. DO NOT use dictionary keys like 'macro_bottle_shots' - use 'macro_bottle' instead
3. DO NOT invent new shot types
4. Every scene MUST have a shot_type field with one of the exact IDs above
5. Output only valid JSON arrays

Example CORRECT shot_type: "macro_bottle"
Example WRONG shot_type: "macro_bottle_shots" (this is a dictionary key, not the ID)

Follow the grammar rules EXACTLY."""
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content
            
            # Try to parse JSON
            try:
                scenes = json.loads(response_text)
            except json.JSONDecodeError:
                # Try extracting from code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    scenes = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                    scenes = json.loads(json_str)
                else:
                    raise ValueError("Could not extract JSON from response")
            
            # LOG: Show scene scripts (background_prompt) generated by LLM
            logger.info(f"📝 LLM generated {len(scenes)} scene scripts:")
            for i, scene in enumerate(scenes):
                background_prompt = scene.get('background_prompt', 'MISSING')
                logger.info(f"   Scene {i+1} script: {background_prompt}")
            
            # VALIDATE AGAINST GRAMMAR
            is_valid, violations = self.grammar_loader.validate_scene_plan(scenes)
            
            if not is_valid:
                if retry_count < 2:
                    # Retry with more explicit prompt
                    logger.info(f"Retrying with more explicit grammar instructions...")
                    return await self._generate_perfume_scenes_with_grammar(
                        creative_prompt=creative_prompt,
                        brand_name=brand_name,
                        perfume_name=perfume_name,
                        brand_description=brand_description,
                        brand_colors=brand_colors,
                        brand_guidelines=brand_guidelines,
                        target_audience=target_audience,
                        target_duration=target_duration,
                        chosen_style=chosen_style,
                        perfume_gender=perfume_gender,
                        retry_count=retry_count + 1,
                    )
                else:
                    # 3 retries failed - use predefined template
                    logger.error(f"❌ Grammar violations after 3 retries. Using fallback template.")
                    fallback_scenes = self._get_fallback_template(scene_count, target_duration, chosen_style, perfume_name, brand_name, brand_colors)
                    logger.info(f"📝 Fallback template scene scripts:")
                    for i, scene in enumerate(fallback_scenes):
                        logger.info(f"   Scene {i+1} script: {scene.get('background_prompt', 'MISSING')}")
                    return fallback_scenes
            
            # Validate scene count
            if len(scenes) != scene_count:
                logger.warning(f"Scene count mismatch: expected {scene_count}, got {len(scenes)}")
                if retry_count < 2:
                    logger.info(f"Retrying to get exact scene count...")
                    return await self._generate_perfume_scenes_with_grammar(
                        creative_prompt=creative_prompt,
                        brand_name=brand_name,
                        perfume_name=perfume_name,
                        brand_description=brand_description,
                        brand_colors=brand_colors,
                        brand_guidelines=brand_guidelines,
                        target_audience=target_audience,
                        target_duration=target_duration,
                        chosen_style=chosen_style,
                        perfume_gender=perfume_gender,
                        retry_count=retry_count + 1,
                    )
                else:
                    logger.error(f"Fallback to template due to scene count mismatch")
                    return self._get_fallback_template(scene_count, target_duration, chosen_style, perfume_name, brand_name, brand_colors)
            
            logger.info(f"✅ Generated {len(scenes)} perfume scenes (grammar validated)")
            return scenes
            
        except Exception as e:
            logger.error(f"Error generating perfume scenes: {e}")
            if retry_count < 2:
                logger.info(f"Retrying due to error...")
                return await self._generate_perfume_scenes_with_grammar(
                    creative_prompt=creative_prompt,
                    brand_name=brand_name,
                    perfume_name=perfume_name,
                    brand_description=brand_description,
                    brand_colors=brand_colors,
                    brand_guidelines=brand_guidelines,
                    target_audience=target_audience,
                    target_duration=target_duration,
                    chosen_style=chosen_style,
                    perfume_gender=perfume_gender,
                    retry_count=retry_count + 1,
                )
            else:
                logger.error(f"Fallback to template due to LLM error")
                return self._get_fallback_template(scene_count, target_duration, chosen_style, perfume_name, brand_name, brand_colors)

    def _get_fallback_template(
        self,
        scene_count: int,
        target_duration: int,
        style: str,
        perfume_name: str,
        brand_name: str,
        brand_colors: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Return predefined scene template as fallback when LLM fails grammar validation.
        
        Template structure is perfume-appropriate and follows shot grammar rules.
        """
        logger.info(f"🎬 Using fallback template: {scene_count} scenes, {style} style")
        
        color = brand_colors[0] if brand_colors else "#FFFFFF"
        
        # Template for 3 scenes (15-30s)
        if scene_count <= 3:
            return [
                {
                    "scene_id": 0,
                    "shot_type": "macro_bottle",
                    "shot_variation": "extreme_closeup_cap",
                    "role": "hook",
                    "duration": max(3, min(8, target_duration // 3)),
                    "background_prompt": f"Extreme close-up of luxury perfume bottle, elegant lighting, {style} aesthetic, premium cinematic commercial",
                    "use_product": True,
                    "product_position": "center",
                    "product_scale": 0.6,
                    "camera_movement": "slow_zoom_in",
                    "transition_to_next": "fade",
                    "overlay": {
                        "text": perfume_name,
                        "position": "bottom",
                        "duration": 2.0,
                        "font_size": 48,
                        "color": color,
                        "animation": "fade_in"
                    }
                },
                {
                    "scene_id": 1,
                    "shot_type": "aesthetic_broll",
                    "shot_variation": "silk_fabric_flowing",
                    "role": "showcase",
                    "duration": max(3, min(8, target_duration // 3)),
                    "background_prompt": f"Luxurious silk and textures, {style} lighting and mood, premium aesthetic",
                    "use_product": False,
                    "camera_movement": "slow_zoom_in",
                    "transition_to_next": "fade",
                    "overlay": {"text": "", "position": "bottom", "duration": 0, "font_size": 48, "color": color, "animation": "fade_in"}
                },
                {
                    "scene_id": 2,
                    "shot_type": "brand_moment",
                    "shot_variation": "product_centered_minimal",
                    "role": "cta",
                    "duration": max(3, min(8, target_duration // 3 + 2)),
                    "background_prompt": f"Clean minimalist studio, perfume bottle centered, {style} aesthetic, premium final moment",
                    "use_product": True,
                    "product_position": "center",
                    "product_scale": 0.5,
                    "camera_movement": "slow_zoom_out",
                    "transition_to_next": "fade",
                    "overlay": {
                        "text": f"{perfume_name}\n{brand_name}",
                        "position": "bottom",
                        "duration": 3.0,
                        "font_size": 48,
                        "color": color,
                        "animation": "fade_in"
                    }
                }
            ]
        
        # Template for 4-5 scenes (30-60s)
        else:
            return [
                {
                    "scene_id": 0,
                    "shot_type": "macro_bottle",
                    "shot_variation": "spray_mist_macro",
                    "role": "hook",
                    "duration": 5,
                    "background_prompt": f"Perfume spray mist in macro, golden particles, {style} lighting, cinematic premium",
                    "use_product": True,
                    "product_position": "center",
                    "product_scale": 0.5,
                    "camera_movement": "static",
                    "transition_to_next": "fade",
                    "overlay": {
                        "text": perfume_name,
                        "position": "bottom",
                        "duration": 2.0,
                        "font_size": 48,
                        "color": color,
                        "animation": "fade_in"
                    }
                },
                {
                    "scene_id": 1,
                    "shot_type": "aesthetic_broll",
                    "shot_variation": "rose_petals_falling",
                    "role": "build",
                    "duration": 6,
                    "background_prompt": f"Rose petals in luxury motion, soft lighting, {style} mood",
                    "use_product": False,
                    "camera_movement": "slow_pan_right",
                    "transition_to_next": "fade",
                    "overlay": {"text": "", "position": "bottom", "duration": 0, "font_size": 48, "color": color, "animation": "fade_in"}
                },
                {
                    "scene_id": 2,
                    "shot_type": "atmospheric",  # Use ID, not dictionary key
                    "shot_variation": "light_rays_through_window",
                    "role": "showcase",
                    "duration": 6,
                    "background_prompt": f"Light rays through premium materials, {style} aesthetic",
                    "use_product": False,
                    "camera_movement": "slow_zoom_in",
                    "transition_to_next": "fade",
                    "overlay": {"text": "", "position": "bottom", "duration": 0, "font_size": 48, "color": color, "animation": "fade_in"}
                },
                {
                    "scene_id": 3,
                    "shot_type": "brand_moment",
                    "shot_variation": "bottle_with_tagline",
                    "role": "cta",
                    "duration": 7,
                    "background_prompt": f"Perfume bottle hero shot with elegant background, {style} premium aesthetic",
                    "use_product": True,
                    "product_position": "center",
                    "product_scale": 0.5,
                    "camera_movement": "slow_zoom_out",
                    "transition_to_next": "fade",
                    "overlay": {
                        "text": f"{perfume_name}\n{brand_name}",
                        "position": "bottom",
                        "duration": 3.0,
                        "font_size": 48,
                        "color": color,
                        "animation": "fade_in"
                    }
                }
            ]

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

    async def _generate_scene_variations(
        self,
        num_variations: int,
        creative_prompt: str,
        brand_name: str,
        brand_description: Optional[str],
        brand_colors: List[str],
        brand_guidelines: Optional[str],
        target_audience: Optional[str],
        target_duration: int,
        has_product: bool,
        has_logo: bool,
        selected_style: Optional[str],
        extracted_style: Optional[Dict[str, Any]],
        perfume_name: Optional[str] = None,
        perfume_gender: Optional[str] = None,
    ) -> List[List[Dict[str, Any]]]:
        """
        Generate N variations of scene plans with different visual approaches.
        
        Each variation uses a different approach:
        - Variation 0: Cinematic + dramatic lighting + wide shots
        - Variation 1: Minimal + clean + close-up macro
        - Variation 2: Lifestyle + real-world + atmospheric
        
        Args:
            num_variations: Number of variations to generate (1-3)
            creative_prompt: User's creative vision
            brand_name: Brand name
            brand_description: Brand description
            brand_colors: Brand colors
            brand_guidelines: Brand guidelines
            target_audience: Target audience
            target_duration: Target duration
            has_product: Whether product image is available
            has_logo: Whether logo is available
            selected_style: Selected style name
            extracted_style: Optional extracted style from reference image
            perfume_name: Perfume product name
            perfume_gender: Perfume gender
            
        Returns:
            List of scene plan lists: [[scenes_v1], [scenes_v2], [scenes_v3]]
        """
        logger.info(f"Generating {num_variations} scene plan variations...")
        
        variation_scenes = []
        
        for var_idx in range(num_variations):
            logger.info(f"Generating variation {var_idx + 1}/{num_variations}...")
            
            # Build variation-specific prompt
            variation_prompt = self._build_variation_prompt(
                variation_index=var_idx,
                total_variations=num_variations,
                creative_prompt=creative_prompt,
                brand_guidelines=brand_guidelines,
                selected_style=selected_style,
            )
            
            # Generate scenes for this variation using existing method
            scenes_json = await self._generate_perfume_scenes_with_grammar(
                creative_prompt=variation_prompt,
                brand_name=brand_name,
                perfume_name=perfume_name or brand_name,
                brand_description=brand_description,
                brand_colors=brand_colors,
                brand_guidelines=brand_guidelines,
                target_audience=target_audience or "general consumers",
                target_duration=target_duration,
                chosen_style=selected_style or "cinematic",
                perfume_gender=perfume_gender,
            )
            
            variation_scenes.append(scenes_json)
            logger.info(f"Variation {var_idx + 1} complete: {len(scenes_json)} scenes")
        
        logger.info(f"Generated {len(variation_scenes)} scene plan variations")
        return variation_scenes

    def _build_variation_prompt(
        self,
        variation_index: int,
        total_variations: int,
        creative_prompt: str,
        brand_guidelines: Optional[str],
        selected_style: Optional[str],
    ) -> str:
        """
        Build a variation-specific prompt with different visual approach.
        
        Args:
            variation_index: Index of this variation (0-based)
            total_variations: Total number of variations
            creative_prompt: Original creative prompt
            brand_guidelines: Brand guidelines text
            selected_style: Selected style name
            
        Returns:
            Enhanced prompt with variation-specific instructions
        """
        # Define variation approaches
        variation_approaches = [
            "Cinematic approach: Use dramatic lighting with high contrast, wide establishing shots, epic scale, cinematic color grading, and dynamic camera movements. Focus on grandeur and visual impact.",
            "Minimal approach: Use clean, soft diffused lighting, close-up macro shots, minimalist composition, subtle textures, and refined simplicity. Focus on product details and elegance.",
            "Lifestyle approach: Use warm atmospheric lighting, real-world settings, natural environments, relatable scenarios, and authentic moments. Focus on emotional connection and everyday luxury.",
        ]
        
        # Get approach for this variation
        approach = variation_approaches[variation_index % len(variation_approaches)]
        
        # Build enhanced prompt
        enhanced_prompt = f"""{creative_prompt}

VARIATION {variation_index + 1} OF {total_variations}:
{approach}

Brand Guidelines: {brand_guidelines or 'Maintain brand consistency'}
Style: {selected_style or 'cinematic'}

IMPORTANT: Generate scenes with a DIFFERENT visual approach than other variations,
but maintain the SAME brand message and product positioning.
"""
        
        return enhanced_prompt
