"""
Perfume API endpoints for B2B SaaS transformation.
Handles perfume CRUD operations.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Optional, List

from app.database.connection import get_db
from app.database import crud
from app.api.auth import get_current_brand_id, verify_perfume_ownership
from app.models.schemas import PerfumeDetail, PerfumeCreate, PaginatedPerfumes, PerfumeGender
from app.utils.s3_utils import upload_perfume_image

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=PerfumeDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create perfume",
    description="Create a new perfume for the authenticated brand. Front image is required, other angles are optional."
)
async def create_perfume(
    perfume_name: str = Form(..., min_length=2, max_length=200, description="Perfume name"),
    perfume_gender: str = Form(..., description="Perfume gender (masculine, feminine, unisex)"),
    front_image: UploadFile = File(..., description="Front image (required, PNG/JPEG/WebP, max 5MB)"),
    back_image: Optional[UploadFile] = File(None, description="Back image (optional)"),
    top_image: Optional[UploadFile] = File(None, description="Top image (optional)"),
    left_image: Optional[UploadFile] = File(None, description="Left image (optional)"),
    right_image: Optional[UploadFile] = File(None, description="Right image (optional)"),
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> PerfumeDetail:
    """
    Create a new perfume for the authenticated brand.
    
    **Request:**
    - Multipart form data with:
      - `perfume_name`: Perfume name (2-200 chars)
      - `perfume_gender`: Gender ('masculine', 'feminine', 'unisex')
      - `front_image`: Front image (REQUIRED, PNG/JPEG/WebP, max 5MB)
      - `back_image`: Back image (optional)
      - `top_image`: Top image (optional)
      - `left_image`: Left image (optional)
      - `right_image`: Right image (optional)
    
    **Returns:**
    - PerfumeDetail: Created perfume with all details
    
    **Raises:**
    - HTTPException 400: Invalid file format, size, or gender
    - HTTPException 409: Perfume name already exists for this brand
    """
    try:
        # Validate perfume_gender
        if perfume_gender not in ["masculine", "feminine", "unisex"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid perfume_gender. Expected 'masculine', 'feminine', or 'unisex', got '{perfume_gender}'"
            )
        
        # Validate front image (required)
        front_content_type = front_image.content_type
        if front_content_type not in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid front image format. Expected PNG, JPEG, or WebP, got {front_content_type}"
            )
        
        front_image.file.seek(0, 2)
        front_size = front_image.file.tell()
        front_image.file.seek(0)
        if front_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Front image file too large. Maximum size is 5MB"
            )
        
        # Validate optional images
        def validate_image(image: Optional[UploadFile], angle: str) -> Optional[str]:
            if image is None:
                return None
            
            content_type = image.content_type
            if content_type not in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid {angle} image format. Expected PNG, JPEG, or WebP, got {content_type}"
                )
            
            image.file.seek(0, 2)
            size = image.file.tell()
            image.file.seek(0)
            if size > 5 * 1024 * 1024:  # 5MB
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{angle.capitalize()} image file too large. Maximum size is 5MB"
                )
            
            return angle
        
        # Generate perfume_id
        from uuid import uuid4
        perfume_id = uuid4()
        
        # Read front image content
        front_image.file.seek(0)
        front_content = await front_image.read()
        front_image.file.seek(0)
        
        # Upload front image (required)
        logger.info(f"📤 Uploading front image for perfume {perfume_id}")
        front_result = await upload_perfume_image(str(brand_id), str(perfume_id), "front", front_content, front_image.filename)
        front_url = front_result["url"]
        logger.info(f"✅ Front image uploaded: {front_url}")
        
        # Upload optional images
        back_url = None
        if back_image:
            back_image.file.seek(0)
            back_content = await back_image.read()
            back_image.file.seek(0)
            logger.info(f"📤 Uploading back image for perfume {perfume_id}")
            back_result = await upload_perfume_image(str(brand_id), str(perfume_id), "back", back_content, back_image.filename)
            back_url = back_result["url"]
            logger.info(f"✅ Back image uploaded: {back_url}")
        
        top_url = None
        if top_image:
            top_image.file.seek(0)
            top_content = await top_image.read()
            top_image.file.seek(0)
            logger.info(f"📤 Uploading top image for perfume {perfume_id}")
            top_result = await upload_perfume_image(str(brand_id), str(perfume_id), "top", top_content, top_image.filename)
            top_url = top_result["url"]
            logger.info(f"✅ Top image uploaded: {top_url}")
        
        left_url = None
        if left_image:
            left_image.file.seek(0)
            left_content = await left_image.read()
            left_image.file.seek(0)
            logger.info(f"📤 Uploading left image for perfume {perfume_id}")
            left_result = await upload_perfume_image(str(brand_id), str(perfume_id), "left", left_content, left_image.filename)
            left_url = left_result["url"]
            logger.info(f"✅ Left image uploaded: {left_url}")
        
        right_url = None
        if right_image:
            right_image.file.seek(0)
            right_content = await right_image.read()
            right_image.file.seek(0)
            logger.info(f"📤 Uploading right image for perfume {perfume_id}")
            right_result = await upload_perfume_image(str(brand_id), str(perfume_id), "right", right_content, right_image.filename)
            right_url = right_result["url"]
            logger.info(f"✅ Right image uploaded: {right_url}")
        
        # Create perfume in database
        logger.info(f"💾 Creating perfume {perfume_id} in database")
        perfume = crud.create_perfume(
            db=db,
            brand_id=brand_id,
            perfume_name=perfume_name,
            perfume_gender=perfume_gender,
            front_image_url=front_url,
            back_image_url=back_url,
            top_image_url=top_url,
            left_image_url=left_url,
            right_image_url=right_url
        )
        
        # Get campaigns count
        campaigns_count = crud.get_perfume_campaigns_count(db, perfume.perfume_id)
        
        logger.info(f"✅ Perfume created: {perfume.perfume_id}")
        
        # Convert to response model
        perfume_detail = PerfumeDetail.model_validate(perfume)
        perfume_detail.campaigns_count = campaigns_count
        return perfume_detail
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create perfume: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create perfume: {str(e)}"
        )


@router.get(
    "",
    response_model=PaginatedPerfumes,
    summary="List perfumes",
    description="Get paginated list of perfumes for the authenticated brand."
)
async def list_perfumes(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> PaginatedPerfumes:
    """
    Get paginated list of perfumes for the authenticated brand.
    
    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `limit`: Items per page (default: 20, max: 100)
    
    **Returns:**
    - PaginatedPerfumes: Paginated list with total count
    """
    try:
        perfumes, total = crud.get_perfumes_by_brand(db, brand_id, page, limit)
        
        # Add campaigns_count to each perfume
        perfume_details = []
        for perfume in perfumes:
            campaigns_count = crud.get_perfume_campaigns_count(db, perfume.perfume_id)
            perfume_detail = PerfumeDetail.model_validate(perfume)
            perfume_detail.campaigns_count = campaigns_count
            perfume_details.append(perfume_detail)
        
        pages = (total + limit - 1) // limit  # Ceiling division
        
        return PaginatedPerfumes(
            perfumes=perfume_details,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to list perfumes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve perfumes"
        )


@router.get(
    "/{perfume_id}",
    response_model=PerfumeDetail,
    summary="Get perfume",
    description="Get perfume details by ID. Verifies ownership."
)
async def get_perfume(
    perfume_id: UUID,
    _: bool = Depends(verify_perfume_ownership),
    db: Session = Depends(get_db)
) -> PerfumeDetail:
    """
    Get perfume details by ID.
    
    **Path Parameters:**
    - `perfume_id`: Perfume UUID
    
    **Returns:**
    - PerfumeDetail: Perfume details
    
    **Raises:**
    - HTTPException 404: Perfume not found or doesn't belong to brand
    """
    try:
        perfume = crud.get_perfume_by_id(db, perfume_id)
        if not perfume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfume not found"
            )
        
        # Get campaigns count
        campaigns_count = crud.get_perfume_campaigns_count(db, perfume.perfume_id)
        
        perfume_detail = PerfumeDetail.model_validate(perfume)
        perfume_detail.campaigns_count = campaigns_count
        return perfume_detail
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get perfume: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve perfume"
        )


@router.delete(
    "/{perfume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete perfume",
    description="Delete a perfume. Only allowed if perfume has no campaigns."
)
async def delete_perfume(
    perfume_id: UUID,
    _: bool = Depends(verify_perfume_ownership),
    db: Session = Depends(get_db)
):
    """
    Delete a perfume.
    
    **Path Parameters:**
    - `perfume_id`: Perfume UUID
    
    **Raises:**
    - HTTPException 400: Perfume has campaigns (cannot delete)
    - HTTPException 404: Perfume not found
    """
    try:
        perfume = crud.get_perfume_by_id(db, perfume_id)
        if not perfume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfume not found"
            )
        
        # Check if perfume has campaigns
        campaigns_count = crud.get_perfume_campaigns_count(db, perfume_id)
        if campaigns_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete perfume with {campaigns_count} campaign(s). Delete campaigns first."
            )
        
        # Delete perfume
        db.delete(perfume)
        db.commit()
        
        logger.info(f"✅ Deleted perfume {perfume_id}")
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete perfume: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete perfume"
        )

