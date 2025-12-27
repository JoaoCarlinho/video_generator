"""Pydantic schemas for API validation and serialization."""

from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============================================================================
# Campaign Status Enum
# ============================================================================

class CampaignStatus(str, Enum):
    """Campaign status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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

    # PHASE 7: Style selection field
    selected_style: Optional[str] = Field(
        default=None,
        description="User-selected video style (e.g., 'cinematic', 'minimalist', 'energetic'). If None, LLM will infer."
    )

    # WAN 2.5: Video provider selection
    video_provider: str = Field(
        default="replicate",
        description="Video generation provider: 'replicate' (cloud API) or 'ecs' (self-hosted GPU)",
        example="replicate"
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

    @validator('video_provider')
    def validate_video_provider(cls, v):
        """Validate video provider is either 'replicate' or 'ecs'."""
        valid_providers = ['replicate', 'ecs']
        if v not in valid_providers:
            raise ValueError(
                f"video_provider must be one of: {', '.join(valid_providers)}. Got: '{v}'"
            )
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

    # WAN 2.5: Video provider tracking
    video_provider: str = Field(description="Video generation provider used", example="replicate")
    video_provider_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Provider-specific metadata (failover events, endpoint info)",
        example={"primary_provider": "ecs", "failover_used": False, "timestamp": "2025-01-21T12:00:00Z"}
    )

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

    # WAN 2.5: Video provider tracking
    video_provider: str = Field(description="Video generation provider used", example="replicate")
    video_provider_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Provider-specific metadata (failover events, endpoint info)",
        example={"primary_provider": "ecs", "failover_used": False, "timestamp": "2025-01-21T12:00:00Z"}
    )

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
    campaign_id: UUID
    status: str
    progress: int
    current_step: str
    cost_so_far: float
    error_message: Optional[str] = None
    local_video_paths: Optional[Dict[str, str]] = None


# ============================================================================
# Brand Schemas
# ============================================================================

class CreateBrandRequest(BaseModel):
    """Request schema for creating a new brand."""
    company_name: str = Field(..., min_length=1, max_length=200, description="Company name (required)")
    brand_name: Optional[str] = Field(None, max_length=200, description="Brand name (optional, if different from company name)")
    description: Optional[str] = Field(None, description="Brand description, story, values")
    guidelines: Optional[str] = Field(None, description="Brand guidelines, voice, style notes")
    logo_urls: Optional[Union[Dict[str, Any], List[str]]] = Field(None, description="Logo URLs as dict or list")


class UpdateBrandRequest(BaseModel):
    """Request schema for updating an existing brand."""
    company_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Company name")
    brand_name: Optional[str] = Field(None, max_length=200, description="Brand name")
    description: Optional[str] = Field(None, description="Brand description")
    guidelines: Optional[str] = Field(None, description="Brand guidelines")
    logo_urls: Optional[Union[Dict[str, Any], List[str]]] = Field(None, description="Logo URLs as dict or list")


class BrandResponse(BaseModel):
    """Response schema for brand data."""
    id: UUID
    user_id: UUID
    company_name: str
    brand_name: Optional[str]
    description: Optional[str]
    guidelines: Optional[str]
    logo_urls: Optional[Union[Dict[str, Any], List[str]]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Brand Schema Aliases (for backward compatibility)
# ============================================================================
BrandDetail = BrandResponse
BrandCreate = CreateBrandRequest


# ============================================================================
# Product Schemas
# ============================================================================

class CreateProductRequest(BaseModel):
    """Request schema for creating a new product."""
    product_type: str = Field(
        ..., min_length=1, max_length=100,
        description="Product type (fragrance, car, watch, energy, mobile_app, etc.)"
    )
    name: str = Field(..., min_length=1, max_length=200, description="Product name (required)")
    product_gender: Optional[str] = Field(
        None, description="Product gender: masculine, feminine, unisex, or NULL for non-gendered"
    )
    product_attributes: Optional[Dict[str, Any]] = Field(
        None, description="Type-specific attributes (e.g., car_category, watch_movement)"
    )
    icp_segment: Optional[str] = Field(None, description="ICP/target audience segment")
    image_urls: Optional[List[str]] = Field(
        None, max_items=10, description="Product image URLs (max 10)"
    )

    # Mobile App specific fields
    app_input_mode: Optional[str] = Field(
        None, description="Mobile app input mode: 'screenshots' or 'generated'"
    )
    app_description: Optional[str] = Field(
        None, max_length=2000,
        description="App description for UI generation (required if app_input_mode='generated')"
    )
    key_features: Optional[List[str]] = Field(
        None, max_length=10,
        description="Key app features to showcase (max 10 items)"
    )
    app_visual_style: Optional[str] = Field(
        None,
        description="App visual style: modern_minimal, dark_mode, vibrant_colorful, "
        "professional_corporate, playful_friendly"
    )
    screen_recording_url: Optional[str] = Field(
        None, description="S3 URL of uploaded screen recording video"
    )

    @field_validator('image_urls')
    @classmethod
    def validate_image_urls(cls, v):
        """Validate image_urls array has max 10 items."""
        if v is not None and len(v) > 10:
            raise ValueError('Maximum 10 image URLs allowed')
        return v

    @field_validator('product_gender')
    @classmethod
    def validate_product_gender(cls, v):
        """Validate product_gender is one of allowed values."""
        if v is not None and v not in ['masculine', 'feminine', 'unisex']:
            raise ValueError('product_gender must be one of: masculine, feminine, unisex')
        return v

    @field_validator('app_input_mode')
    @classmethod
    def validate_app_input_mode(cls, v):
        """Validate app_input_mode is one of allowed values."""
        if v is not None and v not in ['screenshots', 'generated']:
            raise ValueError("app_input_mode must be 'screenshots' or 'generated'")
        return v

    @field_validator('key_features')
    @classmethod
    def validate_key_features(cls, v):
        """Validate key_features array has max 10 items."""
        if v is not None and len(v) > 10:
            raise ValueError('Maximum 10 key features allowed')
        return v

    @field_validator('app_visual_style')
    @classmethod
    def validate_app_visual_style(cls, v):
        """Validate app_visual_style is one of allowed values."""
        valid_styles = [
            'modern_minimal', 'dark_mode', 'vibrant_colorful',
            'professional_corporate', 'playful_friendly'
        ]
        if v is not None and v not in valid_styles:
            raise ValueError(f"app_visual_style must be one of: {', '.join(valid_styles)}")
        return v


class UpdateProductRequest(BaseModel):
    """Request schema for updating an existing product."""
    product_type: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Product type"
    )
    name: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Product name"
    )
    product_gender: Optional[str] = Field(
        None, description="Product gender: masculine, feminine, unisex, or NULL"
    )
    product_attributes: Optional[Dict[str, Any]] = Field(
        None, description="Type-specific attributes"
    )
    icp_segment: Optional[str] = Field(None, description="ICP/target audience segment")
    image_urls: Optional[List[str]] = Field(
        None, max_items=10, description="Product image URLs (max 10)"
    )

    # Mobile App specific fields
    app_input_mode: Optional[str] = Field(
        None, description="Mobile app input mode: 'screenshots' or 'generated'"
    )
    app_description: Optional[str] = Field(
        None, max_length=2000,
        description="App description for UI generation"
    )
    key_features: Optional[List[str]] = Field(
        None, max_length=10,
        description="Key app features to showcase (max 10 items)"
    )
    app_visual_style: Optional[str] = Field(
        None,
        description="App visual style: modern_minimal, dark_mode, vibrant_colorful, "
        "professional_corporate, playful_friendly"
    )
    screen_recording_url: Optional[str] = Field(
        None, description="S3 URL of uploaded screen recording video"
    )

    @field_validator('image_urls')
    @classmethod
    def validate_image_urls(cls, v):
        """Validate image_urls array has max 10 items."""
        if v is not None and len(v) > 10:
            raise ValueError('Maximum 10 image URLs allowed')
        return v

    @field_validator('product_gender')
    @classmethod
    def validate_product_gender(cls, v):
        """Validate product_gender is one of allowed values."""
        if v is not None and v not in ['masculine', 'feminine', 'unisex']:
            raise ValueError('product_gender must be one of: masculine, feminine, unisex')
        return v

    @field_validator('app_input_mode')
    @classmethod
    def validate_app_input_mode(cls, v):
        """Validate app_input_mode is one of allowed values."""
        if v is not None and v not in ['screenshots', 'generated']:
            raise ValueError("app_input_mode must be 'screenshots' or 'generated'")
        return v

    @field_validator('key_features')
    @classmethod
    def validate_key_features(cls, v):
        """Validate key_features array has max 10 items."""
        if v is not None and len(v) > 10:
            raise ValueError('Maximum 10 key features allowed')
        return v

    @field_validator('app_visual_style')
    @classmethod
    def validate_app_visual_style(cls, v):
        """Validate app_visual_style is one of allowed values."""
        valid_styles = [
            'modern_minimal', 'dark_mode', 'vibrant_colorful',
            'professional_corporate', 'playful_friendly'
        ]
        if v is not None and v not in valid_styles:
            raise ValueError(f"app_visual_style must be one of: {', '.join(valid_styles)}")
        return v


class ProductResponse(BaseModel):
    """Response schema for product data."""
    id: UUID
    brand_id: UUID
    product_type: str
    name: str
    product_gender: Optional[str]
    product_attributes: Optional[Dict[str, Any]]
    icp_segment: Optional[str]
    image_urls: Optional[List[str]]

    # Mobile App specific fields
    app_input_mode: Optional[str] = None
    app_description: Optional[str] = None
    key_features: Optional[List[str]] = None
    app_visual_style: Optional[str] = None
    screen_recording_url: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Campaign Schemas
# ============================================================================

class CinematographySchema(BaseModel):
    """Cinematography configuration for a scene."""
    camera_aspect: str = Field(..., description="Camera angle: POV, near_birds_eye, satellite, follow")
    lighting: str = Field(..., description="Lighting style: natural, golden_hour, dramatic, soft, high_contrast, studio, dim, bright")
    mood: str = Field(..., description="Scene mood: energetic, calm, suspenseful, playful, professional, intimate, powerful")
    transition: str = Field(..., description="Transition to next scene: cut, fade, dissolve, wipe, slide")
    environment: str = Field(..., description="Environment: bright, dim, foggy, clear, urban, natural, indoor, outdoor")
    setting: str = Field(..., max_length=100, description="Physical setting (residential, office, beach, etc.)")


class SceneConfigSchema(BaseModel):
    """Scene configuration for campaign."""
    scene_number: int = Field(..., ge=1, le=10, description="Scene number (1-10)")
    creative_vision: str = Field(..., min_length=20, max_length=2000, description="Creative vision description")
    reference_images: List[str] = Field(..., min_items=3, max_items=3, description="3 reference images: theme, start interpolation, end interpolation")
    cinematography: CinematographySchema


class CreateCampaignRequest(BaseModel):
    """Request schema for creating a new campaign.

    Campaigns are organizational containers for creatives.
    Video-specific settings (duration, scenes) are defined per-creative.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Campaign name")
    seasonal_event: str = Field(..., min_length=1, max_length=100, description="Seasonal event or marketing initiative")
    year: int = Field(..., ge=2020, le=2030, description="Campaign year")


class UpdateCampaignRequest(BaseModel):
    """Request schema for updating an existing campaign."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Campaign name")
    seasonal_event: Optional[str] = Field(None, min_length=1, max_length=100, description="Seasonal event")
    year: Optional[int] = Field(None, ge=2020, le=2030, description="Campaign year")
    duration: Optional[int] = Field(None, description="Video duration in seconds")
    scene_configs: Optional[List[SceneConfigSchema]] = Field(None, description="Array of scene configurations")

    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        """Validate duration is one of the allowed values."""
        if v is not None and v not in [15, 30, 45, 60]:
            raise ValueError('Duration must be 15, 30, 45, or 60 seconds')
        return v


class CampaignResponse(BaseModel):
    """Response schema for campaign data.

    Campaigns are organizational containers. Video-specific fields
    (duration, scene_configs) are optional and primarily used per-creative.
    """
    id: UUID
    product_id: UUID
    name: str
    seasonal_event: str
    year: int
    display_name: str
    duration: Optional[int] = 30
    scene_configs: Optional[List[Dict[str, Any]]] = []
    status: str
    progress: int = 0
    campaign_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedCampaigns(BaseModel):
    """Paginated list of campaigns."""
    campaigns: List[CampaignResponse]
    total: int
    page: int
    limit: int
    pages: int


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


class AdCampaign(BaseModel):
    """Complete ad campaign configuration stored in database JSON field."""
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
    video_metadata: Optional[Dict[str, Any]] = None  # For storing additional metadata like selectedStyle


# ============================================================================
# Provider Health Check Schemas
# ============================================================================

class ProviderHealthStatus(BaseModel):
    """Health status for a single video generation provider."""
    provider: str = Field(..., description="Provider name (replicate or ecs)")
    healthy: bool = Field(..., description="Whether provider is currently healthy")
    message: str = Field(..., description="Human-readable status message")
    endpoint: Optional[str] = Field(None, description="Provider endpoint URL (if applicable)")

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "ecs",
                "healthy": True,
                "message": "Operational",
                "endpoint": "http://internal-adgen-ecs-alb-123.us-east-1.elb.amazonaws.com"
            }
        }


class ProvidersHealthResponse(BaseModel):
    """Health status response for all video generation providers."""
    replicate: ProviderHealthStatus
    ecs: ProviderHealthStatus

    class Config:
        json_schema_extra = {
            "example": {
                "replicate": {
                    "provider": "replicate",
                    "healthy": True,
                    "message": "Always available"
                },
                "ecs": {
                    "provider": "ecs",
                    "healthy": True,
                    "message": "Operational",
                    "endpoint": "http://internal-adgen-ecs-alb-123.us-east-1.elb.amazonaws.com"
                }
            }
        }


# ============================================================================
# Additional Schema Aliases (for backward compatibility)
# ============================================================================
# Product aliases
ProductDetail = ProductResponse
ProductCreate = CreateProductRequest

# Campaign aliases
CampaignDetail = CampaignResponse
CampaignDetailResponse = CampaignResponse  # Alias for backward compatibility
CampaignCreate = CreateCampaignRequest
