"""API endpoints for campaign management."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import logging

from app.database.connection import get_db
from app.database.crud import (
    create_campaign,
    get_product_campaigns,
    get_campaign,
    update_campaign,
    delete_campaign
)
from app.models.schemas import (
    CreateCampaignRequest,
    UpdateCampaignRequest,
    CampaignResponse
)
from app.api.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# Campaign Endpoints
# ============================================================================

@router.post("/products/{product_id}/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign_endpoint(
    product_id: UUID,
    request: CreateCampaignRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Create a new campaign associated with a product.

    **Path Parameters:**
    - product_id: UUID of the product to associate campaign with

    **Request Body:**
    ```json
    {
        "name": "Summer Launch",
        "seasonal_event": "Summer Sale",
        "year": 2025,
        "duration": 30,
        "scene_configs": [
            {
                "scene_number": 1,
                "creative_vision": "Energetic professional in modern kitchen...",
                "reference_images": ["https://s3.../theme.jpg", "https://s3.../start.jpg", "https://s3.../end.jpg"],
                "cinematography": {
                    "camera_aspect": "POV",
                    "lighting": "natural",
                    "mood": "energetic",
                    "transition": "fade",
                    "environment": "bright",
                    "setting": "residential"
                }
            }
        ]
    }
    ```

    **Response:** CampaignResponse with created campaign data

    **Errors:**
    - 401: Not authenticated
    - 404: Product not found or not owned by user
    - 422: Invalid scene configuration or duration
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Convert scene configs to dicts
        scene_configs_dicts = [scene.model_dump() for scene in request.scene_configs]

        # Create campaign (validates product ownership)
        campaign = create_campaign(
            db=db,
            user_id=user_id,
            product_id=product_id,
            name=request.name,
            seasonal_event=request.seasonal_event,
            year=request.year,
            duration=request.duration,
            scene_configs=scene_configs_dicts
        )

        if not campaign:
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_id} not found or not owned by user"
            )

        logger.info(f"✅ Created campaign {campaign.id} for product {product_id}")

        # Build response with display_name
        response = CampaignResponse(
            id=campaign.id,
            product_id=campaign.product_id,
            name=campaign.name,
            seasonal_event=campaign.seasonal_event,
            year=campaign.year,
            display_name=campaign.display_name,
            duration=campaign.duration,
            scene_configs=campaign.scene_configs,
            status=campaign.status,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")


@router.get("/products/{product_id}/campaigns", response_model=List[CampaignResponse])
async def list_product_campaigns_endpoint(
    product_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None),
    limit: int = 50,
    offset: int = 0
):
    """
    Get all campaigns for a specific product.

    **Path Parameters:**
    - product_id: UUID of the product

    **Query Parameters:**
    - limit: Maximum number of campaigns to return (default: 50)
    - offset: Number of campaigns to skip for pagination (default: 0)

    **Response:** Array of CampaignResponse objects

    **Errors:**
    - 401: Not authenticated
    - 404: Product not found or not owned by user
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Get campaigns (validates product ownership)
        campaigns = get_product_campaigns(
            db=db,
            user_id=user_id,
            product_id=product_id,
            limit=limit,
            offset=offset
        )

        if campaigns is None:
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_id} not found or not owned by user"
            )

        logger.info(f"✅ Retrieved {len(campaigns)} campaigns for product {product_id}")

        # Build responses with display_name
        responses = [
            CampaignResponse(
                id=c.id,
                product_id=c.product_id,
                name=c.name,
                seasonal_event=c.seasonal_event,
                year=c.year,
                display_name=c.display_name,
                duration=c.duration,
                scene_configs=c.scene_configs,
                status=c.status,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in campaigns
        ]

        return responses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaigns: {str(e)}")


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign_endpoint(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Get a single campaign by ID.

    **Path Parameters:**
    - campaign_id: UUID of the campaign

    **Response:** CampaignResponse with campaign data

    **Errors:**
    - 401: Not authenticated
    - 404: Campaign not found or not owned by user
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Get campaign (validates ownership)
        campaign = get_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id
        )

        if not campaign:
            raise HTTPException(
                status_code=404,
                detail=f"Campaign {campaign_id} not found or not owned by user"
            )

        logger.info(f"✅ Retrieved campaign {campaign_id}")

        # Build response with display_name
        response = CampaignResponse(
            id=campaign.id,
            product_id=campaign.product_id,
            name=campaign.name,
            seasonal_event=campaign.seasonal_event,
            year=campaign.year,
            display_name=campaign.display_name,
            duration=campaign.duration,
            scene_configs=campaign.scene_configs,
            status=campaign.status,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaign: {str(e)}")


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign_endpoint(
    campaign_id: UUID,
    request: UpdateCampaignRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Update an existing campaign (for auto-save).

    **Path Parameters:**
    - campaign_id: UUID of the campaign to update

    **Request Body:** UpdateCampaignRequest (all fields optional)

    **Response:** CampaignResponse with updated campaign data

    **Errors:**
    - 401: Not authenticated
    - 404: Campaign not found or not owned by user
    - 422: Invalid scene configuration or duration
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Build updates dict (only include provided fields)
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.seasonal_event is not None:
            updates['seasonal_event'] = request.seasonal_event
        if request.year is not None:
            updates['year'] = request.year
        if request.duration is not None:
            updates['duration'] = request.duration
        if request.scene_configs is not None:
            updates['scene_configs'] = [scene.model_dump() for scene in request.scene_configs]

        # Update campaign (validates ownership)
        campaign = update_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
            **updates
        )

        if not campaign:
            raise HTTPException(
                status_code=404,
                detail=f"Campaign {campaign_id} not found or not owned by user"
            )

        logger.info(f"✅ Updated campaign {campaign_id}")

        # Build response with display_name
        response = CampaignResponse(
            id=campaign.id,
            product_id=campaign.product_id,
            name=campaign.name,
            seasonal_event=campaign.seasonal_event,
            year=campaign.year,
            display_name=campaign.display_name,
            duration=campaign.duration,
            scene_configs=campaign.scene_configs,
            status=campaign.status,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update campaign: {str(e)}")


@router.delete("/campaigns/{campaign_id}", status_code=204)
async def delete_campaign_endpoint(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Delete a campaign.

    **Path Parameters:**
    - campaign_id: UUID of the campaign to delete

    **Response:** 204 No Content on success

    **Errors:**
    - 401: Not authenticated
    - 404: Campaign not found or not owned by user
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Delete campaign (validates ownership)
        success = delete_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Campaign {campaign_id} not found or not owned by user"
            )

        logger.info(f"✅ Deleted campaign {campaign_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")
