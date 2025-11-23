"""API endpoints for campaign management."""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
import logging

from app.database.connection import get_db, init_db
from app.database.crud import (
    create_campaign,
    get_campaign,
    get_campaign_by_user,
    get_user_campaigns,
    update_campaign,
    update_campaign_s3_paths,
    update_campaign_status,
    delete_campaign,
    get_generation_stats
)
from app.models.schemas import (
    CreateCampaignRequest,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignListResponse,
    ErrorResponse
)
from app.api.auth import get_current_user_id
from app.utils.s3_utils import create_campaign_folder_structure, delete_campaign_folder
from app.services.style_manager import StyleManager

logger = logging.getLogger(__name__)

router = APIRouter(redirect_slashes=False)


# Note: get_current_user_id imported from app.api.auth


# ============================================================================
# CREATE Endpoints
# ============================================================================

@router.post("/", response_model=CampaignResponse)
async def create_new_campaign(
    request: CreateCampaignRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Create a new luxury perfume TikTok ad campaign.
    
    Logs request data for debugging validation errors.
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Request Body:**
    - title: Campaign title (max 200 chars)
    - creative_prompt: User's creative vision for the perfume ad (20-3000 chars)
    - target_duration: Target video duration (15-60 seconds for TikTok)
    - brand_name: Brand name (max 100 chars)
    - brand_description: (optional) Brand story, values, personality
    - target_audience: (optional) Target audience description
    - perfume_name: Product product name (required, e.g., "Noir Élégance")
    - perfume_gender: Product gender - 'masculine', 'feminine', or 'unisex' (default: 'unisex')
    - logo_url: (optional) S3 URL of uploaded brand logo
    - product_image_url: (optional) S3 URL of uploaded perfume bottle image
    - guidelines_url: (optional) S3 URL of uploaded brand guidelines
    - selected_style: (optional) Product video style - 'gold_luxe', 'dark_elegance', or 'romantic_floral'
    - num_variations: (optional) Number of video variations to generate (1-3, default: 1)
    
    **Note:** Aspect ratio is hardcoded to 9:16 (TikTok vertical, 1080x1920) for all perfume ads.
    
    **Response:** CampaignResponse with newly created campaign
    
    **Errors:**
    - 400: Invalid input (validation errors)
    - 401: Missing or invalid authorization
    - 500: Database error
    
    **Example:**
    ```json
    {
      "title": "Chanel Noir TikTok Ad",
      "creative_prompt": "Create a mysterious luxury perfume ad for our new noir fragrance. Start with dramatic bottle reveal, show elegant textures, end with brand moment.",
      "target_duration": 30,
      "brand_name": "Chanel",
      "brand_description": "Luxury French perfume house",
      "target_audience": "Sophisticated adults 30-50",
      "perfume_name": "Noir Élégance",
      "perfume_gender": "masculine",
      "selected_style": "dark_elegance"
    }
    ```
    """
    try:
        # Log request data for debugging
        logger.info(f"Creating campaign with data: title={request.title}, brand_name={request.brand_name}, perfume_name={request.perfume_name}, creative_prompt length={len(request.creative_prompt) if request.creative_prompt else 0}")
        
        # Validate required fields
        if not request.perfume_name or not request.perfume_name.strip():
            logger.error("perfume_name is required but missing or empty")
            raise HTTPException(status_code=422, detail="perfume_name is required")
        
        if not request.creative_prompt or len(request.creative_prompt.strip()) < 20:
            logger.error(f"creative_prompt validation failed: length={len(request.creative_prompt) if request.creative_prompt else 0}")
            raise HTTPException(status_code=422, detail="creative_prompt must be at least 20 characters")
        
        # Initialize database if needed
        init_db()

        # Validate ECS provider availability if selected
        from app.config import settings
        if request.video_provider == "ecs":
            if not settings.ecs_provider_enabled:
                logger.warning(f"ECS provider requested but not configured")
                raise HTTPException(
                    status_code=400,
                    detail="ECS provider not available. Use 'replicate' or configure ECS endpoint."
                )

        # Get current user from auth
        user_id = get_current_user_id(authorization)
        
        # Create brand config
        brand_config = {
            "name": request.brand_name,
            "description": request.brand_description,
            "font_family": "Inter",
            "logo_url": request.logo_url,
            "guidelines_url": request.guidelines_url
        }
        
        # Create product asset if product image URL provided
        product_asset = None
        if request.product_image_url:
            product_asset = {
                "original_url": request.product_image_url,
                "masked_png_url": None,
                "mask_url": None,
                "width": None,
                "height": None,
                "extracted_at": None
            }
        
        # STORY 3: Handle multiple product images (backward compatible)
        product_images_list = request.product_images or []
        if not product_images_list and request.product_image_url:
            # Backward compatibility: convert single image to array
            product_images_list = [request.product_image_url]

        # STORY 3: Handle scene backgrounds
        scene_backgrounds_list = []
        if request.scene_backgrounds:
            scene_backgrounds_list = [
                {"scene_id": sb.scene_id, "background_url": sb.background_url}
                for sb in request.scene_backgrounds
            ]

        # STORY 3: Handle output formats (multiple aspect ratios)
        output_formats_list = request.output_formats or ["16:9"]

        # PHASE 7: Add style configuration if provided
        selected_style_config = None
        if request.selected_style:
            selected_style_config = {
                "style": request.selected_style,
                "display_name": StyleManager.get_style_display_name(request.selected_style),
                "applied_at": datetime.utcnow().isoformat(),
                "source": "user_selected"
            }
        
        # Create initial ad_campaign_json
        ad_campaign_json = {
            "version": "1.0",
            "creative_prompt": request.creative_prompt,
            "target_duration": request.target_duration,
            "target_audience": request.target_audience,
            "brand": brand_config,
            "product_asset": product_asset,
            # STORY 3: New fields
            "product_images": product_images_list,
            "scene_backgrounds": scene_backgrounds_list,
            "output_formats": output_formats_list,
            # WAN 2.5: Video provider selection
            "video_provider": request.video_provider,
            # Continue with existing fields
            "product_name": request.product_name,  # Phase 9: Product product name
            "product_gender": request.product_gender,  # Phase 9: Product gender\
            "selectedStyle": selected_style_config,  # PHASE 7: User-selected or LLM-inferred style
            "style_spec": None,
            "scenes": [],
            "video_settings": {
                "aspect_ratio": request.aspect_ratio,  # Kept for backward compat
                "resolution": "1080p",
                "platform": "tiktok",  # Phase 9: Platform identifier
                "fps": 30,
                "codec": "h264"
            },
            "audio_settings": {
                "include_music": True,
                "music_volume": -6.0,
                "enable_voiceover": False
            },
            "render_status": None
        }
        
        # Create campaign in database
        campaign = create_campaign(
            db=db,
            user_id=user_id,
            title=request.title,
            brief=request.creative_prompt,  # Store creative_prompt as brief in DB for backwards compat
            ad_campaign_json=ad_campaign_json,
            mood="",  # Deprecated, keeping for DB schema compatibility
            duration=request.target_duration,
            aspect_ratio=request.aspect_ratio,  # Deprecated but kept for backward compat
            # STORY 3: Pass new multi-format fields
            product_images=product_images_list,
            scene_backgrounds=scene_backgrounds_list,
            output_formats=output_formats_list,
            selected_style=request.selected_style,  # PHASE 7: Store selected style
            product_name=request.product_name,  # Phase 9: Store product name
            product_gender=request.product_gender,  # Phase 9: Store product gender
            num_variations=request.num_variations  # MULTI-VARIATION: Store variation count
        )
        
        # S3 RESTRUCTURING: Initialize S3 folder structure for new campaign
        try:
            folders = await create_campaign_folder_structure(str(campaign.id))
            # Note: update_campaign_s3_paths is NOT async, don't await it
            update_campaign_s3_paths(
                db,
                campaign.id,
                folders["s3_folder"],
                folders["s3_url"]
            )
            logger.info(f"✅ Created campaign {campaign.id} with S3 folders at {folders['s3_url']}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize S3 folders for {campaign.id}: {e}")
            # Continue anyway - campaign created, S3 will be initialized during generation
        
        # Convert campaign to response - handle both DB and mock campaigns
        return CampaignResponse.model_validate({
            "id": campaign.id,
            "user_id": campaign.user_id,
            "title": campaign.title,
            "status": campaign.status,
            "progress": campaign.progress,
            "cost": float(campaign.cost) if campaign.cost else 0.0,
            "aspect_ratio": getattr(campaign, 'aspect_ratio', '9:16'),  # Phase 9: Default to 9:16
            "created_at": campaign.created_at,
            "updated_at": campaign.updated_at,
        })
    
    except Exception as e:
        logger.error(f"❌ Failed to create campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")


# ============================================================================
# READ Endpoints
# ============================================================================

@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign_details(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Get detailed information about a specific campaign.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** CampaignDetailResponse with full configuration
    
    **Errors:**
    - 404: Campaign not found
    - 403: Not authorized to view this campaign
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get campaign and verify ownership
        campaign = get_campaign_by_user(db, campaign_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return CampaignDetailResponse.model_validate(campaign)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaign: {str(e)}")


@router.get("/", response_model=CampaignListResponse)
async def list_user_campaigns(
    limit: int = Query(50, ge=1, le=100, description="Max campaigns to return"),
    offset: int = Query(0, ge=0, description="Number of campaigns to skip"),
    status: str = Query(None, description="Filter by status (optional)"),
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    List all campaigns for the current user with pagination.
    
    **Query Parameters:**
    - limit: Maximum number of campaigns (1-100, default 50)
    - offset: Number of campaigns to skip (default 0)
    - status: (optional) Filter by status (PENDING, QUEUED, EXTRACTING_PRODUCT, PLANNING, GENERATING_SCENES, COMPOSITING, ADDING_OVERLAYS, GENERATING_AUDIO, RENDERING, COMPLETED, FAILED)
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** CampaignListResponse with list of campaigns
    
    **Errors:**
    - 400: Invalid query parameters
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get campaigns
        campaigns = get_user_campaigns(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status
        )
        
        # Count total (for pagination info)
        total = len(campaigns)  # In production, use a separate count query
        
        # Convert campaigns to response - handle both DB and mock campaigns
        response_campaigns = [
            CampaignResponse.model_validate({
                "id": p.id,
                "user_id": p.user_id,
                "title": p.title,
                "status": p.status,
                "progress": p.progress,
                "cost": float(p.cost) if p.cost else 0.0,
                "aspect_ratio": getattr(p, 'aspect_ratio', '9:16'),  # Phase 9: Default to 9:16
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            })
            for p in campaigns
        ]
        
        return CampaignListResponse(
            total=total,
            limit=limit,
            offset=offset,
            campaigns=response_campaigns
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to list campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list campaigns: {str(e)}")


@router.get("/stats/summary", response_model=dict)
async def get_user_stats(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Get generation statistics for the current user.
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:**
    ```json
    {
      "total_campaigns": 10,
      "completed": 8,
      "failed": 1,
      "in_progress": 1,
      "total_cost": 8.50,
      "success_rate": 80.0
    }
    ```
    
    **Errors:**
    - 401: Missing or invalid authorization
    - 500: Database error
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        stats = get_generation_stats(db, user_id)
        
        return stats
    
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ============================================================================
# STYLE Endpoints (Phase 7)
# ============================================================================

@router.get("/styles/available", response_model=dict)
async def get_available_styles():
    """
    Get all available product video styles for UI selection.
    
    **Response:**
    ```json
    {
      "styles": [
        {
          "id": "gold_luxe",
          "name": "Gold Luxe",
          "description": "Warm golden lighting, rich textures, opulent feel",
          "short_description": "Luxurious, warm",
          "examples": ["Chanel", "Dior", "Tom Ford"],
          "keywords": ["luxury", "gold", "warm", "opulent"],
          "best_for": ["High-end perfumes", "Premium fragrances", "Luxury brands"]
        },
        {
          "id": "dark_elegance",
          "name": "Dark Elegance",
          "description": "Black background, dramatic rim lighting, mysterious",
          "short_description": "Mysterious, sophisticated",
          "examples": ["Yves Saint Laurent", "Versace", "Armani"],
          "keywords": ["dark", "elegant", "mysterious", "dramatic"],
          "best_for": ["Masculine fragrances", "Exclusive perfumes", "Evening scents"]
        },
        {
          "id": "romantic_floral",
          "name": "Romantic Floral",
          "description": "Soft pastels, floral elements, feminine aesthetic",
          "short_description": "Romantic, delicate",
          "examples": ["Marc Jacobs", "Viktor & Rolf", "Valentino"],
          "keywords": ["romantic", "floral", "feminine", "delicate"],
          "best_for": ["Feminine fragrances", "Floral perfumes", "Spring/Summer scents"]
        }
      ]
    }
    ```
    
    **Errors:**
    - 500: Server error
    """
    try:
        styles = StyleManager.get_all_styles()
        return {"styles": styles}
    except Exception as e:
        logger.error(f"❌ Failed to get available styles: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get styles: {str(e)}")


# ============================================================================
# UPDATE Endpoints
# ============================================================================

@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign_details(
    campaign_id: UUID,
    request: dict,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Update campaign details (title, brief, etc).
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Request Body:**
    - Flexible: any campaign fields to update
    
    **Response:** Updated CampaignResponse
    
    **Errors:**
    - 404: Campaign not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Verify ownership
        campaign = get_campaign_by_user(db, campaign_id, user_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Update campaign
        updated = update_campaign(db, campaign_id, **request)
        
        if not updated:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return CampaignResponse.model_validate(updated)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update campaign: {str(e)}")


# ============================================================================
# DELETE Endpoints
# ============================================================================

@router.delete("/{campaign_id}")
async def delete_campaign_endpoint(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Delete a campaign (only if owned by current user).
    
    Also deletes all S3 files associated with the campaign.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign to delete
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** {"status": "deleted", "campaign_id": "...", "s3_cleaned": true/false}
    
    **Errors:**
    - 404: Campaign not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get campaign to retrieve S3 folder path
        campaign = get_campaign_by_user(db, campaign_id, user_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found or not authorized")
        
        # S3 RESTRUCTURING: Delete S3 folder and all contents
        s3_cleaned = False
        if campaign.s3_campaign_folder:
            try:
                s3_cleaned = await delete_campaign_folder(str(campaign_id))
                if s3_cleaned:
                    logger.info(f"✅ Deleted S3 folder: {campaign.s3_campaign_folder}")
                else:
                    logger.warning(f"⚠️ Partial S3 cleanup for {campaign_id}")
            except Exception as e:
                logger.error(f"⚠️ S3 cleanup error (non-critical): {e}")
                # Continue with database deletion anyway
        
        # Delete campaign from database
        success = delete_campaign(db, campaign_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Campaign not found or not authorized")
        
        return {
            "status": "deleted",
            "campaign_id": str(campaign_id),
            "s3_cleaned": s3_cleaned
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")



