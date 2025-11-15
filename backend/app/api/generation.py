"""API endpoints for generation control."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from rq.job import Job

from app.database.connection import get_db, init_db
from app.database.crud import get_project_by_user, update_project_status
from app.models.schemas import GenerationProgressResponse
from app.jobs.worker import create_worker
from app.api.auth import get_current_user_id

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

@router.post("/projects/{project_id}/generate", deprecated=False)
@router.post("/projects/{project_id}/generate/", deprecated=False)
async def trigger_generation(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Trigger video generation for a project.
    
    **Path Parameters:**
    - project_id: UUID of the project to generate
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** 
    ```json
    {
        "status": "queued",
        "job_id": "...",
        "message": "Generation job enqueued",
        "project_id": "..."
    }
    ```
    
    **Errors:**
    - 404: Project not found
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
        
        user_id = get_current_user_id(authorization)
        
        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if already generating (allow retry from QUEUED or FAILED)
        if project.status not in ["PENDING", "QUEUED", "FAILED"]:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot start generation: project is in state '{project.status}'. Only PENDING, QUEUED, or FAILED projects can be generated."
            )
        
        # Enqueue job with RQ
        job = worker_config.enqueue_job(str(project_id))
        
        # Update project status
        update_project_status(
            db,
            project_id,
            "QUEUED",
            progress=0
        )
        
        logger.info(f"✅ Enqueued generation for project {project_id}, job_id={job.id}")
        
        return {
            "status": "queued",
            "job_id": str(job.id),
            "message": "Generation job enqueued",
            "project_id": str(project_id)
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


@router.post("/projects/{project_id}/reset")
async def reset_project_status(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Reset a stuck project to FAILED status so it can be retried.
    
    Useful when a project gets stuck in an intermediate state (e.g., EXTRACTING_PRODUCT, 
    GENERATING_SCENES, etc.) and needs to be reset.
    
    **Path Parameters:**
    - project_id: UUID of the project to reset
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:**
    ```json
    {
        "status": "reset",
        "project_id": "...",
        "message": "Project reset to FAILED status. You can now retry generation."
    }
    ```
    
    **Errors:**
    - 404: Project not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Reset to FAILED status
        update_project_status(
            db,
            project_id,
            "FAILED",
            progress=0,
            error_message="Manually reset - ready for retry"
        )
        
        logger.info(f"✅ Reset project {project_id} to FAILED status")
        
        return {
            "status": "reset",
            "project_id": str(project_id),
            "message": "Project reset to FAILED status. You can now retry generation."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reset project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset project: {str(e)}")


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


@router.get("/projects/{project_id}/progress", response_model=GenerationProgressResponse)
async def get_generation_progress(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Get current generation progress for a project.
    
    **Path Parameters:**
    - project_id: UUID of the project
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** GenerationProgressResponse with current status
    
    **Example Response:**
    ```json
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "GENERATING_SCENES",
      "progress": 25,
      "current_step": "Generating Video Scenes",
      "cost_so_far": 0.12,
      "error_message": null
    }
    ```
    
    **Errors:**
    - 404: Project not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Map status to readable step
        step_map = {
            "PENDING": "Pending",
            "EXTRACTING_PRODUCT": "Extracting Product",
            "PLANNING": "Planning Scenes",
            "GENERATING_SCENES": "Generating Video Scenes",
            "COMPOSITING": "Compositing Product",
            "ADDING_OVERLAYS": "Adding Text Overlays",
            "GENERATING_AUDIO": "Generating Background Music",
            "RENDERING": "Rendering Final Video",
            "COMPLETED": "Completed",
            "FAILED": "Failed"
        }
        
        return GenerationProgressResponse(
            project_id=project.id,
            status=project.status,
            progress=project.progress,
            current_step=step_map.get(project.status, project.status),
            cost_so_far=float(project.cost),
            error_message=project.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get progress for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.post("/projects/{project_id}/cancel")
async def cancel_generation(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Cancel an in-progress generation (if possible).
    
    **Path Parameters:**
    - project_id: UUID of the project
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:**
    ```json
    {
        "status": "cancelled",
        "project_id": "...",
        "message": "Generation cancelled"
    }
    ```
    
    **Errors:**
    - 404: Project not found
    - 403: Not authorized
    - 409: Cannot cancel (not in progress)
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if generation is in progress
        if project.status == "COMPLETED":
            raise HTTPException(status_code=409, detail="Cannot cancel completed project")
        
        if project.status == "FAILED":
            raise HTTPException(status_code=409, detail="Cannot cancel failed project")
        
        if project.status == "PENDING":
            raise HTTPException(status_code=409, detail="Generation not started")
        
        # TODO: Cancel RQ job
        # For now, just mark as failed
        update_project_status(
            db,
            project_id,
            "FAILED",
            error_message="Cancelled by user"
        )
        
        logger.info(f"✅ Cancelled generation for project {project_id}")
        
        return {
            "status": "cancelled",
            "project_id": str(project_id),
            "message": "Generation cancelled"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cancel generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel generation: {str(e)}")


