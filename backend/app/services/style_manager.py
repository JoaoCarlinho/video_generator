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
        'description': 'High-quality camera feel, dramatic lighting, depth of field, modern ad look',
        'short_description': 'Professional, dramatic',
        'scene_keywords': 'cinematic camera work, dramatic lighting, shallow depth of field, professional color grading, modern premium aesthetic',
        'lighting': 'dramatic directional lighting with shadows, strategic highlights',
        'camera_style': 'cinematic camera movements, slow pans, subtle zooms, professional framing',
        'mood': 'sophisticated, premium, cinematic, dramatic',
        'color_palette': ['#2C1810', '#D4AF37', '#1A1A1A', '#C4B5A0'],
        'texture': 'cinema-grade cinematography, film-like quality',
        'grade': 'cinematic color grade, high contrast, warm tones',
        'examples': ['Nike', 'Apple', 'Samsung'],
        'keywords': ['professional', 'dramatic', 'premium'],
        'music_mood': 'dramatic',
        'best_for': ['Luxury brands', 'Premium products', 'High-end services']
    },
    
    VideoStyle.DARK_PREMIUM: {
        'display_name': 'Dark Premium',
        'description': 'Black background, rim lighting, contrast-heavy, product floating or rotating',
        'short_description': 'Luxury, exclusive',
        'scene_keywords': 'dark black background, rim lighting, high contrast, product isolated and floating, luxury aesthetic, product rotating on axis',
        'lighting': 'rim lighting on product edges, dark background, strategic accent lighting, backlight emphasis',
        'camera_style': 'static or slow product rotation, floating effect, 360-degree showcase',
        'mood': 'luxurious, sophisticated, exclusive, premium, elegant',
        'color_palette': ['#000000', '#FF6B9D', '#C44569', '#F39C12'],
        'texture': 'smooth luxurious surfaces, glossy finish, metallic hints',
        'grade': 'high contrast, deep blacks, vibrant accents, moody',
        'examples': ['Sony', 'Nike', 'Luxury brands'],
        'keywords': ['luxury', 'dark', 'premium', 'exclusive'],
        'music_mood': 'luxurious',
        'best_for': ['Luxury goods', 'High-end electronics', 'Premium beauty']
    },
    
    VideoStyle.MINIMAL_STUDIO: {
        'display_name': 'Minimal Studio',
        'description': 'Minimal, bright, Apple-style aesthetic with clean compositions',
        'short_description': 'Clean, modern',
        'scene_keywords': 'minimalist studio style, clean bright background, simple composition, Apple aesthetic, premium simplicity, product-centric',
        'lighting': 'even soft lighting, bright clean environment, minimal shadows',
        'camera_style': 'static or subtle movements, product-centric, simple framing',
        'mood': 'clean, minimal, premium, modern, simple, refined',
        'color_palette': ['#FFFFFF', '#F5F5F5', '#333333', '#0071E3'],
        'texture': 'clean minimal surfaces, smooth finishes, professional',
        'grade': 'bright, clean, minimal color grading, neutral tones',
        'examples': ['Apple', 'Tech brands', 'Wellness', 'Ecommerce'],
        'keywords': ['minimal', 'clean', 'bright', 'simple'],
        'music_mood': 'calm',
        'best_for': ['Tech products', 'SaaS', 'Wellness brands', 'Clean beauty']
    },
    
    VideoStyle.LIFESTYLE: {
        'display_name': 'Lifestyle',
        'description': 'Product used in everyday scenarios — running, cooking, working out, fashion',
        'short_description': 'Authentic, relatable',
        'scene_keywords': 'lifestyle photography, product in active use, everyday scenario, authentic moment, relatable context, real-world usage, genuine emotion',
        'lighting': 'natural or warm lighting, realistic, candid',
        'camera_style': 'documentary-style, natural movements, handheld feel, motion-focused',
        'mood': 'authentic, relatable, real-world, genuine, warm, human',
        'color_palette': ['#E8D4B8', '#C89968', '#556B2F', '#8B4513'],
        'texture': 'natural real-world textures, organic materials, authentic surfaces',
        'grade': 'warm, natural, authentic color grading, slightly desaturated',
        'examples': ['Social ads', 'Relatable brands', 'Lifestyle companies'],
        'keywords': ['authentic', 'real-world', 'relatable', 'genuine'],
        'music_mood': 'uplifting',
        'best_for': ['Everyday products', 'Sports brands', 'Fashion', 'Social media']
    },
    
    VideoStyle.ANIMATED_2D: {
        'display_name': '2D Animated',
        'description': 'Modern vector-style animation for explainers or playful ads',
        'short_description': 'Playful, modern',
        'scene_keywords': '2D animation, vector style, motion graphics, modern animated explainer, playful transitions, illustrated style, dynamic movement',
        'lighting': 'stylized animated lighting, flat or gradient backgrounds',
        'camera_style': 'animated transitions, playful movements, parallax effects, dynamic motion',
        'mood': 'playful, modern, innovative, fun, engaging, youthful',
        'color_palette': ['#FF6B9D', '#4ECDC4', '#FFE66D', '#95E1D3'],
        'texture': 'smooth vector illustration style, clean lines, graphic design',
        'grade': 'vibrant, saturated, stylized colors, bold',
        'examples': ['Fintech', 'SaaS', 'Apps', 'Startups'],
        'keywords': ['animated', 'playful', 'modern', 'fun'],
        'music_mood': 'playful',
        'best_for': ['Tech startups', 'SaaS platforms', 'Mobile apps', 'Fintech']
    }
}


class StyleManager:
    """
    Manages video style configuration and application throughout the pipeline.
    
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
        Enhance scene prompt with style-specific keywords and guidance.
        
        Args:
            scene_prompt: Original scene description/prompt
            style: Style to apply
        
        Returns:
            Enhanced prompt with style keywords
        
        Example:
            "sunset beach" → "sunset beach with cinematic lighting, drama..."
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

