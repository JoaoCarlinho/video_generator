"""
Style management service for luxury perfume video aesthetic selection and application.
Manages 3 predefined perfume-specific styles and provides configuration for consistent styling.

Phase 4 Implementation - Perfume Style Refactor
"""

from enum import Enum
from typing import Optional, Dict, Any, List


class VideoStyle(Enum):
    """Perfume video styles (3 user-selectable options)."""
    GOLD_LUXE = "gold_luxe"
    DARK_ELEGANCE = "dark_elegance"
    ROMANTIC_FLORAL = "romantic_floral"


# Complete style configurations for all 3 perfume styles
STYLE_CONFIGS = {
    VideoStyle.GOLD_LUXE: {
        'display_name': 'Gold Luxe',
        'description': 'Warm golden lighting, rich textures, opulent feel',
        'short_description': 'Luxurious, warm',
        'scene_keywords': 'golden hour lighting, warm champagne tones, luxury gold accents, soft glow, premium aesthetic',
        'lighting': 'warm golden rim lighting, soft glow, backlit elegance',
        'camera_style': 'slow zoom, cinematic movements, macro details',
        'mood': 'luxurious, warm, sophisticated, opulent',
        'color_palette': ['#D4AF37', '#8B4513', '#FFD700', '#FFF8DC'],
        'texture': 'gold leaf, silk, smooth glass, rich textures',
        'grade': 'warm golden grade, lifted midtones, subtle vignette',
        'examples': ['Chanel', 'Dior', 'Tom Ford'],
        'keywords': ['luxury', 'gold', 'warm', 'opulent'],
        'music_mood': 'luxurious',
        'best_for': ['High-end perfumes', 'Premium fragrances', 'Luxury brands'],
        'priority_weight': 1.0  # User selection weight
    },
    
    VideoStyle.DARK_ELEGANCE: {
        'display_name': 'Dark Elegance',
        'description': 'Black background, dramatic rim lighting, mysterious',
        'short_description': 'Mysterious, sophisticated',
        'scene_keywords': 'dark black background, rim lighting, high contrast, dramatic shadows, mysterious elegance',
        'lighting': 'rim lighting on bottle edges, dark background, strategic highlights',
        'camera_style': 'static or slow rotation, floating effect, dramatic angles',
        'mood': 'mysterious, sophisticated, exclusive, dramatic',
        'color_palette': ['#000000', '#1A1A1A', '#C0C0C0', '#FFD700'],
        'texture': 'smooth glass, metallic accents, deep blacks, glossy finish',
        'grade': 'high contrast, deep blacks, lifted highlights, moody',
        'examples': ['Yves Saint Laurent', 'Versace', 'Armani'],
        'keywords': ['dark', 'elegant', 'mysterious', 'dramatic'],
        'music_mood': 'dramatic',
        'best_for': ['Masculine fragrances', 'Exclusive perfumes', 'Evening scents'],
        'priority_weight': 1.0
    },
    
    VideoStyle.ROMANTIC_FLORAL: {
        'display_name': 'Romantic Floral',
        'description': 'Soft pastels, floral elements, feminine aesthetic',
        'short_description': 'Romantic, delicate',
        'scene_keywords': 'soft pink tones, floral elements, rose petals, delicate lighting, feminine elegance',
        'lighting': 'soft diffused lighting, natural glow, gentle highlights',
        'camera_style': 'gentle movements, soft focus, dreamy aesthetic',
        'mood': 'romantic, feminine, delicate, dreamy',
        'color_palette': ['#FFB6C1', '#FFC0CB', '#FADADD', '#E6E6FA'],
        'texture': 'soft petals, silk, delicate materials, smooth glass',
        'grade': 'soft pastels, lifted shadows, gentle desaturation',
        'examples': ['Marc Jacobs', 'Viktor & Rolf', 'Valentino'],
        'keywords': ['romantic', 'floral', 'feminine', 'delicate'],
        'music_mood': 'calm',
        'best_for': ['Feminine fragrances', 'Floral perfumes', 'Spring/Summer scents'],
        'priority_weight': 1.0
    }
}

# Priority weights for style cascading
# Used by StyleCascadingManager to merge multiple style sources
STYLE_PRIORITY_WEIGHTS = {
    'brand_guidelines': 1.0,      # HIGHEST - always followed
    'user_selected_style': 0.7,   # MORE WEIGHT - user choice
    'creative_prompt': 0.7,       # MORE WEIGHT - user instructions
    'reference_image': 0.2        # SOME WEIGHT - subtle influence
}


class StyleManager:
    """
    Manages luxury perfume video style configuration and application throughout the pipeline.
    
    Responsibilities:
    - Retrieve perfume style configurations (gold_luxe, dark_elegance, romantic_floral)
    - Apply style guidance to scene prompts
    - Generate StyleSpec overrides for specific perfume styles
    - Determine appropriate music mood for each perfume style
    """
    
    @staticmethod
    def get_style_config(style: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Get complete configuration for a perfume style.
        
        Args:
            style: Style name (e.g., 'gold_luxe', 'dark_elegance', 'romantic_floral')
        
        Returns:
            Dictionary with complete style configuration or None if invalid
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
    def apply_style_to_scene_prompt(scene_prompt: str, style: Optional[str]) -> str:
        """
        Enhance scene prompt with perfume style-specific keywords and guidance.
        
        Args:
            scene_prompt: Original scene description/prompt
            style: Perfume style to apply (gold_luxe, dark_elegance, romantic_floral)
        
        Returns:
            Enhanced prompt with perfume style keywords
        
        Example:
            "perfume bottle close-up" → "perfume bottle close-up with golden hour lighting, warm champagne tones..."
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
        
        Used by AudioEngine to select music that matches the visual style.
        
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
        Get human-readable display name for a perfume style.
        
        Args:
            style: Style name (e.g., 'gold_luxe', 'dark_elegance', 'romantic_floral')
        
        Returns:
            Display name (e.g., "Gold Luxe")
        """
        config = StyleManager.get_style_config(style)
        if config:
            return config.get('display_name', style)
        return style

