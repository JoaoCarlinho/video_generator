"""Local-first video generation endpoints.

Handles preview from local storage and finalization to S3.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.database.connection import get_db, init_db
from app.database.crud import get_project_by_user, update_project_status
from app.api.auth import get_current_user_id
from app.utils.local_storage import LocalStorageManager, format_storage_size
# S3 imports removed - using local storage only

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/preview")
async def get_preview_video(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """Get preview video from S3 or local storage.

    Tries S3 first (output_videos field), falls back to local storage if needed.
    Returns a redirect to S3 URL for efficient video delivery.

    **Path Parameters:**
    - project_id: UUID of the project

    **Response:**
    - 307 Redirect to S3 URL OR
    - Content-Type: video/mp4 (streamed from local if S3 unavailable)

    **Errors:**
    - 404: Project not found or video not available
    - 403: Not authorized
    """
    try:
        init_db()
        user_id = get_current_user_id(authorization)

        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # PRIORITY 1: Check S3 URLs (output_videos field)
        s3_video_urls = project.output_videos or {}
        if s3_video_urls:
            # Get the first available S3 URL
            s3_url = next((url for url in s3_video_urls.values() if url), None)
            if s3_url:
                logger.info(f"✅ Redirecting to S3 preview: {s3_url}")
                # Return 307 redirect to S3 URL
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=s3_url, status_code=307)

        # FALLBACK: Check local storage
        local_video_paths = project.local_video_paths or {}
        local_video_path = next(iter(local_video_paths.values()), None) if local_video_paths else None

        if local_video_path and LocalStorageManager.file_exists(local_video_path):
            logger.info(f"✅ Streaming preview from local storage (S3 not available): {local_video_path}")
            return FileResponse(
                local_video_path,
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f"inline; filename=preview.mp4",
                    "Cache-Control": "no-cache"
                }
            )

        # No video found anywhere
        raise HTTPException(
            status_code=404,
            detail=f"Preview video not available"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get preview video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get preview video: {str(e)}")


@router.get("/projects/{project_id}/storage-info")
async def get_storage_info(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """Get local storage information for a project.
    
    Returns storage usage and status.
    
    **Response:**
    ```json
    {
        "project_id": "...",
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
        
        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Calculate storage size
        storage_size = LocalStorageManager.get_project_storage_size(project_id)
        
        return {
            "project_id": str(project_id),
            "local_storage_size": storage_size,
            "local_storage_size_formatted": format_storage_size(storage_size),
            "status": project.status,
            "local_video_paths": project.local_video_paths or {},
            "has_all_aspects": all(
                v in (project.local_video_paths or {})
                for v in ['16:9']
            )
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get storage info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get storage info: {str(e)}")


@router.post("/projects/{project_id}/finalize")
async def finalize_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """Finalize video: mark as finalized and keep videos in local storage.
    
    Called when user confirms they want to keep the video.
    - Marks project as FINALIZED
    - Keeps videos in local storage (no S3 upload)
    - Videos remain accessible via preview endpoint
    
    **Path Parameters:**
    - project_id: UUID of the project
    
    **Response:**
    ```json
    {
        "status": "finalized",
        "project_id": "...",
        "local_video_paths": {
            "16:9": "/tmp/genads/.../video_16-9.mp4"
        },
        "message": "Project finalized. Videos remain in local storage."
    }
    ```
    
    **Errors:**
    - 404: Project not found
    - 403: Not authorized
    - 400: Project not ready for finalization
    """
    try:
        init_db()
        user_id = get_current_user_id(authorization)
        
        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if project is ready for finalization
        if project.status not in ['READY_FOR_REVIEW', 'COMPLETED']:
            raise HTTPException(
                status_code=400,
                detail=f"Project cannot be finalized in status: {project.status}"
            )
        
        # Get local video paths
        local_video_paths = project.local_video_paths or {}
        if not local_video_paths:
            raise HTTPException(
                status_code=400,
                detail="No videos available for finalization"
            )
        
        logger.info(f"🚀 Finalizing project {project_id} (keeping videos in local storage)")
        
        # Update project status to FINALIZED (keep videos in local storage)
        project.status = 'FINALIZED'
        db.commit()
        
        logger.info(f"✅ Updated project status to FINALIZED")
        
        return {
            "status": "finalized",
            "project_id": str(project_id),
            "local_video_paths": local_video_paths,
            "message": "Project finalized. Videos remain in local storage."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to finalize project: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to finalize project: {str(e)}"
        )


@router.post("/projects/{project_id}/cleanup-local")
async def cleanup_local_storage(
    project_id: UUID,
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
        
        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Clear local storage metadata
        project.local_project_path = None
        project.local_video_paths = {}
        project.local_input_files = {}
        project.local_draft_files = {}
        db.commit()
        
        # Delete files from disk
        success = LocalStorageManager.cleanup_project_storage(project_id)
        
        return {
            "status": "cleaned",
            "project_id": str(project_id),
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

