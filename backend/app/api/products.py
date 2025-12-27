"""API endpoints for product management."""

from fastapi import APIRouter, Depends, HTTPException, Header, File, UploadFile, Form
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
import logging

from app.database.connection import get_db
from app.database.crud import (
    create_product,
    get_brand_products,
    get_product,
    update_product,
    delete_product,
    create_campaign,
    get_campaigns_by_product
)
from app.models.schemas import (
    CreateProductRequest,
    UpdateProductRequest,
    ProductResponse,
    CampaignCreate,
    CampaignDetail
)
from app.api.auth import get_current_user_id, get_current_brand_id, verify_perfume_ownership
from app.services.storage import storage_service
from fastapi import status

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# Product Endpoints
# ============================================================================

@router.post(
    "/brands/{brand_id}/products",
    response_model=ProductResponse,
    status_code=201
)
async def create_product_endpoint(
    brand_id: UUID,
    product_name: str = Form(...),
    product_gender: Optional[str] = Form(None),
    product_type: str = Form("fragrance"),
    icp_segment: Optional[str] = Form(None),
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    top_image: Optional[UploadFile] = File(None),
    left_image: Optional[UploadFile] = File(None),
    right_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Create a new product with multipart/form-data file uploads.

    **Path Parameters:**
    - brand_id: UUID of the brand to associate product with

    **Form Data:**
    - product_name: Name of the product (required)
    - product_gender: Gender (masculine/feminine/unisex, optional)
    - product_type: Type of product (default: fragrance)
    - icp_segment: Target audience description (optional)
    - front_image: Front product image (required)
    - back_image: Back product image (optional)
    - top_image: Top product image (optional)
    - left_image: Left product image (optional)
    - right_image: Right product image (optional)

    **Response:** ProductResponse with created product data

    **Errors:**
    - 401: Not authenticated
    - 404: Brand not found or not owned by user
    - 400: Invalid request data
    - 500: Database error or S3 upload failure
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Collect images to upload
        images_to_upload = [
            ("front", front_image),
            ("back", back_image),
            ("top", top_image),
            ("left", left_image),
            ("right", right_image)
        ]

        # Upload images to S3
        image_urls = []
        for angle, image_file in images_to_upload:
            if image_file:
                # Read file content
                file_content = await image_file.read()

                # Upload to S3
                s3_url = await storage_service.upload_file(
                    file_content=file_content,
                    folder="products",
                    filename=image_file.filename or f"{angle}.jpg",
                    content_type=image_file.content_type or "image/jpeg",
                    user_id=str(user_id)
                )

                if s3_url:
                    image_urls.append(s3_url)
                else:
                    logger.warning(
                        f"⚠️ Failed to upload {angle} image for product"
                    )

        if not image_urls:
            raise HTTPException(
                status_code=400,
                detail="At least one product image must be uploaded"
            )

        # Create product (validates brand ownership)
        product = create_product(
            db=db,
            user_id=user_id,
            brand_id=brand_id,
            product_type=product_type,
            name=product_name,
            product_gender=product_gender,
            icp_segment=icp_segment,
            image_urls=image_urls
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Brand {brand_id} not found or not owned by user"
            )

        logger.info(
            f"✅ Created product {product.id} for brand {brand_id}"
        )

        return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create product: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create product: {str(e)}"
        )


@router.post(
    "/brands/{brand_id}/products/json",
    response_model=ProductResponse,
    status_code=201
)
async def create_product_json_endpoint(
    brand_id: UUID,
    request: CreateProductRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Create a new product with JSON body and pre-uploaded image URLs.

    Use this endpoint when images have already been uploaded to S3 via presigned URLs.

    **Path Parameters:**
    - brand_id: UUID of the brand to associate product with

    **Request Body (JSON):**
    - product_type: Type of product (fragrance, car, watch, energy, mobile_app)
    - name: Product name (required)
    - product_gender: Gender (masculine/feminine/unisex, optional)
    - product_attributes: Type-specific attributes (optional)
    - icp_segment: Target audience description (optional)
    - image_urls: Array of S3 image URLs (required for most types, max 10)

    **Mobile App specific fields (when product_type='mobile_app'):**
    - app_input_mode: 'screenshots' or 'generated'
    - app_description: Description for UI generation (required if generated)
    - key_features: Array of features to showcase (max 10)
    - app_visual_style: UI style (modern_minimal, dark_mode, etc.)
    - screen_recording_url: S3 URL of screen recording video

    **Response:** ProductResponse with created product data
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Validate image requirements based on product type and mode
        is_mobile_app = request.product_type == 'mobile_app'
        is_generated_mode = request.app_input_mode == 'generated'

        # Mobile apps in generated mode don't require images upfront
        if not is_mobile_app or not is_generated_mode:
            if not request.image_urls or len(request.image_urls) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="At least one product image URL is required"
                )

        # Create product (validates brand ownership)
        product = create_product(
            db=db,
            user_id=user_id,
            brand_id=brand_id,
            product_type=request.product_type,
            name=request.name,
            product_gender=request.product_gender,
            icp_segment=request.icp_segment,
            image_urls=request.image_urls,
            # Mobile App fields
            app_input_mode=request.app_input_mode,
            app_description=request.app_description,
            key_features=request.key_features,
            app_visual_style=request.app_visual_style,
            screen_recording_url=request.screen_recording_url
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Brand {brand_id} not found or not owned by user"
            )

        logger.info(f"✅ Created product {product.id} (JSON) for brand {brand_id}")
        return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create product (JSON): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create product: {str(e)}"
        )


@router.get("/brands/{brand_id}/products", response_model=List[ProductResponse])
async def list_brand_products_endpoint(
    brand_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None),
    limit: int = 50,
    offset: int = 0
):
    """
    Get all products for a specific brand (ownership verified).

    **Path Parameters:**
    - brand_id: UUID of the brand

    **Query Parameters:**
    - limit: Maximum number of products to return (default: 50)
    - offset: Number of products to skip for pagination (default: 0)

    **Response:** List of ProductResponse objects

    **Errors:**
    - 401: Not authenticated
    - 404: Brand not found or not owned by user
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Get products (validates brand ownership)
        products = get_brand_products(
            db=db,
            user_id=user_id,
            brand_id=brand_id,
            limit=limit,
            offset=offset
        )

        if products is None:
            raise HTTPException(
                status_code=404,
                detail=f"Brand {brand_id} not found or not owned by user"
            )

        logger.info(f"✅ Retrieved {len(products)} products for brand {brand_id}")

        return products

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to list products for brand {brand_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product_endpoint(
    product_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Get a single product by ID (ownership verified via brand).

    **Path Parameters:**
    - product_id: UUID of the product

    **Response:** ProductResponse with product data

    **Errors:**
    - 401: Not authenticated
    - 404: Product not found or brand not owned by user
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Get product (validates brand ownership via JOIN)
        product = get_product(db=db, user_id=user_id, product_id=product_id)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        logger.info(f"✅ Retrieved product {product_id}")

        return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get product: {str(e)}")


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product_endpoint(
    product_id: UUID,
    request: UpdateProductRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Update a product (only if user owns parent brand).

    **Path Parameters:**
    - product_id: UUID of the product to update

    **Request Body:** Partial update - only include fields to change
    ```json
    {
        "name": "Updated Product Name",
        "icp_segment": "Updated segment"
    }
    ```

    **Response:** ProductResponse with updated product data

    **Errors:**
    - 401: Not authenticated
    - 404: Product not found or brand not owned by user
    - 400: Invalid request data (max 10 image URLs, no fields to update)
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Prepare update dict (only include fields that were provided)
        updates = request.dict(exclude_unset=True)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update product (validates brand ownership via JOIN)
        product = update_product(
            db=db,
            user_id=user_id,
            product_id=product_id,
            **updates
        )

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        logger.info(f"✅ Updated product {product_id}")

        return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")


@router.delete("/products/{product_id}", status_code=204)
async def delete_product_endpoint(
    product_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Delete a product (only if user owns parent brand).

    **Path Parameters:**
    - product_id: UUID of the product to delete

    **Response:** 204 No Content on success

    **Errors:**
    - 401: Not authenticated
    - 404: Product not found or brand not owned by user
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Delete product (validates brand ownership via JOIN)
        deleted = delete_product(db=db, user_id=user_id, product_id=product_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Product not found")

        logger.info(f"✅ Deleted product {product_id}")

        # Return 204 No Content
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")


# ============================================================================
# Campaign Endpoints for Products
# ============================================================================

@router.post(
    "/products/{product_id}/campaigns",
    response_model=CampaignDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create campaign for product",
    description="Create a new campaign for a product. Verifies product ownership."
)
async def create_product_campaign(
    product_id: UUID,
    data: CampaignCreate,
    brand_id: UUID = Depends(get_current_brand_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> CampaignDetail:
    """
    Create a new campaign for a product.

    Campaigns are organizational containers for creatives. Video-specific
    settings (duration, scenes) are defined per-creative, not per-campaign.

    **Path Parameters:**
    - `product_id`: Product UUID

    **Request Body:**
    - `name`: Campaign name (1-100 chars, unique within product)
    - `seasonal_event`: Seasonal event or marketing initiative (1-100 chars)
    - `year`: Campaign year (2020-2030)

    **Returns:**
    - CampaignDetail: Created campaign with all details

    **Raises:**
    - HTTPException 400: Invalid input data
    - HTTPException 404: Product not found or doesn't belong to brand
    - HTTPException 409: Campaign name already exists for this product
    """
    try:
        # Verify product belongs to brand
        verify_perfume_ownership(product_id, brand_id, db)

        # Check campaign name uniqueness within product
        existing_campaigns, _ = get_campaigns_by_product(db, product_id, page=1, limit=1000)
        for existing in existing_campaigns:
            if existing.name == data.name:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Campaign name '{data.name}' already exists for this product"
                )

        # Create campaign (video-specific fields use defaults)
        logger.info(f"💾 Creating campaign '{data.name}' for product {product_id} (brand {brand_id})")
        campaign = create_campaign(
            db=db,
            user_id=user_id,
            product_id=product_id,
            brand_id=brand_id,
            name=data.name,
            seasonal_event=data.seasonal_event,
            year=data.year
        )

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or doesn't belong to brand"
            )

        logger.info(f"✅ Created campaign {campaign.id} for product {product_id}")
        return CampaignDetail.model_validate(campaign)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create campaign: {str(e)}"
        )
