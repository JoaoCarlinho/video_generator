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
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request Schema for JSON-based brand creation
# ============================================================================

class CreateBrandJSONRequest(BaseModel):
    """Request schema for creating a brand via JSON (with pre-uploaded S3 URLs)."""
    name: str = Field(..., min_length=1, max_length=200, description="Brand/company name")
    logo_url: Optional[str] = Field(None, description="S3 URL of uploaded logo")
    brand_guidelines_url: Optional[str] = Field(None, description="S3 URL or text of brand guidelines")
    primary_color: Optional[str] = Field(None, description="Primary brand color (hex)")
    secondary_color: Optional[str] = Field(None, description="Secondary brand color (hex)")
    target_audience: Optional[str] = Field(None, description="Target audience description")


# ============================================================================
# Brand Endpoints
# ============================================================================

@router.post(
    "",
    response_model=BrandDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create brand with JSON data",
    description="Create a brand using JSON body with pre-uploaded S3 URLs for assets."
)
async def create_brand_json(
    request: CreateBrandJSONRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> BrandDetail:
    """
    Create a brand using JSON data with pre-uploaded S3 URLs.

    This endpoint is used when files are uploaded to S3 via presigned URLs first,
    then the brand is created with the resulting URLs.

    **Request Body:**
    - `name`: Brand/company name (required)
    - `logo_url`: S3 URL of uploaded logo (optional)
    - `brand_guidelines_url`: S3 URL or text of guidelines (optional)
    - `primary_color`: Primary brand color hex (optional)
    - `secondary_color`: Secondary brand color hex (optional)
    - `target_audience`: Target audience description (optional)

    **Returns:**
    - BrandDetail: Created brand with all details

    **Raises:**
    - HTTPException 409: User already has a brand
    - HTTPException 500: Database error
    """
    try:
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")

        # Check if user already has a brand
        existing_brand = crud.get_brand_by_user_id(db, user_id)
        if existing_brand:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has a brand. Use update endpoint to modify."
            )

        # Prepare logo_urls dict if logo_url provided
        logo_urls = None
        if request.logo_url:
            logo_urls = {"primary": request.logo_url}

        # Create brand in database
        logger.info(f"💾 Creating brand for user {user_id}")
        brand = crud.create_brand(
            db=db,
            user_id=user_id,
            company_name=request.name,
            brand_name=request.name,
            description=request.target_audience,
            guidelines=request.brand_guidelines_url,
            logo_urls=logo_urls
        )

        logger.info(f"✅ Brand created with ID: {brand.id}")
        return BrandDetail.model_validate(brand)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Brand creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create brand: {str(e)}"
        )


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
            user_id=user_id,
            company_name=brand_name,  # Use brand_name as company_name
            brand_name=brand_name,
            guidelines=guidelines_url,  # Store URL as guidelines text
            logo_urls={"primary": logo_url}  # Store logo URL in JSONB dict
        )

        # Override the generated ID with the pre-generated brand_id to match S3 paths
        brand.id = brand_id
        db.commit()
        db.refresh(brand)

        logger.info(f"✅ Brand created with ID: {brand.id}")

        logger.info(f"✅ Brand onboarding completed: {brand.id}")
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
    response_model=Optional[BrandDetail],
    summary="Get current brand",
    description="Get brand details for the authenticated user. Returns null if onboarding not completed."
)
async def get_my_brand(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Optional[BrandDetail]:
    """
    Get brand details for the current authenticated user.

    **Returns:**
    - BrandDetail: Brand details if onboarding completed
    - None: If user hasn't completed onboarding yet

    **Raises:**
    - HTTPException 500: Database or internal error
    """
    try:
        brand = crud.get_brand_by_user_id(db, user_id)
        if not brand:
            return None

        return BrandDetail.model_validate(brand)

    except Exception as e:
        logger.error(f"❌ Failed to get brand: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brand"
        )


@router.get(
    "/me/stats",
    summary="Get brand statistics",
    description="Get statistics for the authenticated user's brand. Returns zeros if onboarding not completed."
)
async def get_brand_stats(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get brand statistics including:
    - Total products
    - Total campaigns
    - Total cost

    **Returns:**
    - Dict with statistics (zeros if brand not found)

    **Raises:**
    - HTTPException 500: Database or internal error
    """
    try:
        brand = crud.get_brand_by_user_id(db, user_id)
        if not brand:
            # Return empty stats if user hasn't completed onboarding
            return {
                "total_products": 0,
                "total_campaigns": 0,
                "total_cost": 0.0
            }

        stats = crud.get_brand_stats(db, brand.id)
        return stats

    except Exception as e:
        logger.error(f"❌ Failed to get brand stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brand statistics"
        )

