"""API endpoints for generation control."""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from rq.job import Job
import boto3
from io import BytesIO

from app.database.connection import get_db, init_db
from app.database import crud
from app.models.schemas import GenerationProgressResponse, CampaignStatus
from app.jobs.worker import create_worker
from app.api.auth import get_current_brand_id, verify_campaign_ownership

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize worker config
try:
    worker_config = create_worker()
except Exception as e:
    logger.warning(f"⚠️ Failed to initialize worker config: {e}")
    worker_config = None


# ============================================================================
# Generation Endpoints
# ============================================================================

@router.post("/campaigns/{campaign_id}/generate", deprecated=False)
@router.post("/campaigns/{campaign_id}/generate/", deprecated=False)
async def trigger_generation(
    campaign_id: UUID,
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
):
    """
    Trigger video generation for a campaign.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign to generate
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** 
    ```json
    {
        "status": "queued",
        "job_id": "...",
        "message": "Generation job enqueued",
        "campaign_id": "..."
    }
    ```
    
    **Errors:**
    - 404: Campaign not found
    - 403: Not authorized
    - 409: Generation already in progress
    - 401: Missing or invalid authorization
    - 503: Worker not available
    - 500: Failed to enqueue job
    """
    try:
        if not worker_config:
            raise HTTPException(
                status_code=503,
                detail="Worker not available. Redis connection required."
            )
        
        init_db()
        
        # Get campaign and verify ownership (done via dependency)
        campaign = crud.get_campaign_by_id(db, campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Check if already generating (allow retry from pending or failed)
        if campaign.status not in [CampaignStatus.PENDING.value, CampaignStatus.FAILED.value]:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot start generation: campaign is in state '{campaign.status}'. Only pending or failed campaigns can be generated."
            )
        
        # Enqueue job with RQ
        job = worker_config.enqueue_job(str(campaign_id))
        
        # Update campaign status
        crud.update_campaign(
            db,
            campaign_id,
            status=CampaignStatus.PROCESSING.value,
            progress=0
        )
        
        logger.info(f"✅ Enqueued generation for campaign {campaign_id}, job_id={job.id}")
        
        return {
            "status": "queued",
            "job_id": str(job.id),
            "message": "Generation job enqueued",
            "campaign_id": str(campaign_id)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to trigger generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger generation: {str(e)}")


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Get status of a specific RQ job.
    
    **Path Parameters:**
    - job_id: RQ Job ID
    
    **Response:**
    ```json
    {
        "job_id": "...",
        "status": "queued|started|finished|failed",
        "result": {...},
        "error": "..."
    }
    ```
    """
    try:
        if not worker_config:
            raise HTTPException(
                status_code=503,
                detail="Worker not available. Redis connection required."
            )
        
        job_status = worker_config.get_job_status(job_id)
        return job_status
    
    except Exception as e:
        logger.error(f"❌ Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/campaigns/{campaign_id}/reset")
async def reset_campaign_status(
    campaign_id: UUID,
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
):
    """
    Reset a stuck campaign to FAILED status so it can be retried.
    
    Useful when a campaign gets stuck in processing state and needs to be reset.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign to reset
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:**
    ```json
    {
        "status": "reset",
        "campaign_id": "...",
        "message": "Campaign reset to FAILED status. You can now retry generation."
    }
    ```
    
    **Errors:**
    - 404: Campaign not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        # Get campaign and verify ownership (done via dependency)
        campaign = crud.get_campaign_by_id(db, campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Reset to FAILED status
        crud.update_campaign(
            db,
            campaign_id,
            status=CampaignStatus.FAILED.value,
            progress=0,
            error_message="Manually reset - ready for retry"
        )
        
        logger.info(f"✅ Reset campaign {campaign_id} to FAILED status")
        
        return {
            "status": "reset",
            "campaign_id": str(campaign_id),
            "message": "Campaign reset to FAILED status. You can now retry generation."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reset campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset campaign: {str(e)}")


# ============================================================================
# MULTI-VARIATION GENERATION FEATURE: Variation Selection
# ============================================================================

class SelectVariationRequest(BaseModel):
    """Request schema for selecting a video variation."""
    variation_index: int = Field(..., ge=0, le=2, description="Index of variation to select (0-2)")


@router.post("/campaigns/{campaign_id}/select-variation")
async def select_variation(
    campaign_id: UUID,
    request: SelectVariationRequest,
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
):
    """
    Select a video variation for a multi-variation campaign.
    
    After generating multiple variations (num_variations > 1), users can select their preferred
    variation. This endpoint updates the campaign's selected_variation_index field.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Request Body:**
    ```json
    {
        "variation_index": 0
    }
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "campaign_id": "...",
        "selected_variation": 0,
        "message": "Variation 0 selected successfully"
    }
    ```
    
    **Errors:**
    - 400: Invalid variation_index (out of range) or campaign has only 1 variation
    - 404: Campaign not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        # Get campaign and verify ownership (done via dependency)
        campaign = crud.get_campaign_by_id(db, campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Validate that campaign has multiple variations
        num_variations = campaign.num_variations
        if num_variations <= 1:
            raise HTTPException(
                status_code=400,
                detail=f"Campaign has only {num_variations} variation(s). Selection is only available for campaigns with 2-3 variations."
            )
        
        # Validate variation_index is in valid range
        if request.variation_index < 0 or request.variation_index >= num_variations:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid variation_index: {request.variation_index}. Must be between 0 and {num_variations - 1}."
            )
        
        # Update campaign with selected variation
        updated_campaign = crud.update_campaign(
            db,
            campaign_id,
            selected_variation_index=request.variation_index
        )
        
        if not updated_campaign:
            raise HTTPException(status_code=404, detail="Failed to update campaign")
        
        logger.info(f"✅ Selected variation {request.variation_index} for campaign {campaign_id}")
        
        return {
            "status": "success",
            "campaign_id": str(campaign_id),
            "selected_variation": request.variation_index,
            "message": f"Variation {request.variation_index} selected successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to select variation for campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to select variation: {str(e)}")


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running job.
    
    **Path Parameters:**
    - job_id: RQ Job ID
    
    **Response:**
    ```json
    {
        "status": "cancelled",
        "job_id": "...",
        "message": "Job cancelled"
    }
    ```
    """
    try:
        if not worker_config:
            raise HTTPException(
                status_code=503,
                detail="Worker not available. Redis connection required."
            )
        
        cancelled = worker_config.cancel_job(job_id)
        
        if cancelled:
            return {
                "status": "cancelled",
                "job_id": job_id,
                "message": "Job cancelled successfully"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to cancel job"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/campaigns/{campaign_id}/progress", response_model=GenerationProgressResponse)
async def get_generation_progress(
    campaign_id: UUID,
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
):
    """
    Get current generation progress for a campaign.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** GenerationProgressResponse with current status
    
    **Example Response:**
    ```json
    {
      "campaign_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "processing",
      "progress": 25,
      "current_step": "Generating Video Scenes",
      "cost_so_far": 0.12,
      "error_message": null
    }
    ```
    
    **Errors:**
    - 404: Campaign not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        # Get campaign and verify ownership (done via dependency)
        campaign = crud.get_campaign_by_id(db, campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Map status to readable step
        step_map = {
            CampaignStatus.PENDING.value: "Pending",
            CampaignStatus.PROCESSING.value: "Processing",
            CampaignStatus.COMPLETED.value: "Completed",
            CampaignStatus.FAILED.value: "Failed"
        }
        
        return GenerationProgressResponse(
            campaign_id=campaign.campaign_id,
            status=campaign.status,
            progress=campaign.progress,
            current_step=step_map.get(campaign.status, campaign.status),
            cost_so_far=float(campaign.cost),
            error_message=campaign.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get progress for {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.post("/campaigns/{campaign_id}/cancel")
async def cancel_generation(
    campaign_id: UUID,
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
):
    """
    Cancel an in-progress generation (if possible).
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:**
    ```json
    {
        "status": "cancelled",
        "campaign_id": "...",
        "message": "Generation cancelled"
    }
    ```
    
    **Errors:**
    - 404: Campaign not found
    - 403: Not authorized
    - 409: Cannot cancel (not in progress)
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        # Get campaign and verify ownership (done via dependency)
        campaign = crud.get_campaign_by_id(db, campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Check if generation is in progress
        if campaign.status == CampaignStatus.COMPLETED.value:
            raise HTTPException(status_code=409, detail="Cannot cancel completed campaign")
        
        if campaign.status == CampaignStatus.FAILED.value:
            raise HTTPException(status_code=409, detail="Cannot cancel failed campaign")
        
        if campaign.status == CampaignStatus.PENDING.value:
            raise HTTPException(status_code=409, detail="Generation not started")
        
        # TODO: Cancel RQ job
        # For now, just mark as failed
        crud.update_campaign(
            db,
            campaign_id,
            status=CampaignStatus.FAILED.value,
            error_message="Cancelled by user"
        )
        
        logger.info(f"✅ Cancelled generation for campaign {campaign_id}")
        
        return {
            "status": "cancelled",
            "campaign_id": str(campaign_id),
            "message": "Generation cancelled"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cancel generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel generation: {str(e)}")


@router.get("/campaigns/{campaign_id}/download/{aspect_ratio}")
async def download_video(
    campaign_id: UUID,
    aspect_ratio: str,
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
):
    """
    Download a video file as a blob for local storage (IndexedDB).
    
    This endpoint streams the video file from S3 directly to the browser,
    allowing the frontend to store it locally for preview before finalization.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    - aspect_ratio: Video aspect ratio ('9:16', '1:1', '16:9')
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** 
    - Content-Type: video/mp4
    - Video file as binary blob
    
    **Errors:**
    - 404: Campaign not found or video not available
    - 403: Not authorized
    - 401: Missing or invalid authorization
    - 400: Invalid aspect ratio
    """
    try:
        # Validate aspect ratio
        if aspect_ratio not in ['9:16', '1:1', '16:9']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid aspect ratio: {aspect_ratio}. Must be: 9:16, 1:1, or 16:9"
            )
        
        init_db()
        
        # Get campaign and verify ownership (done via dependency)
        campaign = crud.get_campaign_by_id(db, campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get video URL from campaign_json variationPaths
        campaign_json = campaign.campaign_json or {}
        if isinstance(campaign_json, str):
            import json
            campaign_json = json.loads(campaign_json)
        
        # Get selected variation index (default to 0)
        selected_variation = campaign.selected_variation_index if campaign.selected_variation_index is not None else 0
        variation_paths = campaign_json.get('variationPaths', {})
        variation_key = f"variation_{selected_variation}"
        
        if variation_key not in variation_paths:
            raise HTTPException(
                status_code=404,
                detail=f"Variation {selected_variation} not found for campaign"
            )
        
        variation_data = variation_paths[variation_key]
        video_url = variation_data.get('aspectExports', {}).get(aspect_ratio)
        
        if not video_url:
            raise HTTPException(
                status_code=404,
                detail=f"Video not available for aspect ratio {aspect_ratio}"
            )
        
        # Extract S3 bucket and key from URL
        # URL format: https://bucket.s3.amazonaws.com/key or https://s3.amazonaws.com/bucket/key
        if '.s3.' in video_url:
            # Format: https://bucket.s3.region.amazonaws.com/key
            parts = video_url.split('/')
            bucket = parts[2].split('.')[0]
            key = '/'.join(parts[3:])
        else:
            # Fallback: assume it's a direct S3 URL
            raise HTTPException(status_code=400, detail="Invalid S3 URL format")
        
        # Download from S3
        s3_client = boto3.client('s3')
        
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            video_stream = response['Body'].read()
        except s3_client.exceptions.NoSuchKey:
            raise HTTPException(status_code=404, detail="Video file not found in S3")
        except Exception as e:
            logger.error(f"❌ Failed to download video from S3: {e}")
            raise HTTPException(status_code=500, detail="Failed to download video from S3")
        
        # Stream the video file to client
        return StreamingResponse(
            iter([video_stream]),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"inline; filename=video-{aspect_ratio}.mp4",
                "Cache-Control": "public, max-age=3600"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")


