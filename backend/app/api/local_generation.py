"""Local-first video generation endpoints.

Handles preview from local storage and finalization to S3.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.database.connection import get_db, init_db
from app.database.crud import get_campaign_by_user, update_campaign_status
from app.api.auth import get_current_user_id
from app.utils.local_storage import LocalStorageManager, format_storage_size
# S3 imports removed - using local storage only

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/campaigns/{campaign_id}/preview")
async def get_preview_video(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """Get preview video from S3 or local storage.

    Tries S3 first (output_videos field), falls back to local storage if needed.
    Returns a redirect to S3 URL for efficient video delivery.

    **Path Parameters:**
    - campaign_id: UUID of the campaign

    **Response:**
    - 307 Redirect to S3 URL OR
    - Content-Type: video/mp4 (streamed from local if S3 unavailable)

    **Errors:**
    - 404: Campaign not found or video not available
    - 403: Not authorized
    """
    try:
        init_db()
        user_id = get_current_user_id(authorization)
        # Get campaign and verify ownership
        campaign = get_campaign_by_user(db, campaign_id, user_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # PRIORITY 1: Check S3 URLs (output_videos field)
        s3_video_urls = campaign.output_videos or {}
        if s3_video_urls:
            # Get the first available S3 URL
            s3_url = next((url for url in s3_video_urls.values() if url), None)
            if s3_url:
                logger.info(f"✅ Redirecting to S3 preview: {s3_url}")
                # Return 307 redirect to S3 URL
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=s3_url, status_code=307)

        # FALLBACK: Check local storage
        local_video_paths = campaign.local_video_paths or {}
        local_video_path = next(iter(local_video_paths.values()), None) if local_video_paths else None

        if local_video_path and LocalStorageManager.file_exists(local_video_path):
            logger.info(f"✅ Streaming preview from local storage (S3 not available): {local_video_path}")
            return FileResponse(
                local_video_path,
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f"inline; filename=preview_variation_{variation}.mp4",
                    "Cache-Control": "public, max-age=3600",
                    "Accept-Ranges": "bytes",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "Range",
                }
            )
        
        # No video found in local storage
        raise HTTPException(
            status_code=404,
            detail=f"Preview video not available at path: {local_video_path}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get preview video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get preview video: {str(e)}")


@router.get("/campaigns/{campaign_id}/storage-info")
async def get_storage_info(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """Get local storage information for a campaign.
    
    Returns storage usage and status.
    
    **Response:**
    ```json
    {
        "campaign_id": "...",
        "local_storage_size": 524288000,
        "local_storage_size_formatted": "500 MB",
        "status": "READY_FOR_REVIEW",
        "local_video_paths": {
            "16:9": "/tmp/genads/.../video_16-9.mp4"
        }
    }
    ```
    """
    try:
        init_db()
        user_id = get_current_user_id(authorization)
        
        # Get campaign and verify ownership
        campaign = get_campaign_by_user(db, campaign_id, user_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Calculate storage size
        storage_size = LocalStorageManager.get_campaign_storage_size(campaign_id)
        
        return {
            "campaign_id": str(campaign_id),
            "local_storage_size": storage_size,
            "local_storage_size_formatted": format_storage_size(storage_size),
            "status": campaign.status,
            "local_video_paths": campaign.local_video_paths or {},
            "has_all_aspects": all(
                v in (campaign.local_video_paths or {})
                for v in ['16:9']
            )
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get storage info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get storage info: {str(e)}")


@router.post("/campaigns/{campaign_id}/finalize")
async def finalize_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """Finalize video: mark as finalized and keep videos in local storage.
    
    Called when user confirms they want to keep the video.
    - Marks campaign as FINALIZED
    - Keeps videos in local storage (no S3 upload)
    - Videos remain accessible via preview endpoint
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    
    **Response:**
    ```json
    {
        "status": "finalized",
        "campaign_id": "...",
        "local_video_paths": {
            "16:9": "/tmp/genads/.../video_16-9.mp4"
        },
        "message": "Campaign finalized. Videos remain in local storage."
    }
    ```
    
    **Errors:**
    - 404: Campaign not found
    - 403: Not authorized
    - 400: Campaign not ready for finalization
    """
    try:
        init_db()
        user_id = get_current_user_id(authorization)
        
        # Get campaign and verify ownership
        campaign = get_campaign_by_user(db, campaign_id, user_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Check if campaign is ready for finalization
        if campaign.status not in ['READY_FOR_REVIEW', 'COMPLETED']:
            raise HTTPException(
                status_code=400,
                detail=f"Campaign cannot be finalized in status: {campaign.status}"
            )
        
        # Get local video paths
        local_video_paths = campaign.local_video_paths or {}
        if not local_video_paths:
            raise HTTPException(
                status_code=400,
                detail="No videos available for finalization"
            )
        
        logger.info(f"🚀 Finalizing campaign {campaign_id} (keeping videos in local storage)")
        
        # Update campaign status to FINALIZED (keep videos in local storage)
        campaign.status = 'FINALIZED'
        db.commit()
        
        logger.info(f"✅ Updated campaign status to FINALIZED")
        
        return {
            "status": "finalized",
            "campaign_id": str(campaign_id),
            "local_video_paths": local_video_paths,
            "message": "Campaign finalized. Videos remain in local storage."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to finalize campaign: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to finalize campaign: {str(e)}"
        )


@router.post("/campaigns/{campaign_id}/cleanup-local")
async def cleanup_local_storage(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """Manual cleanup of local storage.
    
    Use if user wants to delete local files.
    
    **Warning:** This deletes all local files including final videos!
    """
    try:
        init_db()
        user_id = get_current_user_id(authorization)
        
        # Get campaign and verify ownership
        campaign = get_campaign_by_user(db, campaign_id, user_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Clear local storage metadata
        campaign.local_campaign_path = None
        campaign.local_video_paths = {}
        campaign.local_input_files = {}
        campaign.local_draft_files = {}
        db.commit()
        
        # Delete files from disk
        success = LocalStorageManager.cleanup_campaign_storage(campaign_id)
        
        return {
            "status": "cleaned",
            "campaign_id": str(campaign_id),
            "message": "Local storage cleaned up"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cleanup local storage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup: {str(e)}"
        )

