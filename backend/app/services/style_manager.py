"""
Style management service for video aesthetic selection and application.
Manages 5 predefined styles and provides configuration for consistent styling.

Phase 7 Implementation
"""

from enum import Enum
from typing import Optional, Dict, Any, List


class VideoStyle(Enum):
    """Enumeration of available video styles."""
    CINEMATIC = "cinematic"
    DARK_PREMIUM = "dark_premium"
    MINIMAL_STUDIO = "minimal_studio"
    LIFESTYLE = "lifestyle"
    ANIMATED_2D = "2d_animated"


# Complete style configurations for all 5 styles
STYLE_CONFIGS = {
    VideoStyle.CINEMATIC: {
        'display_name': 'Cinematic',
        'description': (
            'High-quality camera feel, dramatic lighting, depth of '
            'field, modern ad look'
        ),
        'short_description': 'Professional, dramatic',
        'scene_keywords': (
            'cinematic camera work, dramatic lighting, shallow depth '
            'of field, professional color grading, modern premium '
            'aesthetic'
        ),
        'lighting': (
            'dramatic directional lighting with shadows, strategic '
            'highlights'
        ),
        'camera_style': (
            'cinematic camera movements, slow pans, subtle zooms, '
            'professional framing'
        ),
        'mood': 'sophisticated, premium, cinematic, dramatic',
        'color_palette': ['#2C1810', '#D4AF37', '#1A1A1A', '#C4B5A0'],
        'texture': 'cinema-grade cinematography, film-like quality',
        'grade': 'cinematic color grade, high contrast, warm tones',
        'examples': ['Nike', 'Apple', 'Samsung'],
        'keywords': ['professional', 'dramatic', 'premium'],
        'music_mood': 'dramatic',
        'best_for': [
            'Luxury brands',
            'Premium products',
            'High-end services'
        ]
    },

    VideoStyle.DARK_PREMIUM: {
        'display_name': 'Dark Premium',
        'description': (
            'Black background, rim lighting, contrast-heavy, product '
            'floating or rotating'
        ),
        'short_description': 'Luxury, exclusive',
        'scene_keywords': (
            'dark black background, rim lighting, high contrast, '
            'product isolated and floating, luxury aesthetic, '
            'product rotating on axis'
        ),
        'lighting': (
            'rim lighting on product edges, dark background, strategic '
            'accent lighting, backlight emphasis'
        ),
        'camera_style': (
            'static or slow product rotation, floating effect, '
            '360-degree showcase'
        ),
        'mood': 'luxurious, sophisticated, exclusive, premium, elegant',
        'color_palette': ['#000000', '#FF6B9D', '#C44569', '#F39C12'],
        'texture': (
            'smooth luxurious surfaces, glossy finish, metallic hints'
        ),
        'grade': 'high contrast, deep blacks, vibrant accents, moody',
        'examples': ['Sony', 'Nike', 'Luxury brands'],
        'keywords': ['luxury', 'dark', 'premium', 'exclusive'],
        'music_mood': 'luxurious',
        'best_for': [
            'Luxury goods',
            'High-end electronics',
            'Premium beauty'
        ]
    },

    VideoStyle.MINIMAL_STUDIO: {
        'display_name': 'Minimal Studio',
        'description': (
            'Minimal, bright, Apple-style aesthetic with clean '
            'compositions'
        ),
        'short_description': 'Clean, modern',
        'scene_keywords': (
            'minimalist studio style, clean bright background, simple '
            'composition, Apple aesthetic, premium simplicity, '
            'product-centric'
        ),
        'lighting': (
            'even soft lighting, bright clean environment, minimal '
            'shadows'
        ),
        'camera_style': (
            'static or subtle movements, product-centric, simple '
            'framing'
        ),
        'mood': 'clean, minimal, premium, modern, simple, refined',
        'color_palette': ['#FFFFFF', '#F5F5F5', '#333333', '#0071E3'],
        'texture': (
            'clean minimal surfaces, smooth finishes, professional'
        ),
        'grade': 'bright, clean, minimal color grading, neutral tones',
        'examples': ['Apple', 'Tech brands', 'Wellness', 'Ecommerce'],
        'keywords': ['minimal', 'clean', 'bright', 'simple'],
        'music_mood': 'calm',
        'best_for': [
            'Tech products',
            'SaaS',
            'Wellness brands',
            'Clean beauty'
        ]
    },

    VideoStyle.LIFESTYLE: {
        'display_name': 'Lifestyle',
        'description': (
            'Product used in everyday scenarios — running, cooking, '
            'working out, fashion'
        ),
        'short_description': 'Authentic, relatable',
        'scene_keywords': (
            'lifestyle photography, product in active use, everyday '
            'scenario, authentic moment, relatable context, real-world '
            'usage, genuine emotion'
        ),
        'lighting': 'natural or warm lighting, realistic, candid',
        'camera_style': (
            'documentary-style, natural movements, handheld feel, '
            'motion-focused'
        ),
        'mood': 'authentic, relatable, real-world, genuine, warm, human',
        'color_palette': ['#E8D4B8', '#C89968', '#556B2F', '#8B4513'],
        'texture': (
            'natural real-world textures, organic materials, authentic '
            'surfaces'
        ),
        'grade': (
            'warm, natural, authentic color grading, slightly '
            'desaturated'
        ),
        'examples': [
            'Social ads',
            'Relatable brands',
            'Lifestyle companies'
        ],
        'keywords': ['authentic', 'real-world', 'relatable', 'genuine'],
        'music_mood': 'uplifting',
        'best_for': [
            'Everyday products',
            'Sports brands',
            'Fashion',
            'Social media'
        ]
    },

    VideoStyle.ANIMATED_2D: {
        'display_name': '2D Animated',
        'description': (
            'Modern vector-style animation for explainers or '
            'playful ads'
        ),
        'short_description': 'Playful, modern',
        'scene_keywords': (
            '2D animation, vector style, motion graphics, modern '
            'animated explainer, playful transitions, illustrated '
            'style, dynamic movement'
        ),
        'lighting': (
            'stylized animated lighting, flat or gradient backgrounds'
        ),
        'camera_style': (
            'animated transitions, playful movements, parallax effects,'
            ' dynamic motion'
        ),
        'mood': 'playful, modern, innovative, fun, engaging, youthful',
        'color_palette': ['#FF6B9D', '#4ECDC4', '#FFE66D', '#95E1D3'],
        'texture': (
            'smooth vector illustration style, clean lines, graphic '
            'design'
        ),
        'grade': 'vibrant, saturated, stylized colors, bold',
        'examples': ['Fintech', 'SaaS', 'Apps', 'Startups'],
        'keywords': ['animated', 'playful', 'modern', 'fun'],
        'music_mood': 'playful',
        'best_for': [
            'Tech startups',
            'SaaS platforms',
            'Mobile apps',
            'Fintech'
        ]
    }
}


class StyleManager:
    """
    Manages video style configuration and application.

    Responsibilities:
    - Retrieve style configurations
    - Apply style guidance to prompts
    - Generate StyleSpec overrides for specific styles
    - Determine appropriate music mood for each style
    """

    @staticmethod
    def get_style_config(style: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Get complete configuration for a style.

        Args:
            style: Style name (e.g., 'cinematic', 'dark_premium')

        Returns:
            Dictionary with complete style configuration or None
        """
        if not style:
            return None

        try:
            style_enum = VideoStyle(style)
            return STYLE_CONFIGS.get(style_enum)
        except ValueError:
            # Invalid style name
            return None

    @staticmethod
    def apply_style_to_scene_prompt(
        scene_prompt: str,
        style: Optional[str]
    ) -> str:
        """
        Enhance scene prompt with style-specific keywords.

        Args:
            scene_prompt: Original scene description/prompt
            style: Style to apply

        Returns:
            Enhanced prompt with style keywords

        Example:
            "sunset beach" → "sunset beach with cinematic lighting..."
        """
        if not style:
            return scene_prompt

        config = StyleManager.get_style_config(style)
        if not config:
            return scene_prompt

        style_keywords = config.get('scene_keywords', '')
        return f"{scene_prompt}. Style guidance: {style_keywords}"

    @staticmethod
    def get_style_spec(style: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Generate StyleSpec overrides for a specific style.

        StyleSpec is used by VideoGenerator and other services to apply
        consistent style throughout video generation.

        Args:
            style: Style name

        Returns:
            StyleSpec dictionary with lighting, mood, colors, etc.
        """
        if not style:
            return None

        config = StyleManager.get_style_config(style)
        if not config:
            return None

        return {
            'lighting': config['lighting'],
            'camera_style': config['camera_style'],
            'mood': config['mood'],
            'color_palette': config['color_palette'],
            'texture': config['texture'],
            'grade': config['grade'],
            'music_mood': StyleManager._get_music_mood_for_style(style)
        }

    @staticmethod
    def _get_music_mood_for_style(style: str) -> str:
        """
        Get appropriate music mood for a style.

        Used by AudioEngine to select music that matches the
        visual style.

        Args:
            style: Style name

        Returns:
            Music mood string (e.g., 'dramatic', 'playful')
        """
        config = StyleManager.get_style_config(style)
        if config:
            return config.get('music_mood', 'uplifting')
        return 'uplifting'

    @staticmethod
    def get_all_styles() -> List[Dict[str, Any]]:
        """
        Get list of all available styles for UI display.

        Returns:
            List of style dictionaries with id, name, description, etc.
        """
        styles = []
        for style_enum in VideoStyle:
            config = STYLE_CONFIGS[style_enum]
            styles.append({
                'id': style_enum.value,
                'name': config['display_name'],
                'description': config['description'],
                'short_description': config['short_description'],
                'examples': config['examples'],
                'keywords': config['keywords'],
                'best_for': config['best_for']
            })
        return styles

    @staticmethod
    def validate_style(style: Optional[str]) -> bool:
        """
        Validate if a style string is valid.

        Args:
            style: Style to validate

        Returns:
            True if valid, False otherwise
        """
        if not style:
            return True  # None/empty is valid (means LLM decides)

        try:
            VideoStyle(style)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_style_display_name(style: str) -> str:
        """
        Get human-readable display name for a style.

        Args:
            style: Style name

        Returns:
            Display name (e.g., "Cinematic")
        """
        config = StyleManager.get_style_config(style)
        if config:
            return config.get('display_name', style)
        return style

    @staticmethod
    def synthesize_style_from_references(
        extracted_styles: List[Dict[str, Any]],
        brand_name: str = "",
        creative_prompt: str = ""
    ) -> str:
        """
        Synthesize a single style from multiple reference image styles.

        This function analyzes multiple extracted reference styles and
        determines which of the 5 predefined styles best matches the
        overall aesthetic.

        Strategy:
        1. Extract common themes from all reference images
        2. Score each of the 5 predefined styles against these themes
        3. Return the best-matching style

        Args:
            extracted_styles: List of extracted style dictionaries
            brand_name: Optional brand name for context
            creative_prompt: Optional creative prompt for context

        Returns:
            Single style string (e.g., "cinematic", "dark_premium")

        Example:
            extracted_styles = [
                {
                    "mood": "dark, premium",
                    "lighting": "dramatic",
                    "colors": ["#000", "#FFD700"]
                },
                {
                    "mood": "luxury, elegant",
                    "lighting": "rim lighting",
                    "colors": ["#000", "#C0C0C0"]
                }
            ]
            → Returns "dark_premium"
        """
        if not extracted_styles:
            return "cinematic"  # Default fallback

        # Single reference image - do direct mapping
        if len(extracted_styles) == 1:
            return StyleManager._map_extracted_to_predefined_style(
                extracted_styles[0]
            )

        # Multiple reference images - find common themes
        common_themes = StyleManager._extract_common_themes(
            extracted_styles
        )

        # Score each predefined style against common themes
        scores = {}
        for style_enum in VideoStyle:
            config = STYLE_CONFIGS[style_enum]
            score = StyleManager._score_style_match(
                config,
                common_themes
            )
            scores[style_enum.value] = score

        # Return highest scoring style
        best_style = max(scores, key=scores.get)

        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"🎨 Style synthesis from {len(extracted_styles)} "
            f"references:"
        )
        logger.info(f"   Common themes: {common_themes}")
        logger.info(f"   Scores: {scores}")
        logger.info(f"   Selected: {best_style}")

        return best_style

    @staticmethod
    def _extract_common_themes(
        extracted_styles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract common themes from multiple extracted styles.

        Analyzes mood, lighting, atmosphere, colors to find patterns.
        """
        all_moods = []
        all_lighting = []
        all_atmospheres = []
        all_colors = []

        for style in extracted_styles:
            if 'mood' in style:
                all_moods.append(style['mood'].lower())
            if 'lighting' in style:
                all_lighting.append(style['lighting'].lower())
            if 'atmosphere' in style:
                all_atmospheres.append(style['atmosphere'].lower())
            if 'colors' in style:
                all_colors.extend(style['colors'])

        # Find common keywords
        mood_keywords = StyleManager._extract_keywords_from_descriptions(
            all_moods
        )
        lighting_keywords = (
            StyleManager._extract_keywords_from_descriptions(
                all_lighting
            )
        )
        atmosphere_keywords = (
            StyleManager._extract_keywords_from_descriptions(
                all_atmospheres
            )
        )

        # Analyze color palette (dark vs light, saturated vs muted)
        color_analysis = StyleManager._analyze_color_palette(all_colors)

        return {
            'mood_keywords': mood_keywords,
            'lighting_keywords': lighting_keywords,
            'atmosphere_keywords': atmosphere_keywords,
            'color_analysis': color_analysis,
            'all_colors': all_colors[:8]
        }

    @staticmethod
    def _extract_keywords_from_descriptions(
        descriptions: List[str]
    ) -> List[str]:
        """Extract and count keywords from description strings."""
        keyword_counts = {}

        for desc in descriptions:
            # Split on common separators
            words = desc.replace(',', ' ').replace(';', ' ').split()
            for word in words:
                word = word.strip().lower()
                if len(word) > 2:  # Skip very short words
                    keyword_counts[word] = keyword_counts.get(word, 0) + 1

        # Return keywords that appear in multiple references
        threshold = max(1, len(descriptions) // 2)
        common = [
            k for k, v in keyword_counts.items() if v >= threshold
        ]

        return common

    @staticmethod
    def _analyze_color_palette(colors: List[str]) -> Dict[str, Any]:
        """
        Analyze a color palette to determine characteristics.

        Returns:
            Dict with is_dark, is_saturated, is_warm, etc.
        """
        if not colors:
            return {
                'is_dark': False,
                'is_saturated': False,
                'is_warm': True
            }

        def hex_to_brightness(hex_color: str) -> float:
            """Calculate perceived brightness (0-1)."""
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                # Perceived brightness formula
                return (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return 0.5

        def hex_to_saturation(hex_color: str) -> float:
            """Calculate saturation (0-1)."""
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                max_val = max(r, g, b)
                min_val = min(r, g, b)
                if max_val == 0:
                    return 0
                return (max_val - min_val) / max_val
            return 0.5

        def hex_to_warmth(hex_color: str) -> float:
            """Calculate warmth (red/yellow vs blue/green)."""
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                b = int(hex_color[4:6], 16)
                # Warm if red > blue
                return (r - b + 255) / 510  # Normalize to 0-1
            return 0.5

        brightnesses = [hex_to_brightness(c) for c in colors]
        saturations = [hex_to_saturation(c) for c in colors]
        warmths = [hex_to_warmth(c) for c in colors]

        avg_brightness = sum(brightnesses) / len(brightnesses)
        avg_saturation = sum(saturations) / len(saturations)
        avg_warmth = sum(warmths) / len(warmths)

        return {
            'is_dark': avg_brightness < 0.3,
            'is_bright': avg_brightness > 0.7,
            'is_saturated': avg_saturation > 0.5,
            'is_warm': avg_warmth > 0.55,
            'avg_brightness': avg_brightness,
            'avg_saturation': avg_saturation,
            'avg_warmth': avg_warmth
        }

    @staticmethod
    def _score_style_match(
        style_config: Dict[str, Any],
        themes: Dict[str, Any]
    ) -> float:
        """
        Score how well a predefined style matches extracted themes.

        Returns score from 0-100.
        """
        score = 0.0

        # Check mood keywords (30 points)
        mood_keywords = themes.get('mood_keywords', [])
        style_keywords = [
            k.lower() for k in style_config.get('keywords', [])
        ]
        mood_match = sum(
            1 for kw in mood_keywords
            if any(sk in kw or kw in sk for sk in style_keywords)
        )
        score += min(30, mood_match * 10)

        # Check lighting keywords (20 points)
        lighting_keywords = themes.get('lighting_keywords', [])
        style_lighting = style_config.get('lighting', '').lower()
        lighting_match = sum(
            1 for kw in lighting_keywords if kw in style_lighting
        )
        score += min(20, lighting_match * 7)

        # Check atmosphere keywords (20 points)
        atmosphere_keywords = themes.get('atmosphere_keywords', [])
        style_mood = style_config.get('mood', '').lower()
        atmosphere_match = sum(
            1 for kw in atmosphere_keywords if kw in style_mood
        )
        score += min(20, atmosphere_match * 7)

        # Check color analysis (30 points)
        color_analysis = themes.get('color_analysis', {})

        # Dark Premium: dark colors, high contrast
        if style_config.get('display_name') == 'Dark Premium':
            if color_analysis.get('is_dark'):
                score += 20
            if color_analysis.get('is_saturated'):
                score += 10

        # Minimal Studio: bright, clean
        elif style_config.get('display_name') == 'Minimal Studio':
            if color_analysis.get('is_bright'):
                score += 20
            if not color_analysis.get('is_saturated'):
                score += 10

        # Lifestyle: natural, warm
        elif style_config.get('display_name') == 'Lifestyle':
            if color_analysis.get('is_warm'):
                score += 15
            brightness = color_analysis.get('avg_brightness', 0.5)
            if 0.3 <= brightness <= 0.7:
                score += 15  # Mid-range brightness

        # 2D Animated: saturated, colorful
        elif style_config.get('display_name') == '2D Animated':
            if color_analysis.get('is_saturated'):
                score += 20
            if color_analysis.get('is_bright'):
                score += 10

        # Cinematic: balanced (default gets bonus if nothing matches)
        elif style_config.get('display_name') == 'Cinematic':
            score += 10  # Small baseline bonus

        return score

    @staticmethod
    def _map_extracted_to_predefined_style(
        extracted_style: Dict[str, Any]
    ) -> str:
        """
        Map a single extracted style to one of 5 predefined styles.

        Uses keyword matching and color analysis.
        """
        # Use the same scoring mechanism as synthesis
        themes = {
            'mood_keywords': extracted_style.get('mood', '').lower(
            ).split(),
            'lighting_keywords': extracted_style.get(
                'lighting',
                ''
            ).lower().split(),
            'atmosphere_keywords': extracted_style.get(
                'atmosphere',
                ''
            ).lower().split(),
            'color_analysis': StyleManager._analyze_color_palette(
                extracted_style.get('colors', [])
            ),
            'all_colors': extracted_style.get('colors', [])
        }

        scores = {}
        for style_enum in VideoStyle:
            config = STYLE_CONFIGS[style_enum]
            score = StyleManager._score_style_match(config, themes)
            scores[style_enum.value] = score

        return max(scores, key=scores.get)
