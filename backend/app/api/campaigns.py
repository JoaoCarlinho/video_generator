"""
Campaign API endpoints for B2B SaaS transformation.
Handles campaign CRUD operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Optional

from app.database.connection import get_db
from app.database import crud
from app.api.auth import get_current_brand_id, verify_perfume_ownership, verify_campaign_ownership
from app.models.schemas import CampaignDetail, CampaignCreate, PaginatedCampaigns, CampaignStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=CampaignDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create campaign",
    description="Create a new campaign for a perfume. Verifies perfume ownership."
)
async def create_campaign(
    data: CampaignCreate,
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> CampaignDetail:
    """
    Create a new campaign for a perfume.
    
    **Request Body:**
    - `perfume_id`: Perfume UUID (required)
    - `campaign_name`: Campaign name (2-200 chars, unique within perfume)
    - `creative_prompt`: Creative prompt (10-2000 chars)
    - `selected_style`: Video style ('gold_luxe', 'dark_elegance', 'romantic_floral')
    - `target_duration`: Target duration in seconds (15-60)
    - `num_variations`: Number of variations (1-3, default: 1)
    
    **Returns:**
    - CampaignDetail: Created campaign with all details
    
    **Raises:**
    - HTTPException 400: Invalid input data
    - HTTPException 404: Perfume not found or doesn't belong to brand
    - HTTPException 409: Campaign name already exists for this perfume
    """
    try:
        # Verify perfume belongs to brand
        verify_perfume_ownership(data.perfume_id, brand_id, db)
        
        # Check campaign name uniqueness within perfume
        existing_campaigns, _ = crud.get_campaigns_by_perfume(db, data.perfume_id, page=1, limit=1000)
        for existing in existing_campaigns:
            if existing.campaign_name == data.campaign_name:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Campaign name '{data.campaign_name}' already exists for this perfume"
                )
        
        # Create campaign
        logger.info(f"💾 Creating campaign '{data.campaign_name}' for perfume {data.perfume_id}")
        campaign = crud.create_campaign(
            db=db,
            perfume_id=data.perfume_id,
            brand_id=brand_id,
            campaign_name=data.campaign_name,
            creative_prompt=data.creative_prompt,
            selected_style=data.selected_style.value,
            target_duration=data.target_duration,
            num_variations=data.num_variations
        )
        
        logger.info(f"✅ Campaign created: {campaign.campaign_id}")
        return CampaignDetail.model_validate(campaign)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create campaign: {str(e)}"
        )


@router.get(
    "",
    response_model=PaginatedCampaigns,
    summary="List campaigns",
    description="Get paginated list of campaigns for a perfume. Verifies perfume ownership."
)
async def list_campaigns(
    perfume_id: UUID = Query(..., description="Perfume ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> PaginatedCampaigns:
    """
    Get paginated list of campaigns for a perfume.
    
    **Query Parameters:**
    - `perfume_id`: Perfume UUID (required)
    - `page`: Page number (default: 1)
    - `limit`: Items per page (default: 20, max: 100)
    
    **Returns:**
    - PaginatedCampaigns: Paginated list with total count
    
    **Raises:**
    - HTTPException 404: Perfume not found or doesn't belong to brand
    """
    try:
        # Verify perfume belongs to brand
        verify_perfume_ownership(perfume_id, brand_id, db)
        
        # Get campaigns for perfume
        campaigns, total = crud.get_campaigns_by_perfume(db, perfume_id, page, limit)
        
        # Convert to response models
        campaign_details = [CampaignDetail.model_validate(c) for c in campaigns]
        
        pages = (total + limit - 1) // limit  # Ceiling division
        
        return PaginatedCampaigns(
            campaigns=campaign_details,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to list campaigns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve campaigns"
        )


@router.get(
    "/{campaign_id}",
    response_model=CampaignDetail,
    summary="Get campaign",
    description="Get campaign details by ID. Verifies campaign ownership."
)
async def get_campaign(
    campaign_id: UUID,
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
) -> CampaignDetail:
    """
    Get campaign details by ID.
    
    **Path Parameters:**
    - `campaign_id`: Campaign UUID
    
    **Returns:**
    - CampaignDetail: Campaign details
    
    **Raises:**
    - HTTPException 404: Campaign not found or doesn't belong to brand
    """
    try:
        campaign = crud.get_campaign_by_id(db, campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        return CampaignDetail.model_validate(campaign)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve campaign"
        )


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete campaign",
    description="Delete a campaign. Only allowed if campaign is not processing."
)
async def delete_campaign(
    campaign_id: UUID,
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
):
    """
    Delete a campaign.
    
    **Path Parameters:**
    - `campaign_id`: Campaign UUID
    
    **Raises:**
    - HTTPException 400: Campaign is processing (cannot delete)
    - HTTPException 404: Campaign not found
    """
    try:
        campaign = crud.get_campaign_by_id(db, campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        # Check if campaign is processing
        if campaign.status == CampaignStatus.PROCESSING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete campaign while it is processing. Please wait for completion or failure."
            )
        
        # Delete campaign
        deleted = crud.delete_campaign(db, campaign_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete campaign"
            )
        
        logger.info(f"✅ Deleted campaign {campaign_id}")
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete campaign"
        )

