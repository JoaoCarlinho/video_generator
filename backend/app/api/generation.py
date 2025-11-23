"""API endpoints for generation control."""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from typing import Optional
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
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize SQS worker config (only available in worker Lambda with full dependencies)
try:
    from app.jobs.sqs_worker import create_sqs_worker
    worker_config = create_sqs_worker()
except (ImportError, AttributeError, Exception) as e:
    logger.warning(f"⚠️ Failed to initialize SQS worker config: {e}")
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
                detail="Worker not available. SQS connection required."
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
            "job_id": str(job["id"]),
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
    Get status of a specific job.
    
    **Path Parameters:**
    - job_id: Job ID
    
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
                detail="Worker not available. SQS connection required."
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
    - job_id: Job ID
    
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
                detail="Worker not available. SQS connection required."
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


@router.get("/campaigns/{campaign_id}/stream/{aspect_ratio}")
async def stream_video(
    campaign_id: UUID,
    aspect_ratio: str,
    variation_index: Optional[int] = Query(None),
    _: bool = Depends(verify_campaign_ownership),
    db: Session = Depends(get_db)
):
    """
    Stream a video file for playback in the browser (with CORS support).
    
    This endpoint streams the video file from S3 through the backend,
    adding proper CORS headers to allow frontend video players to access it.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    - aspect_ratio: Video aspect ratio ('9:16', '1:1', '16:9')
    
    **Query Parameters:**
    - variation_index: Optional variation index (0, 1, 2) to stream specific variation. 
                      If not provided, streams the campaign's selected variation (or 0).
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    - Range: Optional byte range for video seeking (e.g., "bytes=0-1023")
    
    **Response:** 
    - Content-Type: video/mp4
    - Video file as binary stream with CORS headers
    
    **Errors:**
    - 404: Campaign not found or video not available
    - 403: Not authorized
    - 401: Missing or invalid authorization
    - 400: Invalid aspect ratio
    """
    from fastapi import Request
    from fastapi.responses import Response
    
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
        
        # Construct S3 key directly to avoid issues with stored URLs
        # Use provided variation_index, or selected variation, or default to 0
        if variation_index is not None:
            target_variation = variation_index
        elif campaign.selected_variation_index is not None:
            target_variation = campaign.selected_variation_index
        else:
            target_variation = 0
            
        # Validate target variation
        if target_variation < 0:
             raise HTTPException(status_code=400, detail="Invalid variation index")
        
        # Construct path based on hierarchy: brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/variation_{i}/final/final_video.mp4
        # Note: currently only 9:16 is generated as 'final_video.mp4'
        # In future phases, we might have final_1_1.mp4 etc.
        filename = "final_video.mp4"
        if aspect_ratio != '9:16':
            # For now, we only support 9:16 as per Phase 2 implementation
            # If other aspect ratios are requested, we check if they exist or fail
            # TODO: Support other aspect ratios in filenames (e.g., final_1_1.mp4)
            pass
            
        s3_key = f"brands/{str(campaign.brand_id)}/perfumes/{str(campaign.perfume_id)}/campaigns/{str(campaign_id)}/variation_{target_variation}/final/{filename}"
        
        logger.info(f"🎬 Streaming video from S3: {s3_key} (variation {target_variation})")
        
        if not settings.s3_bucket_name:
             raise HTTPException(status_code=500, detail="S3 bucket not configured")
             
        bucket_name = settings.s3_bucket_name
        
        # Download from S3 using configured credentials
        from app.utils.s3_utils import get_s3_client
        s3_client = get_s3_client()
        
        try:
            # Get object metadata first
            head_response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            content_length = head_response['ContentLength']
            content_type = head_response.get('ContentType', 'video/mp4')
            etag = head_response.get('ETag', '').strip('"')
            
            # Handle range requests for video seeking
            range_header = None
            # Note: FastAPI doesn't expose Request headers directly in this context
            # We'll stream the full video for now, but add CORS headers
            
            response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            video_stream = response['Body'].read()
            logger.info(f"✅ Streamed video from S3: {s3_key} ({len(video_stream)} bytes)")
        except s3_client.exceptions.NoSuchKey:
            logger.warning(f"⚠️ Video file not found at exact path: {s3_key}")
            
            # Fallback: Search for any final video in the campaign folder
            # This handles cases where variation index might be mismatched or path structure slightly different
            try:
                campaign_prefix = f"brands/{str(campaign.brand_id)}/perfumes/{str(campaign.perfume_id)}/campaigns/{str(campaign_id)}/"
                logger.info(f"🔍 Searching for fallback video in: {campaign_prefix}")
                
                objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=campaign_prefix)
                
                found_fallback = None
                if 'Contents' in objects:
                    # Look for any mp4 in a 'final' folder
                    for obj in objects['Contents']:
                        key = obj['Key']
                        if '/final/' in key and key.endswith('.mp4'):
                            logger.info(f"✅ Found fallback video: {key}")
                            found_fallback = key
                            # If we requested a specific variation, try to match it loosely
                            if f"variation_{target_variation}" in key:
                                break # Found best match
                            
                if found_fallback:
                    logger.warning(f"⚠️ Using fallback video: {found_fallback}")
                    head_response = s3_client.head_object(Bucket=bucket_name, Key=found_fallback)
                    content_length = head_response['ContentLength']
                    content_type = head_response.get('ContentType', 'video/mp4')
                    etag = head_response.get('ETag', '').strip('"')
                    
                    response = s3_client.get_object(Bucket=bucket_name, Key=found_fallback)
                    video_stream = response['Body'].read()
                else:
                    # Log all files found to help debugging
                    files_found = [o['Key'] for o in objects.get('Contents', [])]
                    logger.error(f"❌ No video files found. Files in campaign: {files_found}")
                    raise HTTPException(status_code=404, detail=f"Video file not found in S3. Searched: {campaign_prefix}")
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                logger.error(f"❌ Fallback search failed: {e}")
                raise HTTPException(status_code=404, detail=f"Video file not found in S3: {s3_key}")
        except Exception as e:
            logger.error(f"❌ Failed to stream video from S3: {e}")
            raise HTTPException(status_code=500, detail="Failed to stream video from S3")
        
        # Stream the video file to client with CORS headers
        # Use no-cache headers to prevent browser caching after edits
        return StreamingResponse(
            iter([video_stream]),
            media_type=content_type,
            headers={
                "Content-Length": str(content_length),
                "Content-Type": content_type,
                "Accept-Ranges": "bytes",
                "ETag": f'"{etag}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range, Content-Range, Content-Type",
                "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to stream video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stream video: {str(e)}")


@router.get("/campaigns/{campaign_id}/download/{aspect_ratio}")
async def download_video(
    campaign_id: UUID,
    aspect_ratio: str,
    variation_index: Optional[int] = Query(None),
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
    
    **Query Parameters:**
    - variation_index: Optional variation index (0, 1, 2)
    
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
        if aspect_ratio not in ['16:9']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid aspect ratio: {aspect_ratio}. Must be: 16:9"
            )
        
        init_db()
        
        # Get campaign and verify ownership (done via dependency)
        campaign = crud.get_campaign_by_id(db, campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Construct S3 key directly
        if variation_index is not None:
            target_variation = variation_index
        elif campaign.selected_variation_index is not None:
            target_variation = campaign.selected_variation_index
        else:
            target_variation = 0
        
        filename = "final_video.mp4"
        if aspect_ratio != '9:16':
            pass # Future support
            
        s3_key = f"brands/{campaign.brand_id}/perfumes/{campaign.perfume_id}/campaigns/{campaign_id}/variation_{target_variation}/final/{filename}"
        
        if not settings.s3_bucket_name:
             raise HTTPException(status_code=500, detail="S3 bucket not configured")
             
        bucket_name = settings.s3_bucket_name
        
        # Download from S3 using configured credentials
        from app.utils.s3_utils import get_s3_client
        s3_client = get_s3_client()
        
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            video_stream = response['Body'].read()
            logger.info(f"✅ Downloaded video from S3: {s3_key}")
        except s3_client.exceptions.NoSuchKey:
            logger.warning(f"⚠️ Video file not found in S3: {s3_key}")
            raise HTTPException(status_code=404, detail="Video file not found in S3")
        except Exception as e:
            logger.error(f"❌ Failed to download video from S3: {e}")
            raise HTTPException(status_code=500, detail="Failed to download video from S3")
        
        # Stream the video file to client with CORS headers
        return StreamingResponse(
            iter([video_stream]),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"inline; filename=video-{aspect_ratio}.mp4",
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range",
                "Accept-Ranges": "bytes"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")


