"""API endpoints for project management."""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.database.connection import get_db, init_db
from app.database.crud import (
    create_project,
    get_project,
    get_project_by_user,
    get_user_projects,
    update_project,
    update_project_s3_paths,
    update_project_status,
    delete_project,
    get_generation_stats
)
from app.models.schemas import (
    CreateProjectRequest,
    ProjectResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ErrorResponse
)
from app.api.auth import get_current_user_id
from app.utils.s3_utils import create_project_folder_structure, delete_project_folder

logger = logging.getLogger(__name__)

router = APIRouter()


# Note: get_current_user_id imported from app.api.auth


# ============================================================================
# CREATE Endpoints
# ============================================================================

@router.post("/", response_model=ProjectResponse)
async def create_new_project(
    request: CreateProjectRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Create a new ad generation project.
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Request Body:**
    - title: Project title (max 200 chars)
    - brief: Product brief/description (10-2000 chars)
    - duration: Video duration (15-120 seconds)
    - mood: Video mood (uplifting, dramatic, energetic, calm, luxurious, playful)
    - brand_name: Brand name (max 100 chars)
    - primary_color: Primary brand color (hex #RRGGBB or #RRGGBBAA)
    - secondary_color: (optional) Secondary brand color (hex)
    
    **Response:** ProjectResponse with newly created project
    
    **Errors:**
    - 400: Invalid input (validation errors)
    - 401: Missing or invalid authorization
    - 500: Database error
    
    **Example:**
    ```json
    {
      "title": "Summer Skincare Campaign",
      "brief": "Premium hydrating serum with SPF for sensitive skin",
      "duration": 30,
      "mood": "uplifting",
      "brand_name": "HydraGlow",
      "primary_color": "#4dbac7",
      "secondary_color": "#ffffff"
    }
    ```
    """
    try:
        # Initialize database if needed
        init_db()
        
        # Get current user from auth
        user_id = get_current_user_id(authorization)
        
        # Create brand config
        brand_config = {
            "name": request.brand_name,
            "primary_color": request.primary_color,
            "secondary_color": request.secondary_color or "",
            "font_family": "Inter"
        }
        
        # Create initial ad_project_json
        ad_project_json = {
            "version": "1.0",
            "brief": request.brief,
            "duration": request.duration,
            "mood": request.mood,
            "brand": brand_config,
            "product_asset": None,
            "style_spec": None,
            "scenes": [],
            "video_settings": {
                "aspect_ratios": ["9:16", "1:1", "16:9"],
                "resolution": "1080p",
                "fps": 30,
                "codec": "h264"
            },
            "audio_settings": {
                "include_music": True,
                "music_volume": -6.0,
                "enable_voiceover": False
            },
            "render_status": None
        }
        
        # Create project in database
        project = create_project(
            db=db,
            user_id=user_id,
            title=request.title,
            brief=request.brief,
            ad_project_json=ad_project_json,
            mood=request.mood,
            duration=request.duration
        )
        
        # S3 RESTRUCTURING: Initialize S3 folder structure for new project
        try:
            folders = await create_project_folder_structure(str(project.id))
            # Note: update_project_s3_paths is NOT async, don't await it
            update_project_s3_paths(
                db,
                project.id,
                folders["s3_folder"],
                folders["s3_url"]
            )
            logger.info(f"✅ Created project {project.id} with S3 folders at {folders['s3_url']}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize S3 folders for {project.id}: {e}")
            # Continue anyway - project created, S3 will be initialized during generation
        
        # Convert project to response - handle both DB and mock projects
        return ProjectResponse.model_validate({
            "id": project.id,
            "user_id": project.user_id,
            "title": project.title,
            "status": project.status,
            "progress": project.progress,
            "cost": float(project.cost) if project.cost else 0.0,
            "s3_project_folder": getattr(project, 's3_project_folder', None),
            "s3_project_folder_url": getattr(project, 's3_project_folder_url', None),
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        })
    
    except Exception as e:
        logger.error(f"❌ Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


# ============================================================================
# READ Endpoints
# ============================================================================

@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project_details(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Get detailed information about a specific project.
    
    **Path Parameters:**
    - project_id: UUID of the project
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** ProjectDetailResponse with full configuration
    
    **Errors:**
    - 404: Project not found
    - 403: Not authorized to view this project
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get project and verify ownership
        project = get_project_by_user(db, project_id, user_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectDetailResponse.from_orm(project)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.get("/", response_model=ProjectListResponse)
async def list_user_projects(
    limit: int = Query(50, ge=1, le=100, description="Max projects to return"),
    offset: int = Query(0, ge=0, description="Number of projects to skip"),
    status: str = Query(None, description="Filter by status (optional)"),
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    List all projects for the current user with pagination.
    
    **Query Parameters:**
    - limit: Maximum number of projects (1-100, default 50)
    - offset: Number of projects to skip (default 0)
    - status: (optional) Filter by status (PENDING, QUEUED, EXTRACTING_PRODUCT, PLANNING, GENERATING_SCENES, COMPOSITING, ADDING_OVERLAYS, GENERATING_AUDIO, RENDERING, COMPLETED, FAILED)
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** ProjectListResponse with list of projects
    
    **Errors:**
    - 400: Invalid query parameters
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get projects
        projects = get_user_projects(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status
        )
        
        # Count total (for pagination info)
        total = len(projects)  # In production, use a separate count query
        
        # Convert projects to response - handle both DB and mock projects
        response_projects = [
            ProjectResponse.model_validate({
                "id": p.id,
                "user_id": p.user_id,
                "title": p.title,
                "status": p.status,
                "progress": p.progress,
                "cost": float(p.cost) if p.cost else 0.0,
                "s3_project_folder": getattr(p, 's3_project_folder', None),
                "s3_project_folder_url": getattr(p, 's3_project_folder_url', None),
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            })
            for p in projects
        ]
        
        return ProjectListResponse(
            total=total,
            limit=limit,
            offset=offset,
            projects=response_projects
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/stats/summary", response_model=dict)
async def get_user_stats(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Get generation statistics for the current user.
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:**
    ```json
    {
      "total_projects": 10,
      "completed": 8,
      "failed": 1,
      "in_progress": 1,
      "total_cost": 8.50,
      "success_rate": 80.0
    }
    ```
    
    **Errors:**
    - 401: Missing or invalid authorization
    - 500: Database error
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        stats = get_generation_stats(db, user_id)
        
        return stats
    
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ============================================================================
# UPDATE Endpoints
# ============================================================================

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project_details(
    project_id: UUID,
    request: dict,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Update project details (title, brief, etc).
    
    **Path Parameters:**
    - project_id: UUID of the project
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Request Body:**
    - Flexible: any project fields to update
    
    **Response:** Updated ProjectResponse
    
    **Errors:**
    - 404: Project not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Verify ownership
        project = get_project_by_user(db, project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update project
        updated = update_project(db, project_id, **request)
        
        if not updated:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse.from_orm(updated)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


# ============================================================================
# DELETE Endpoints
# ============================================================================

@router.delete("/{project_id}")
async def delete_project_endpoint(
    project_id: UUID,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """
    Delete a project (only if owned by current user).
    
    Also deletes all S3 files associated with the project.
    
    **Path Parameters:**
    - project_id: UUID of the project to delete
    
    **Headers:**
    - Authorization: Bearer {token} (optional in development)
    
    **Response:** {"status": "deleted", "project_id": "...", "s3_cleaned": true/false}
    
    **Errors:**
    - 404: Project not found
    - 403: Not authorized
    - 401: Missing or invalid authorization
    """
    try:
        init_db()
        
        user_id = get_current_user_id(authorization)
        
        # Get project to retrieve S3 folder path
        project = get_project_by_user(db, project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or not authorized")
        
        # S3 RESTRUCTURING: Delete S3 folder and all contents
        s3_cleaned = False
        if project.s3_project_folder:
            try:
                s3_cleaned = await delete_project_folder(str(project_id))
                if s3_cleaned:
                    logger.info(f"✅ Deleted S3 folder: {project.s3_project_folder}")
                else:
                    logger.warning(f"⚠️ Partial S3 cleanup for {project_id}")
            except Exception as e:
                logger.error(f"⚠️ S3 cleanup error (non-critical): {e}")
                # Continue with database deletion anyway
        
        # Delete project from database
        success = delete_project(db, project_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found or not authorized")
        
        return {
            "status": "deleted",
            "project_id": str(project_id),
            "s3_cleaned": s3_cleaned
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")



