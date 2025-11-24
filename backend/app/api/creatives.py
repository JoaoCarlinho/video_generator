"""
Creative API endpoints.
Handles creative CRUD operations within campaigns.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.database.connection import get_db
from app.database import crud
from app.api.auth import get_current_user_id, verify_campaign_ownership
from app.models.schemas import CampaignStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class CreateCreativeRequest(BaseModel):
    """Request schema for creating a creative."""
    title: str = Field(..., min_length=1, max_length=200)
    brief: Optional[str] = None
    brand_name: str
    product_name: str
    mood: Optional[str] = "uplifting"
    duration: Optional[int] = 30
    aspect_ratio: Optional[str] = "9:16"
    product_image_url: Optional[str] = None
    productImages: Optional[List[str]] = None
    sceneBackgrounds: Optional[List[Dict[str, Any]]] = None
    outputFormats: Optional[List[str]] = None
    output_formats: Optional[List[str]] = None
    logo_url: Optional[str] = None
    guidelines_url: Optional[str] = None
    creative_prompt: Optional[str] = None
    brand_description: Optional[str] = None
    target_audience: Optional[str] = None
    target_duration: Optional[int] = 30
    selected_style: Optional[str] = None
    video_provider: Optional[str] = "replicate"
    product_gender: Optional[str] = None
    num_variations: Optional[int] = 1


class CreativeResponse(BaseModel):
    """Response schema for a creative."""
    id: UUID
    campaign_id: UUID
    user_id: UUID
    title: str
    ad_creative_json: Dict[str, Any]
    status: str
    progress: int
    cost: float
    error_message: Optional[str] = None
    aspect_ratio: str
    video_provider: str
    output_formats: Optional[List[str]] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PaginatedCreatives(BaseModel):
    """Paginated creatives response."""
    creatives: List[CreativeResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Creative Endpoints
# ============================================================================

@router.get(
    "/{campaign_id}/creatives",
    response_model=PaginatedCreatives,
    summary="List creatives for campaign",
    description="Get all creatives for a specific campaign"
)
async def list_creatives(
    campaign_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List all creatives for a campaign.

    **Path Parameters:**
    - `campaign_id`: Campaign UUID

    **Query Parameters:**
    - `limit`: Maximum number of creatives to return (1-100, default: 20)
    - `offset`: Number of creatives to skip (default: 0)

    **Returns:**
    - Paginated list of creatives
    """
    try:
        creatives, total = crud.get_creatives_for_campaign(
            db,
            campaign_id=campaign_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        # Convert to response format
        creative_responses = []
        for creative in creatives:
            creative_responses.append(CreativeResponse(
                id=creative.id,
                campaign_id=creative.campaign_id,
                user_id=creative.user_id,
                title=creative.title,
                ad_creative_json=creative.ad_creative_json,
                status=creative.status,
                progress=creative.progress,
                cost=float(creative.cost),
                error_message=creative.error_message,
                aspect_ratio=creative.aspect_ratio,
                video_provider=creative.video_provider,
                output_formats=creative.output_formats,
                created_at=creative.created_at.isoformat(),
                updated_at=creative.updated_at.isoformat()
            ))

        return PaginatedCreatives(
            creatives=creative_responses,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"❌ Failed to list creatives for campaign {campaign_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list creatives: {str(e)}"
        )


@router.post(
    "/{campaign_id}/creatives",
    response_model=CreativeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create creative",
    description="Create a new creative for a campaign"
)
async def create_creative(
    campaign_id: UUID,
    creative_data: CreateCreativeRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create a new creative for a campaign.

    **Path Parameters:**
    - `campaign_id`: Campaign UUID

    **Request Body:**
    - Creative configuration including title, brief, settings, etc.

    **Returns:**
    - Created creative object
    """
    try:
        # Build ad_creative_json from request data
        ad_creative_json = {
            "brief": creative_data.brief or "",
            "brand_name": creative_data.brand_name,
            "product_name": creative_data.product_name,
            "mood": creative_data.mood or "uplifting",
            "duration": creative_data.duration or 30,
            "creative_prompt": creative_data.creative_prompt,
            "brand_description": creative_data.brand_description,
            "target_audience": creative_data.target_audience,
            "selected_style": creative_data.selected_style,
            "product_gender": creative_data.product_gender,
            "num_variations": creative_data.num_variations or 1,
            "productImages": creative_data.productImages or [],
            "sceneBackgrounds": creative_data.sceneBackgrounds or [],
        }

        # Determine output formats
        output_formats = (
            creative_data.output_formats or
            creative_data.outputFormats or
            [creative_data.aspect_ratio or "9:16"]
        )

        # Create creative
        creative = crud.create_creative(
            db=db,
            campaign_id=campaign_id,
            user_id=user_id,
            title=creative_data.title,
            ad_creative_json=ad_creative_json,
            status="pending",
            aspect_ratio=creative_data.aspect_ratio or "9:16",
            video_provider=creative_data.video_provider or "replicate",
            output_formats=output_formats
        )

        if not creative:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create creative for this campaign"
            )

        logger.info(f"✅ Created creative {creative.id} for campaign {campaign_id}")

        return CreativeResponse(
            id=creative.id,
            campaign_id=creative.campaign_id,
            user_id=creative.user_id,
            title=creative.title,
            ad_creative_json=creative.ad_creative_json,
            status=creative.status,
            progress=creative.progress,
            cost=float(creative.cost),
            error_message=creative.error_message,
            aspect_ratio=creative.aspect_ratio,
            video_provider=creative.video_provider,
            output_formats=creative.output_formats,
            created_at=creative.created_at.isoformat(),
            updated_at=creative.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create creative: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create creative: {str(e)}"
        )


@router.get(
    "/{campaign_id}/creatives/{creative_id}",
    response_model=CreativeResponse,
    summary="Get creative",
    description="Get a specific creative by ID"
)
async def get_creative(
    campaign_id: UUID,
    creative_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get a specific creative.

    **Path Parameters:**
    - `campaign_id`: Campaign UUID
    - `creative_id`: Creative UUID

    **Returns:**
    - Creative object
    """
    try:
        creative = crud.get_creative_by_id(db, creative_id)

        if not creative or creative.campaign_id != campaign_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Creative not found"
            )

        # Verify ownership
        if creative.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this creative"
            )

        return CreativeResponse(
            id=creative.id,
            campaign_id=creative.campaign_id,
            user_id=creative.user_id,
            title=creative.title,
            ad_creative_json=creative.ad_creative_json,
            status=creative.status,
            progress=creative.progress,
            cost=float(creative.cost),
            error_message=creative.error_message,
            aspect_ratio=creative.aspect_ratio,
            video_provider=creative.video_provider,
            output_formats=creative.output_formats,
            created_at=creative.created_at.isoformat(),
            updated_at=creative.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get creative {creative_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get creative: {str(e)}"
        )


@router.delete(
    "/{campaign_id}/creatives/{creative_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete creative",
    description="Delete a creative"
)
async def delete_creative(
    campaign_id: UUID,
    creative_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Delete a creative.

    **Path Parameters:**
    - `campaign_id`: Campaign UUID
    - `creative_id`: Creative UUID
    """
    try:
        deleted = crud.delete_creative(
            db=db,
            campaign_id=campaign_id,
            creative_id=creative_id,
            user_id=user_id
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Creative not found or not authorized"
            )

        logger.info(f"✅ Deleted creative {creative_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete creative {creative_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete creative: {str(e)}"
        )
