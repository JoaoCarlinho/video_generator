"""API endpoints for campaign editing."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.database.connection import get_db
from app.database.crud import get_campaign_by_id
from app.api.auth import verify_campaign_ownership
from app.jobs.worker import create_worker

router = APIRouter(prefix="/api/campaigns", tags=["editing"])

# Initialize worker config
try:
    worker_config = create_worker()
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Failed to initialize worker config: {e}")
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
            perfume_id=str(campaign.perfume_id),
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

