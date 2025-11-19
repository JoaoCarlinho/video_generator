"""API endpoints for brand management."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import logging

from app.database.connection import get_db
from app.database.crud import (
    create_brand,
    get_user_brands,
    get_brand,
    update_brand,
    delete_brand
)
from app.models.schemas import (
    CreateBrandRequest,
    UpdateBrandRequest,
    BrandResponse
)
from app.api.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Brand Endpoints
# ============================================================================

@router.post("/", response_model=BrandResponse, status_code=201)
async def create_brand_endpoint(
    request: CreateBrandRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Create a new brand for the authenticated user.

    **Request Body:**
    ```json
    {
        "company_name": "Acme Corp",
        "brand_name": "Acme",
        "description": "Leading provider of...",
        "guidelines": "Brand voice is professional...",
        "logo_urls": {"urls": ["https://s3.../logo.png"]}
    }
    ```

    **Response:** BrandResponse with created brand data

    **Errors:**
    - 401: Not authenticated
    - 400: Invalid request data
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Create brand
        brand = create_brand(
            db=db,
            user_id=user_id,
            company_name=request.company_name,
            brand_name=request.brand_name,
            description=request.description,
            guidelines=request.guidelines,
            logo_urls=request.logo_urls
        )

        logger.info(f"✅ Created brand {brand.id} for user {user_id}")

        return brand

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create brand: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create brand: {str(e)}")


@router.get("/", response_model=List[BrandResponse])
async def list_brands_endpoint(
    db: Session = Depends(get_db),
    authorization: str = Header(None),
    limit: int = 50,
    offset: int = 0
):
    """
    Get all brands for the authenticated user.

    **Query Parameters:**
    - limit: Maximum number of brands to return (default: 50)
    - offset: Number of brands to skip for pagination (default: 0)

    **Response:** List of BrandResponse objects

    **Errors:**
    - 401: Not authenticated
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Get user's brands
        brands = get_user_brands(db=db, user_id=user_id, limit=limit, offset=offset)

        logger.info(f"✅ Retrieved {len(brands)} brands for user {user_id}")

        return brands

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to list brands: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list brands: {str(e)}")


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand_endpoint(
    brand_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Get a single brand by ID (ownership verified).

    **Path Parameters:**
    - brand_id: UUID of the brand

    **Response:** BrandResponse with brand data

    **Errors:**
    - 401: Not authenticated
    - 404: Brand not found or not owned by user
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Get brand with ownership check
        brand = get_brand(db=db, brand_id=brand_id, user_id=user_id)

        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")

        logger.info(f"✅ Retrieved brand {brand_id} for user {user_id}")

        return brand

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get brand {brand_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get brand: {str(e)}")


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand_endpoint(
    brand_id: UUID,
    request: UpdateBrandRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Update a brand (only if owned by user).

    **Path Parameters:**
    - brand_id: UUID of the brand to update

    **Request Body:** Partial update - only include fields to change
    ```json
    {
        "company_name": "New Name",
        "description": "Updated description"
    }
    ```

    **Response:** BrandResponse with updated brand data

    **Errors:**
    - 401: Not authenticated
    - 404: Brand not found or not owned by user
    - 400: Invalid request data
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Prepare update dict (only include fields that were provided)
        updates = request.dict(exclude_unset=True)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update brand with ownership check
        brand = update_brand(
            db=db,
            brand_id=brand_id,
            user_id=user_id,
            **updates
        )

        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")

        logger.info(f"✅ Updated brand {brand_id} for user {user_id}")

        return brand

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update brand {brand_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update brand: {str(e)}")


@router.delete("/{brand_id}", status_code=204)
async def delete_brand_endpoint(
    brand_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Delete a brand (only if owned by user). CASCADE deletes all associated products.

    **Path Parameters:**
    - brand_id: UUID of the brand to delete

    **Response:** 204 No Content on success

    **Errors:**
    - 401: Not authenticated
    - 404: Brand not found or not owned by user
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Delete brand with ownership check
        deleted = delete_brand(db=db, brand_id=brand_id, user_id=user_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Brand not found")

        logger.info(f"✅ Deleted brand {brand_id} for user {user_id}")

        # Return 204 No Content
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete brand {brand_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete brand: {str(e)}")
