"""Product type definitions with their specific attributes and prompt customizations.

This module defines the supported product types and their configurations for video generation.
Each product type has its own shot grammar, director persona, and visual language.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ProductTypeConfig(BaseModel):
    """Configuration for a specific product type."""
    id: str  # e.g., "fragrance", "car", "watch", "energy"
    display_name: str
    description: str
    supports_gender: bool  # Whether this product type has gender variants
    shot_grammar_file: str  # Path to shot grammar JSON (relative to templates/scene_grammar/)

    # Prompt customization
    director_persona: str  # "PERFUME COMMERCIAL DIRECTOR", "AUTOMOTIVE DIRECTOR", etc.
    visual_language_title: str  # "PERFUME VISUAL LANGUAGE", "AUTOMOTIVE CINEMATOGRAPHY"
    common_elements_title: str  # "COMMON PERFUME AD ELEMENTS", "CAR COMMERCIAL TECHNIQUES"

    # Gender-specific prompts (if supports_gender=True)
    gender_prompts: Optional[Dict[str, str]] = None

    # Product-specific visual characteristics
    default_mood: str = "luxurious"
    default_lighting: str = "dramatic"
    key_visual_elements: List[str] = []


# Registry of supported product types
PRODUCT_TYPES: Dict[str, ProductTypeConfig] = {
    "fragrance": ProductTypeConfig(
        id="fragrance",
        display_name="Fragrance/Perfume",
        description="Luxury perfumes and fragrances",
        supports_gender=True,
        shot_grammar_file="perfume_shot_grammar.json",
        director_persona="world-class PERFUME COMMERCIAL DIRECTOR",
        visual_language_title="PERFUME VISUAL LANGUAGE LIBRARY",
        common_elements_title="COMMON PERFUME AD ELEMENTS",
        default_mood="luxurious and elegant",
        default_lighting="soft with rim lighting",
        key_visual_elements=[
            "Bottle close-ups with premium lighting",
            "Silk fabric and flowing materials",
            "Luxury environments (marble, velvet, gold accents)",
            "Mist and spray effects",
            "Elegant product reveals"
        ],
        gender_prompts={
            "masculine": """This is a MASCULINE fragrance. Apply these visual characteristics:
- Deep, bold tones (navy, charcoal, forest green, burgundy)
- Strong, confident lighting with hard edges and dramatic shadows
- Masculine materials: leather, wood, steel, stone
- Angular compositions and geometric shapes
- Urban or rugged natural environments
- Powerful, assertive mood""",
            "feminine": """This is a FEMININE fragrance. Apply these visual characteristics:
- Soft, elegant tones (rose gold, pearl, blush, lavender, champagne)
- Gentle lighting with soft diffusion and glowing highlights
- Feminine materials: silk, satin, flowers, crystals
- Flowing, organic compositions
- Elegant environments (gardens, ballrooms, luxury interiors)
- Graceful, romantic mood""",
            "unisex": """This is a UNISEX fragrance. Apply these visual characteristics:
- Balanced, versatile tones (whites, greys, muted earth tones)
- Clean, modern lighting with subtle sophistication
- Universal materials: glass, water, clean fabrics, minimalist elements
- Balanced compositions with both soft and structured elements
- Contemporary, timeless environments
- Sophisticated, inclusive mood"""
        }
    ),

    "car": ProductTypeConfig(
        id="car",
        display_name="Automobile/Vehicle",
        description="Cars, trucks, motorcycles, and other vehicles",
        supports_gender=False,
        shot_grammar_file="car_shot_grammar.json",
        director_persona="world-class AUTOMOTIVE COMMERCIAL DIRECTOR",
        visual_language_title="AUTOMOTIVE CINEMATOGRAPHY LIBRARY",
        common_elements_title="CAR COMMERCIAL SHOT TECHNIQUES",
        default_mood="powerful and dynamic",
        default_lighting="dramatic with strong reflections",
        key_visual_elements=[
            "Dynamic tracking shots showing motion",
            "Detail shots of design elements (grille, headlights, wheels)",
            "Reflections and paint quality",
            "Interior craftsmanship and technology",
            "Environmental context (roads, cityscapes, nature)",
            "Speed and performance indicators"
        ],
        gender_prompts=None
    ),

    "watch": ProductTypeConfig(
        id="watch",
        display_name="Watch/Timepiece",
        description="Luxury watches and timepieces",
        supports_gender=False,
        shot_grammar_file="watch_shot_grammar.json",
        director_persona="world-class LUXURY TIMEPIECE DIRECTOR",
        visual_language_title="HOROLOGY VISUAL LANGUAGE LIBRARY",
        common_elements_title="WATCH COMMERCIAL TECHNIQUES",
        default_mood="sophisticated and precise",
        default_lighting="focused with jewelry lighting",
        key_visual_elements=[
            "Macro shots of watch face and complications",
            "Movement and mechanism details (if visible)",
            "Bracelet/strap craftsmanship",
            "Reflections on crystal and metal",
            "On-wrist lifestyle moments",
            "Heritage and craftsmanship storytelling"
        ],
        gender_prompts=None
    ),

    "energy": ProductTypeConfig(
        id="energy",
        display_name="Energy/Utilities",
        description="Electricity, gas, renewable energy, and utility services",
        supports_gender=False,
        shot_grammar_file="energy_shot_grammar.json",
        director_persona="world-class ENERGY & SUSTAINABILITY DIRECTOR",
        visual_language_title="ENERGY VISUAL STORYTELLING LIBRARY",
        common_elements_title="ENERGY COMMERCIAL TECHNIQUES",
        default_mood="innovative and trustworthy",
        default_lighting="clean and bright with modern feel",
        key_visual_elements=[
            "Clean energy sources (solar panels, wind turbines)",
            "Power infrastructure and technology",
            "Homes and businesses being powered",
            "Environmental benefits and sustainability",
            "Innovation and future-focused imagery",
            "Community and reliability themes"
        ],
        gender_prompts=None
    ),
}


def get_product_type_config(product_type: str) -> ProductTypeConfig:
    """
    Get configuration for a product type.

    Args:
        product_type: Product type ID (e.g., 'fragrance', 'car', 'watch', 'energy')

    Returns:
        ProductTypeConfig for the type, defaults to fragrance if not found
    """
    return PRODUCT_TYPES.get(product_type.lower(), PRODUCT_TYPES["fragrance"])


def get_all_product_types() -> List[ProductTypeConfig]:
    """Get list of all supported product types."""
    return list(PRODUCT_TYPES.values())


def get_product_type_choices() -> List[Dict[str, str]]:
    """Get product type choices for frontend/forms."""
    return [
        {
            "id": config.id,
            "display_name": config.display_name,
            "description": config.description,
            "supports_gender": config.supports_gender
        }
        for config in PRODUCT_TYPES.values()
    ]
