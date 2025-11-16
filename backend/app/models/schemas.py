"""Pydantic schemas for API validation and serialization."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal


# ============================================================================
# Scene Background Upload Schema
# ============================================================================

class SceneBackgroundInput(BaseModel):
    """Scene background mapping for custom backgrounds."""
    scene_id: str = Field(..., description="Scene identifier (e.g., 'scene_1')")
    background_url: str = Field(..., description="S3 URL of uploaded background image")


# ============================================================================
# Project Request Schemas
# ============================================================================

class CreateProjectRequest(BaseModel):
    """Request schema for creating a new ad generation project."""
    title: str = Field(..., min_length=1, max_length=200, description="Project title")
    creative_prompt: str = Field(
        ...,
        min_length=20,
        max_length=3000,
        description="User's creative vision for the video"
    )
    target_duration: int = Field(..., ge=15, le=120, description="Target video duration in seconds")
    brand_name: str = Field(..., min_length=1, max_length=100, description="Brand name")
    brand_description: Optional[str] = Field(None, description="Brand story, values, personality")
    target_audience: Optional[str] = Field(None, description="Target audience description")

    # NEW FIELDS for Story 3
    product_images: Optional[List[str]] = Field(
        default=None,
        max_items=10,
        description="Array of S3 URLs for product images (max 10). First image is primary."
    )
    scene_backgrounds: Optional[List[SceneBackgroundInput]] = Field(
        default=None,
        description="Array of scene-background mappings for custom backgrounds"
    )
    output_formats: Optional[List[str]] = Field(
        default=["16:9"],
        description="Array of desired aspect ratios: '9:16' (vertical), '16:9' (horizontal), '1:1' (square)"
    )

    # LEGACY FIELDS (for backward compatibility)
    aspect_ratio: Optional[str] = Field(
        default="16:9",
        description="DEPRECATED: Use output_formats instead. Primary aspect ratio."
    )
    logo_url: Optional[str] = Field(None, description="S3 URL of uploaded brand logo")
    product_image_url: Optional[str] = Field(None, description="DEPRECATED: Use product_images instead")
    guidelines_url: Optional[str] = Field(None, description="S3 URL of uploaded brand guidelines")

    @validator('output_formats')
    def validate_output_formats(cls, v):
        """Ensure at least one format and all valid."""
        if not v or len(v) == 0:
            raise ValueError("At least one output format must be specified")

        valid_formats = {'9:16', '16:9', '1:1'}
        for fmt in v:
            if fmt not in valid_formats:
                raise ValueError(f"Invalid aspect ratio: {fmt}. Must be one of {valid_formats}")

        # Remove duplicates
        return list(set(v))

    @validator('product_images')
    def validate_product_images(cls, v):
        """Ensure not more than 10 images."""
        if v and len(v) > 10:
            raise ValueError("Maximum 10 product images allowed")
        return v


# ============================================================================
# Project Response Schemas
# ============================================================================

class ProjectResponse(BaseModel):
    """Response schema for project basic info."""
    id: UUID
    user_id: UUID
    title: str
    status: str
    progress: int
    cost: float
    s3_project_folder: Optional[str]
    s3_project_folder_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDetailResponse(BaseModel):
    """Response schema for full project details."""
    id: UUID
    user_id: UUID
    title: str
    ad_project_json: Dict[str, Any]
    status: str
    progress: int
    cost: float
    error_message: Optional[str]
    s3_project_folder: Optional[str]
    s3_project_folder_url: Optional[str]
    aspect_ratio: str
    local_project_path: Optional[str]
    local_video_paths: Optional[Dict[str, str]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Response schema for list of projects with pagination."""
    total: int
    limit: int
    offset: int
    projects: List[ProjectResponse]


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str


# ============================================================================
# Generation Progress Schema
# ============================================================================

class GenerationProgressResponse(BaseModel):
    """Response schema for generation progress polling."""
    project_id: UUID
    status: str
    progress: int
    error_message: Optional[str] = None
    local_video_paths: Optional[Dict[str, str]] = None


# ============================================================================
# Ad Project Domain Models (used in pipeline)
# ============================================================================

class Overlay(BaseModel):
    """Text overlay configuration for a scene."""
    text: str
    position: str = "bottom_center"  # top_left, top_center, top_right, center, bottom_left, bottom_center, bottom_right
    font_size: int = 48
    duration: float
    start_time: Optional[float] = 0.0


class Scene(BaseModel):
    """Scene configuration in ad project."""
    id: str
    role: str  # hook, problem, solution, cta, etc.
    duration: float
    description: str
    background_prompt: str
    background_type: str = "ai_generated"  # ai_generated or custom_upload
    use_product: bool = False
    use_logo: bool = False
    product_usage: str = "none"  # none, static_insert, animated
    camera_movement: str = "static"
    transition_to_next: str = "cut"
    overlay: Optional[Overlay] = None
    custom_background_url: Optional[str] = None  # NEW: for custom scene backgrounds


class StyleSpec(BaseModel):
    """Visual style specification for consistent look."""
    lighting: str
    camera_style: str
    mood: str
    color_palette: List[str]
    texture: str
    grade: str


class ProductAsset(BaseModel):
    """Product image asset configuration."""
    original_url: str
    masked_png_url: Optional[str] = None
    mask_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    extracted_at: Optional[str] = None


class BrandConfig(BaseModel):
    """Brand configuration."""
    name: str
    description: Optional[str] = None
    font_family: str = "Inter"
    logo_url: Optional[str] = None
    guidelines_url: Optional[str] = None


class VideoSettings(BaseModel):
    """Video rendering settings."""
    aspect_ratio: str = "16:9"  # DEPRECATED: use output_formats in AdProject root
    resolution: str = "1080p"
    fps: int = 30
    codec: str = "h264"


class AudioSettings(BaseModel):
    """Audio settings."""
    include_music: bool = True
    music_volume: float = -6.0
    enable_voiceover: bool = False


class AdProject(BaseModel):
    """Complete ad project configuration stored in database JSON field."""
    version: str = "1.0"
    creative_prompt: str
    target_duration: int
    target_audience: Optional[str] = None
    brand: BrandConfig
    product_asset: Optional[ProductAsset] = None

    # NEW FIELDS for Story 3
    product_images: Optional[List[str]] = None  # Array of product image URLs
    scene_backgrounds: Optional[List[SceneBackgroundInput]] = None  # Custom scene backgrounds
    output_formats: Optional[List[str]] = ["16:9"]  # Multiple aspect ratios

    style_spec: Optional[StyleSpec] = None
    scenes: List[Scene] = []
    video_settings: VideoSettings
    audio_settings: AudioSettings
    render_status: Optional[str] = None
