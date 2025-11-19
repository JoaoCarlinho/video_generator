"""API endpoints for product management."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import logging

from app.database.connection import get_db
from app.database.crud import (
    create_product,
    get_brand_products,
    get_product,
    update_product,
    delete_product
)
from app.models.schemas import (
    CreateProductRequest,
    UpdateProductRequest,
    ProductResponse
)
from app.api.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# Product Endpoints
# ============================================================================

@router.post("/brands/{brand_id}/products", response_model=ProductResponse, status_code=201)
async def create_product_endpoint(
    brand_id: UUID,
    request: CreateProductRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Create a new product associated with a brand.

    **Path Parameters:**
    - brand_id: UUID of the brand to associate product with

    **Request Body:**
    ```json
    {
        "product_type": "SaaS",
        "name": "Analytics Platform",
        "icp_segment": "Mid-market B2B companies",
        "image_urls": ["https://s3.../product1.png", "https://s3.../product2.png"]
    }
    ```

    **Response:** ProductResponse with created product data

    **Errors:**
    - 401: Not authenticated
    - 404: Brand not found or not owned by user
    - 400: Invalid request data (max 10 image URLs)
    - 500: Database error
    """
    try:
        # Get authenticated user
        user_id = get_current_user_id(authorization)

        # Create product (validates brand ownership)
        product = create_product(
            db=db,
            user_id=user_id,
            brand_id=brand_id,
            product_type=request.product_type,
            name=request.name,
            icp_segment=request.icp_segment,
            image_urls=request.image_urls
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Brand {brand_id} not found or not owned by user"
            )

        logger.info(f"✅ Created product {product.id} for brand {brand_id}")

        return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


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
