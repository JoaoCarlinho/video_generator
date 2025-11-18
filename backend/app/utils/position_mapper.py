"""Position mapping utilities for aspect-ratio aware positioning."""

from typing import Dict, Tuple


def get_position_coordinates(
    position: str,
    frame_width: int,
    frame_height: int,
    element_width: int,
    element_height: int,
    margin: int = 40
) -> Tuple[int, int]:
    """
    Convert logical position to pixel coordinates.
    
    Args:
        position: Logical position (center, top_left, etc.)
        frame_width: Video frame width
        frame_height: Video frame height
        element_width: Element width (product/logo)
        element_height: Element height (product/logo)
        margin: Margin from edges in pixels
        
    Returns:
        Tuple of (x, y) coordinates
    """
    positions = {
        "center": (
            (frame_width - element_width) // 2,
            (frame_height - element_height) // 2,
        ),
        "left": (
            margin,
            (frame_height - element_height) // 2,
        ),
        "right": (
            frame_width - element_width - margin,
            (frame_height - element_height) // 2,
        ),
        "top_left": (margin, margin),
        "top_right": (frame_width - element_width - margin, margin),
        "bottom_left": (margin, frame_height - element_height - margin),
        "bottom_right": (
            frame_width - element_width - margin,
            frame_height - element_height - margin,
        ),
        "bottom_center": (
            (frame_width - element_width) // 2,
            frame_height - element_height - margin,
        ),
    }
    
    return positions.get(position, positions["center"])


def get_safe_zones(aspect_ratio: str) -> Dict[str, float]:
    """
    Get safe zone percentages for different aspect ratios.
    
    Safe zones prevent text/elements from being cut off on different screens.
    
    Args:
        aspect_ratio: "16:9", "9:16", or "1:1"
        
    Returns:
        Dict with top, bottom, left, right percentages
    """
    safe_zones = {
        "16:9": {  # Horizontal - wider safe zones on sides
            "top": 0.10,
            "bottom": 0.15,
            "left": 0.05,
            "right": 0.05,
        },
        "9:16": {  # Vertical - wider safe zones top/bottom
            "top": 0.15,
            "bottom": 0.20,
            "left": 0.08,
            "right": 0.08,
        },
        "1:1": {  # Square - balanced safe zones
            "top": 0.12,
            "bottom": 0.15,
            "left": 0.08,
            "right": 0.08,
        },
    }
    
    return safe_zones.get(aspect_ratio, safe_zones["16:9"])


def suggest_text_position(
    has_product: bool,
    product_position: str,
    has_logo: bool,
    logo_position: str,
    aspect_ratio: str = "16:9"
) -> str:
    """
    Suggest text overlay position based on product/logo placement.
    
    Args:
        has_product: Whether scene has product
        product_position: Product position if present
        has_logo: Whether scene has logo
        logo_position: Logo position if present
        aspect_ratio: Video aspect ratio
        
    Returns:
        Suggested text position: "top", "bottom", "center"
    """
    # Priority: avoid overlapping product and logo
    occupied_positions = []
    
    if has_product and product_position:
        if 'bottom' in product_position:
            occupied_positions.append('bottom')
        elif 'top' in product_position:
            occupied_positions.append('top')
        else:
            occupied_positions.append('center')
    
    if has_logo and logo_position:
        if 'bottom' in logo_position:
            occupied_positions.append('bottom')
        elif 'top' in logo_position:
            occupied_positions.append('top')
    
    # Choose unoccupied position
    if 'bottom' not in occupied_positions:
        return 'bottom'
    elif 'top' not in occupied_positions:
        return 'top'
    else:
        return 'center'

