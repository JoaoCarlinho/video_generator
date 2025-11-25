"""API endpoints for campaign editing."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
import logging
import boto3
from io import BytesIO

from app.database.connection import get_db
from app.database.crud import get_campaign_by_id
from app.api.auth import verify_campaign_ownership
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["editing"])

# TODO: Editing feature temporarily disabled - needs migration from Redis/RQ to SQS
# The system has moved to SQS for job queuing, but editing still uses Redis/RQ
# Until editing is migrated, the edit endpoints will return 503 Service Unavailable
worker_config = None


# ============================================================================
# Request/Response Schemas
# ============================================================================

class EditSceneRequest(BaseModel):
    """Request to edit a scene."""
    edit_prompt: str


class EditSceneResponse(BaseModel):
    """Response when edit job is enqueued."""
    job_id: str
    estimated_cost: float
    estimated_duration_seconds: int
    message: str


class SceneInfo(BaseModel):
    """Scene information for editing UI."""
    scene_index: int
    scene_id: int
    role: str
    duration: int
    background_prompt: str
    video_url: str
    thumbnail_url: Optional[str] = None
    edit_count: int = 0
    last_edited_at: Optional[str] = None


class EditHistoryRecord(BaseModel):
    """Single edit history record."""
    edit_id: str
    timestamp: str
    scene_index: int
    edit_prompt: str
    changes_summary: Optional[str] = None
    cost: float
    duration_seconds: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/{campaign_id}/scenes", response_model=List[SceneInfo])
async def get_campaign_scenes(
    campaign_id: UUID,
    variation_index: int = 0,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_ownership)
):
    """
    Get all scenes for a campaign (for editing UI).
    
    Returns scene data with video URLs and thumbnails.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_json = campaign.campaign_json
    if isinstance(campaign_json, str):
        import json
        campaign_json = json.loads(campaign_json)
    
    scenes = campaign_json.get('scenes', [])
    
    from app.utils.s3_utils import get_scene_s3_url
    
    scene_infos = []
    for i, scene in enumerate(scenes):
        # Construct S3 URL for scene video
        video_url = get_scene_s3_url(
            brand_id=str(campaign.brand_id),
            product_id=str(campaign.product_id),
            campaign_id=str(campaign_id),
            variation_index=variation_index,
            scene_index=i
        )
        
        scene_infos.append(SceneInfo(
            scene_index=i,
            scene_id=scene.get('scene_id', i),
            role=scene.get('role', 'unknown'),
            duration=scene.get('duration', 4),
            background_prompt=scene.get('background_prompt', ''),
            video_url=video_url,
            thumbnail_url=None,  # TODO: Generate thumbnails
            edit_count=scene.get('edit_count', 0),
            last_edited_at=scene.get('last_edited_at')
        ))
    
    return scene_infos


@router.post("/{campaign_id}/scenes/{scene_index}/edit", response_model=EditSceneResponse)
async def edit_scene(
    campaign_id: UUID,
    scene_index: int,
    request: EditSceneRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_ownership)
):
    """
    Edit a specific scene in a campaign.
    
    Enqueues an edit job and returns job ID for status polling.
    """
    if not worker_config:
        raise HTTPException(
            status_code=503,
            detail="Worker not available. Redis connection required."
        )
    
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_json = campaign.campaign_json
    if isinstance(campaign_json, str):
        import json
        campaign_json = json.loads(campaign_json)
    
    scenes = campaign_json.get('scenes', [])
    if scene_index >= len(scenes):
        raise HTTPException(status_code=400, detail=f"Scene index {scene_index} out of range")
    
    if not request.edit_prompt.strip():
        raise HTTPException(status_code=400, detail="Edit prompt cannot be empty")
    
    # Enqueue edit job
    job = worker_config.enqueue_edit_job(
        campaign_id=str(campaign_id),
        scene_index=scene_index,
        edit_instruction=request.edit_prompt
    )
    
    return EditSceneResponse(
        job_id=job.id,
        estimated_cost=0.21,  # $0.01 LLM + $0.20 video
        estimated_duration_seconds=180,  # ~3 minutes
        message=f"Edit job enqueued for scene {scene_index}"
    )


@router.get("/{campaign_id}/edit-history", response_model=List[EditHistoryRecord])
async def get_edit_history(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_ownership)
):
    """
    Get edit history for a campaign.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_json = campaign.campaign_json
    if isinstance(campaign_json, str):
        import json
        campaign_json = json.loads(campaign_json)
    
    edit_history = campaign_json.get('edit_history', {})
    edits = edit_history.get('edits', [])
    
    return [EditHistoryRecord(**edit) for edit in edits]


@router.get("/{campaign_id}/scenes/{scene_index}/stream")
async def stream_scene_video(
    campaign_id: UUID,
    scene_index: int,
    variation_index: int = Query(0, description="Variation index (0, 1, 2)"),
    request: Request = None,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_ownership)
):
    """
    Stream a scene video file for playback in the browser (with CORS support).
    
    This endpoint streams the scene video file from S3 through the backend,
    adding proper CORS headers to allow frontend video players to access it.
    
    **Path Parameters:**
    - campaign_id: UUID of the campaign
    - scene_index: Scene index (0-based)
    
    **Query Parameters:**
    - variation_index: Variation index (0, 1, 2). Defaults to 0.
    
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
    - 400: Invalid scene index
    """
    try:
        # Get campaign and verify ownership (done via dependency)
        campaign = get_campaign_by_id(db, campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Validate scene index
        campaign_json = campaign.campaign_json
        if isinstance(campaign_json, str):
            import json
            campaign_json = json.loads(campaign_json)
        
        scenes = campaign_json.get('scenes', [])
        if scene_index < 0 or scene_index >= len(scenes):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scene index: {scene_index}. Must be between 0 and {len(scenes) - 1}"
            )
        
        # Validate variation index
        if variation_index < 0:
            raise HTTPException(status_code=400, detail="Invalid variation index")
        
        # Construct S3 key for scene video
        # Format: brands/{brand_id}/products/{product_id}/campaigns/{campaign_id}/variation_{i}/draft/scene_{scene_index+1}_bg.mp4
        s3_key = (
            f"brands/{str(campaign.brand_id)}/products/{str(campaign.product_id)}/campaigns/{str(campaign_id)}/"
            f"variation_{variation_index}/draft/scene_{scene_index+1}_bg.mp4"
        )
        
        logger.info(f"🎬 Streaming scene video from S3: {s3_key} (scene {scene_index}, variation {variation_index})")
        
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
            if request:
                range_header = request.headers.get('range')
            
            if range_header:
                # Parse range header (e.g., "bytes=0-1023")
                range_match = range_header.replace('bytes=', '').split('-')
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else content_length - 1
                
                # Validate range
                if start < 0 or end >= content_length or start > end:
                    raise HTTPException(status_code=416, detail="Range Not Satisfiable")
                
                # Get partial content
                response = s3_client.get_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Range=f'bytes={start}-{end}'
                )
                video_data = response['Body'].read()
                actual_length = end - start + 1
                
                return StreamingResponse(
                    iter([video_data]),
                    status_code=206,  # Partial Content
                    media_type=content_type,
                    headers={
                        'Content-Range': f'bytes {start}-{end}/{content_length}',
                        'Accept-Ranges': 'bytes',
                        'Content-Length': str(actual_length),
                        'ETag': etag,
                        'Cache-Control': 'public, max-age=31536000',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                        'Access-Control-Allow-Headers': 'Range, Content-Type, Authorization',
                    }
                )
            else:
                # Get full content
                response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
                video_data = response['Body'].read()
                
                return StreamingResponse(
                    iter([video_data]),
                    media_type=content_type,
                    headers={
                        'Content-Length': str(content_length),
                        'Accept-Ranges': 'bytes',
                        'ETag': etag,
                        'Cache-Control': 'public, max-age=31536000',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                        'Access-Control-Allow-Headers': 'Range, Content-Type, Authorization',
                    }
                )
                
        except s3_client.exceptions.NoSuchKey:
            logger.error(f"❌ Scene video not found in S3: {s3_key}")
            raise HTTPException(
                status_code=404,
                detail=f"Scene video not found (scene {scene_index}, variation {variation_index})"
            )
        except Exception as e:
            logger.error(f"❌ Error streaming scene video from S3: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stream scene video: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in stream_scene_video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

