"""API endpoints for campaign editing."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel
import logging
import boto3
from io import BytesIO
import json

from app.database.connection import get_db
from app.database.crud import get_campaign_by_id
from app.api.auth import verify_campaign_ownership, get_current_user_id
from app.config import settings
from app.database import crud

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
# Manual Editing Schemas
# ============================================================================

class MusicInfo(BaseModel):
    """Music information for manual editing."""
    audio_url: str
    duration: float


class TimelineClipState(BaseModel):
    """Timeline clip state for export."""
    id: str
    library_id: str
    name: str
    track_type: str
    duration: float
    trim_start: float
    trim_end: float
    effective_duration: float
    position: float


class TimelineState(BaseModel):
    """Timeline state for export."""
    video_clips: List[TimelineClipState]
    audio_clips: List[TimelineClipState]
    total_duration: float


class ExportEditRequest(BaseModel):
    """Request to export edited video."""
    timeline_state: TimelineState
    export_settings: Optional[Dict[str, Any]] = None


class ExportEditResponse(BaseModel):
    """Response when export job is enqueued."""
    job_id: str
    estimated_duration_seconds: int
    message: str


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
            brand_id=str(campaign.product.brand_id),
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
            f"brands/{str(campaign.product.brand_id)}/products/{str(campaign.product_id)}/campaigns/{str(campaign_id)}/"
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


# ============================================================================
# Manual Editing Endpoints
# ============================================================================

@router.get("/{campaign_id}/editing/scenes", response_model=List[SceneInfo])
async def get_editing_scenes(
    campaign_id: UUID,
    variation_index: int = Query(0, description="Variation index (0, 1, 2)"),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_ownership)
):
    """
    Get all scenes for manual editing.

    Returns scene data with video URLs for the timeline editor.
    If manual editing is already done, returns 400 error.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check if manual editing is already done
    if getattr(campaign, 'manual_editing_done', False):
        raise HTTPException(
            status_code=400,
            detail="Manual editing already completed. Scenes no longer available."
        )

    # Get scenes from campaign_json or scene_configs
    campaign_json = campaign.campaign_json
    if campaign_json:
        if isinstance(campaign_json, str):
            campaign_json = json.loads(campaign_json)
        scenes = campaign_json.get('scenes', [])
    else:
        # Fall back to scene_configs
        scene_configs = campaign.scene_configs
        if isinstance(scene_configs, str):
            scene_configs = json.loads(scene_configs)
        scenes = scene_configs if isinstance(scene_configs, list) else []

    from app.utils.s3_utils import get_scene_s3_url

    scene_infos = []
    for i, scene in enumerate(scenes):
        # Construct S3 URL for scene video
        video_url = get_scene_s3_url(
            brand_id=str(campaign.product.brand_id),
            product_id=str(campaign.product_id),
            campaign_id=str(campaign_id),
            variation_index=variation_index,
            scene_index=i
        )

        scene_infos.append(SceneInfo(
            scene_index=i,
            scene_id=scene.get('scene_id', i) if isinstance(scene, dict) else i,
            role=scene.get('role', 'unknown') if isinstance(scene, dict) else 'unknown',
            duration=scene.get('duration', 4) if isinstance(scene, dict) else 4,
            background_prompt=scene.get('background_prompt', '') if isinstance(scene, dict) else '',
            video_url=video_url,
            thumbnail_url=None,
            edit_count=scene.get('edit_count', 0) if isinstance(scene, dict) else 0,
            last_edited_at=scene.get('last_edited_at') if isinstance(scene, dict) else None
        ))

    return scene_infos


@router.get("/{campaign_id}/editing/music", response_model=MusicInfo)
async def get_editing_music(
    campaign_id: UUID,
    variation_index: int = Query(0, description="Variation index (0, 1, 2)"),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_ownership)
):
    """
    Get music/audio file for manual editing.

    Returns audio URL and duration for the timeline editor.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check if manual editing is already done
    if getattr(campaign, 'manual_editing_done', False):
        raise HTTPException(
            status_code=400,
            detail="Manual editing already completed. Music no longer available."
        )

    from app.utils.s3_utils import get_audio_s3_url

    audio_url = get_audio_s3_url(
        brand_id=str(campaign.product.brand_id),
        product_id=str(campaign.product_id),
        campaign_id=str(campaign_id),
        variation_index=variation_index
    )

    # Get duration from campaign_json if available
    campaign_json = campaign.campaign_json
    if campaign_json:
        if isinstance(campaign_json, str):
            campaign_json = json.loads(campaign_json)
        duration = campaign_json.get('audio_duration', campaign.duration or 30.0)
    else:
        duration = campaign.duration or 30.0

    return MusicInfo(audio_url=audio_url, duration=float(duration))


@router.post("/{campaign_id}/editing/export-upload")
async def export_manual_edit_upload(
    campaign_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    _: bool = Depends(verify_campaign_ownership)
):
    """
    Export manually edited video by uploading the final video file.

    This uses client-side recording (MediaRecorder API) and uploads
    the result to S3, then:
    1. Sets manual_editing_done = True
    2. Cleans up S3 draft files (scene videos, music)
    3. Keeps only final_video.mp4
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check if already finalized
    if getattr(campaign, 'manual_editing_done', False):
        raise HTTPException(
            status_code=400,
            detail="Manual editing already completed for this campaign."
        )

    try:
        # Read file content
        file_content = await file.read()

        # Determine content type
        content_type = file.content_type or 'video/webm'
        file_ext = '.webm' if 'webm' in content_type else '.mp4'

        # Get variation index from campaign or default to 0
        variation_index = getattr(campaign, 'selected_variation_index', 0) or 0

        # Construct S3 key for final video
        s3_key = (
            f"brands/{str(campaign.product.brand_id)}/products/{str(campaign.product_id)}/"
            f"campaigns/{str(campaign_id)}/variation_{variation_index}/final/edited_video{file_ext}"
        )

        logger.info(f"📤 Uploading edited video to S3: {s3_key}")

        from app.utils.s3_utils import get_s3_client
        s3_client = get_s3_client()
        bucket_name = settings.s3_bucket_name

        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type
        )

        # Construct final URL
        final_url = f"https://{bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"

        logger.info(f"✅ Uploaded edited video: {final_url}")

        # Update campaign: mark manual editing as done
        campaign.manual_editing_done = True

        # Update campaign_json with final video URL
        campaign_json = campaign.campaign_json or {}
        if isinstance(campaign_json, str):
            campaign_json = json.loads(campaign_json)
        campaign_json['edited_video_url'] = final_url
        campaign_json['editing_completed_at'] = str(datetime.utcnow())
        campaign.campaign_json = campaign_json

        db.commit()
        db.refresh(campaign)

        # Cleanup draft files in background (optional - can be done async)
        try:
            await _cleanup_s3_draft_files(campaign, variation_index)
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Failed to cleanup draft files: {cleanup_error}")
            # Don't fail the request if cleanup fails

        return {
            "success": True,
            "message": "Edited video uploaded successfully",
            "video_url": final_url,
            "manual_editing_done": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to upload edited video: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload edited video: {str(e)}"
        )


async def _cleanup_s3_draft_files(campaign, variation_index: int):
    """
    Helper function to cleanup S3 draft files after manual edit export.

    Removes scene videos and music from draft folder, keeping only final video.
    Uses product_id in S3 paths (not perfume_id).
    """
    from app.utils.s3_utils import get_s3_client

    s3_client = get_s3_client()
    bucket_name = settings.s3_bucket_name

    # Construct draft folder prefix
    draft_prefix = (
        f"brands/{str(campaign.product.brand_id)}/products/{str(campaign.product_id)}/"
        f"campaigns/{str(campaign.id)}/variation_{variation_index}/draft/"
    )

    logger.info(f"🧹 Cleaning up draft files: {draft_prefix}")

    try:
        # List all objects in draft folder
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=draft_prefix)

        objects_to_delete = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})

        if objects_to_delete:
            # Delete in batches of 1000 (S3 limit)
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': batch}
                )
            logger.info(f"✅ Deleted {len(objects_to_delete)} draft files")
        else:
            logger.info("ℹ️ No draft files to delete")

    except Exception as e:
        logger.error(f"❌ Error cleaning up draft files: {e}")
        raise


# Import datetime for timestamp
from datetime import datetime
