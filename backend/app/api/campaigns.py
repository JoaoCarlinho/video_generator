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
from app.api.auth import get_current_brand_id, get_current_user_id, verify_perfume_ownership, verify_campaign_ownership
from app.models.schemas import CampaignDetail, PaginatedCampaigns, CampaignStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedCampaigns,
    summary="List campaigns",
    description="Get paginated list of campaigns for a product. Verifies product ownership."
)
async def list_campaigns(
    product_id: UUID = Query(..., description="Product ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> PaginatedCampaigns:
    """
    Get paginated list of campaigns for a product.

    **Query Parameters:**
    - `product_id`: Product UUID (required)
    - `page`: Page number (default: 1)
    - `limit`: Items per page (default: 20, max: 100)

    **Returns:**
    - PaginatedCampaigns: Paginated list with total count

    **Raises:**
    - HTTPException 404: Product not found or doesn't belong to brand
    """
    try:
        # Verify product belongs to brand
        verify_perfume_ownership(product_id, brand_id, db)

        # Get campaigns for product
        campaigns, total = crud.get_campaigns_by_product(db, product_id, page, limit)
        
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
        
        # Log campaign_json for debugging
        logger.info(f"🔍 Campaign {campaign_id} campaign_json type: {type(campaign.campaign_json)}")
        logger.info(f"🔍 Campaign {campaign_id} campaign_json value: {campaign.campaign_json}")
        if isinstance(campaign.campaign_json, dict):
            logger.info(f"🔍 Campaign {campaign_id} variationPaths: {campaign.campaign_json.get('variationPaths', 'NOT FOUND')}")
        
        # Note: We no longer replace S3 URLs with backend proxy URLs
        # The S3 URLs are presigned and should work directly from the frontend.
        # This avoids issues where <video src="..."> requests don't send auth headers
        # and thus fail against the protected backend proxy endpoint.
        
        campaign_detail = CampaignDetail.model_validate(campaign)
        
        logger.info(f"🔍 CampaignDetail campaign_json type: {type(campaign_detail.campaign_json)}")
        logger.info(f"🔍 CampaignDetail campaign_json value: {campaign_detail.campaign_json}")
        
        return campaign_detail
    
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
    user_id: UUID = Depends(get_current_user_id),
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

        # Delete campaign (validates user owns the campaign via product/brand)
        deleted = crud.delete_campaign(db, user_id, campaign_id)
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

