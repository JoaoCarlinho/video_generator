"""Core services for AI Ad Video Generator.

This module contains all backend services for video generation:
1. ScenePlanner - LLM-based scene planning
2. ProductExtractor - Background removal and product isolation
3. VideoGenerator - AI video generation via Replicate Wān
4. Compositor - Product overlay onto background videos
5. TextOverlayRenderer - Add text overlays to videos
6. AudioEngine - Background music generation
7. Renderer - Final video rendering and multi-aspect export
8. ReferenceImageStyleExtractor - Extract visual style from reference images
"""

from .scene_planner import ScenePlanner, AdProjectPlan, Scene, StyleSpec, TextOverlay
from .video_generator import VideoGenerator
from .audio_engine import AudioEngine
from .reference_image_extractor import ReferenceImageStyleExtractor, ExtractedStyle

# Import image processing services only if dependencies are available
# (these require OpenCV/NumPy which may not be available in API Lambda)
try:
    from .product_extractor import ProductExtractor
    from .compositor import Compositor
    from .text_overlay import TextOverlayRenderer
    from .renderer import Renderer
    _HAS_IMAGE_PROCESSING = True
except (ImportError, AttributeError) as e:
    # Missing libGL.so.1 or NumPy compatibility issues
    ProductExtractor = None
    Compositor = None
    TextOverlayRenderer = None
    Renderer = None
    _HAS_IMAGE_PROCESSING = False

__all__ = [
    # Scene Planning
    "ScenePlanner",
    "AdProjectPlan",
    "Scene",
    "StyleSpec",
    "TextOverlay",
    # Asset Services
    "ProductExtractor",
    "VideoGenerator",
    "AudioEngine",
    # Reference Image Processing
    "ReferenceImageStyleExtractor",
    "ExtractedStyle",
    # Video Processing
    "Compositor",
    "TextOverlayRenderer",
    "Renderer",
]

