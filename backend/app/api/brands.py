"""
Brand API endpoints for B2B SaaS transformation.
Handles brand onboarding and brand information retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Dict, Any

from app.database.connection import get_db
from app.database import crud
from app.api.auth import get_current_user_id, get_current_brand_id
from app.models.schemas import BrandDetail, BrandCreate
from app.utils.s3_utils import upload_brand_logo, upload_brand_guidelines
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/debug/s3-config")
async def get_s3_config():
    """
    Debug endpoint to check S3 configuration.
    Returns S3 bucket name and region without exposing credentials.
    """
    return {
        "s3_bucket_name": settings.s3_bucket_name,
        "aws_region": settings.aws_region,
        "aws_access_key_configured": bool(settings.aws_access_key_id),
        "aws_secret_key_configured": bool(settings.aws_secret_access_key),
    }


@router.post(
    "/onboard",
    response_model=BrandDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Complete brand onboarding",
    description="Create a brand with logo and guidelines. This is mandatory for new users."
)
async def onboard_brand(
    brand_name: str = Form(..., min_length=2, max_length=100, description="Brand name"),
    logo: UploadFile = File(..., description="Brand logo (PNG, JPEG, WebP, max 5MB)"),
    guidelines: UploadFile = File(..., description="Brand guidelines (PDF or DOCX, max 10MB)"),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> BrandDetail:
    """
    Complete brand onboarding by uploading brand name, logo, and guidelines.
    
    **Request:**
    - Multipart form data with:
      - `brand_name`: Brand name (2-100 chars)
      - `logo`: Brand logo image file (PNG/JPEG/WebP, max 5MB)
      - `guidelines`: Brand guidelines document (PDF/DOCX, max 10MB)
    
    **Returns:**
    - BrandDetail: Created brand with all details
    
    **Raises:**
    - HTTPException 400: Invalid file format or size
    - HTTPException 409: Brand name already exists or user already has a brand
    - HTTPException 500: Upload or database error
    """
    try:
        # Validate logo file format
        logo_content_type = logo.content_type
        if logo_content_type not in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid logo format. Expected PNG, JPEG, or WebP, got {logo_content_type}"
            )
        
        # Validate logo file size (max 5MB)
        logo.file.seek(0, 2)  # Seek to end
        logo_size = logo.file.tell()
        logo.file.seek(0)  # Reset to beginning
        if logo_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Logo file too large. Maximum size is 5MB"
            )
        
        # Validate guidelines file format
        guidelines_content_type = guidelines.content_type
        valid_guidelines_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # DOCX
        ]
        if guidelines_content_type not in valid_guidelines_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid guidelines format. Expected PDF or DOCX, got {guidelines_content_type}"
            )
        
        # Validate guidelines file size (max 10MB)
        guidelines.file.seek(0, 2)  # Seek to end
        guidelines_size = guidelines.file.tell()
        guidelines.file.seek(0)  # Reset to beginning
        if guidelines_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guidelines file too large. Maximum size is 10MB"
            )
        
        # Check if user already has a brand
        existing_brand = crud.get_brand_by_user_id(db, user_id)
        if existing_brand:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has a brand. Use update endpoint to modify."
            )
        
        # Generate brand_id (will be used for S3 paths)
        from uuid import uuid4
        brand_id = uuid4()
        
        # Read file contents
        logo.file.seek(0)
        logo_content = await logo.read()
        logo.file.seek(0)
        
        guidelines.file.seek(0)
        guidelines_content = await guidelines.read()
        guidelines.file.seek(0)
        
        # Upload logo to S3
        logger.info(f"📤 Uploading logo for brand {brand_id}")
        logo_result = await upload_brand_logo(str(brand_id), logo_content, logo.filename)
        logo_url = logo_result["url"]
        logger.info(f"✅ Logo uploaded: {logo_url}")
        
        # Upload guidelines to S3
        logger.info(f"📤 Uploading guidelines for brand {brand_id}")
        guidelines_result = await upload_brand_guidelines(str(brand_id), guidelines_content, guidelines.filename)
        guidelines_url = guidelines_result["url"]
        logger.info(f"✅ Guidelines uploaded: {guidelines_url}")
        
        # Create brand in database
        logger.info(f"💾 Creating brand {brand_id} in database")
        brand = crud.create_brand(
            db=db,
            brand_id=brand_id,  # Pass the brand_id so S3 paths match database
            user_id=user_id,
            brand_name=brand_name,
            brand_logo_url=logo_url,
            brand_guidelines_url=guidelines_url
        )
        
        # Verify brand was created with correct brand_id
        if brand.brand_id != brand_id:
            logger.error(f"❌ CRITICAL: Brand created with wrong brand_id! Expected {brand_id}, got {brand.brand_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Brand created with incorrect brand_id. Expected {brand_id}, got {brand.brand_id}"
            )
        logger.info(f"✅ Verified brand {brand.brand_id} created with correct brand_id")
        
        logger.info(f"✅ Brand onboarding completed: {brand.brand_id}")
        return BrandDetail.model_validate(brand)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Brand onboarding failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete onboarding: {str(e)}"
        )


@router.get(
    "/me",
    response_model=BrandDetail,
    summary="Get current brand",
    description="Get brand details for the authenticated user."
)
async def get_my_brand(
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> BrandDetail:
    """
    Get brand details for the current authenticated user.
    
    **Returns:**
    - BrandDetail: Brand details
    
    **Raises:**
    - HTTPException 404: Brand not found (onboarding not completed)
    """
    try:
        brand = crud.get_brand_by_id(db, brand_id)
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand not found"
            )
        
        return BrandDetail.model_validate(brand)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get brand: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brand"
        )


@router.get(
    "/me/stats",
    summary="Get brand statistics",
    description="Get statistics for the authenticated user's brand (products count, campaigns count, total cost)."
)
async def get_brand_stats(
    brand_id: UUID = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get brand statistics including:
    - Total products
    - Total campaigns
    - Total cost
    
    **Returns:**
    - Dict with statistics
    
    **Raises:**
    - HTTPException 404: Brand not found
    """
    try:
        stats = crud.get_brand_stats(db, brand_id)
        return stats
    
    except Exception as e:
        logger.error(f"❌ Failed to get brand stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brand statistics"
        )

