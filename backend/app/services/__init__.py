"""Core services for AI Ad Video Generator.

This module contains all backend services for video generation:
1. ScenePlanner - LLM-based scene planning
2. ProductExtractor - Background removal and product isolation
3. VideoGenerator - AI video generation via Replicate Wān
4. Compositor - Product overlay onto background videos
5. TextOverlayRenderer - Add text overlays to videos
6. AudioEngine - Background music generation
7. Renderer - Final video rendering and multi-aspect export
"""

from app.services.scene_planner import ScenePlanner, AdProjectPlan, Scene, StyleSpec, TextOverlay
from app.services.product_extractor import ProductExtractor
from app.services.video_generator import VideoGenerator
from app.services.compositor import Compositor
from app.services.text_overlay import TextOverlayRenderer
from app.services.audio_engine import AudioEngine
from app.services.renderer import Renderer

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
    # Video Processing
    "Compositor",
    "TextOverlayRenderer",
    "Renderer",
]

