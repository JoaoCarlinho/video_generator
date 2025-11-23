"""Storage API endpoints for file uploads."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Literal
from app.services.storage import storage_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["storage"])


class PresignedUrlRequest(BaseModel):
    """Request model for generating presigned upload URL."""
    
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type (e.g., 'image/png', 'application/pdf')")
    asset_type: Literal["logo", "product", "guidelines"] = Field(..., description="Type of asset being uploaded")
    user_id: str = Field(default="00000000-0000-0000-0000-000000000001", description="User ID (default dev user)")


class PresignedUrlResponse(BaseModel):
    """Response model with presigned URL."""
    
    upload_url: str = Field(..., description="Presigned URL for uploading file")
    file_url: str = Field(..., description="Public URL of the file after upload")
    s3_key: str = Field(..., description="S3 key of the uploaded file")
    expires_in: int = Field(default=3600, description="URL expiration time in seconds")


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_upload_url(request: PresignedUrlRequest):
    """
    Generate a presigned URL for uploading assets to S3.
    
    This endpoint generates a presigned URL that the frontend can use to upload
    files directly to S3 without going through the backend.
    
    **Asset Types:**
    - `logo`: Brand logos (images)
    - `product`: Product images (images)
    - `guidelines`: Brand guidelines (PDFs, text files)
    
    **Usage:**
    1. Call this endpoint to get a presigned URL
    2. Upload file to the `upload_url` using PUT request
    3. Use the `file_url` when creating a campaign
    
    **Example:**
    ```python
    # Step 1: Get presigned URL
    response = await fetch('/api/storage/presigned-url', {
        method: 'POST',
        body: JSON.stringify({
            filename: 'nike-logo.png',
            content_type: 'image/png',
            asset_type: 'logo'
        })
    })
    
    # Step 2: Upload file to S3
    await fetch(response.upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': 'image/png' }
    })
    
    # Step 3: Use file_url in campaign creation
    await createCampaign({
        ...campaignData,
        logo_url: response.file_url
    })
    ```
    """
    logger.info(f"📤 Generating presigned URL for {request.asset_type}: {request.filename}")
    
    # Map asset type to S3 folder
    folder_map = {
        "logo": "assets/logos",
        "product": "assets/products",
        "guidelines": "assets/guidelines"
    }
    
    folder = folder_map[request.asset_type]
    
    # Generate presigned URL
    result = storage_service.generate_presigned_upload_url(
        folder=folder,
        filename=request.filename,
        content_type=request.content_type,
        user_id=request.user_id,
        expires_in=3600  # 1 hour
    )
    
    if not result:
        logger.error(f"❌ Failed to generate presigned URL for {request.filename}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate presigned URL. S3 may not be configured."
        )
    
    logger.info(f"✅ Generated presigned URL: {result['s3_key']}")
    
    return PresignedUrlResponse(
        upload_url=result['upload_url'],
        file_url=result['file_url'],
        s3_key=result['s3_key'],
        expires_in=3600
    )


@router.get("/health")
async def storage_health():
    """Check if S3 storage is configured and accessible."""
    
    is_configured = (
        storage_service.s3_client is not None and 
        storage_service.bucket_name is not None
    )
    
    return {
        "configured": is_configured,
        "bucket": storage_service.bucket_name if is_configured else None,
        "region": storage_service.s3_client._client_config.region_name if is_configured else None
    }

