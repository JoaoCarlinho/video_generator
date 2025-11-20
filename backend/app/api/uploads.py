"""File upload endpoints for local filesystem storage."""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from pydantic import BaseModel

from app.api.auth import get_current_user_id
from app.config import settings
from app.database.crud import get_project

router = APIRouter()
logger = logging.getLogger(__name__)

# Base upload directory
UPLOAD_BASE_DIR = Path("/tmp/genads")
UPLOAD_BASE_DIR.mkdir(parents=True, exist_ok=True)

class UploadResponse(BaseModel):
    file_path: str
    file_url: str  # For backwards compatibility, returns local path

@router.post("/upload-asset", response_model=UploadResponse, summary="Upload asset file to S3")
async def upload_asset(
    file: UploadFile = File(...),
    asset_type: str = Form(...),  # 'product', 'logo', 'guidelines'
    project_id: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None)
):
    """
    Upload an asset file (product image, logo, or guidelines) to S3.

    Files are uploaded to: s3://bucket/projects/{project_id}/input/{asset_type}/

    Args:
        file: The file to upload
        asset_type: Type of asset ('product', 'logo', 'guidelines')
        project_id: Optional project ID (if not provided, uses 'temp')
        authorization: JWT token for authentication

    Returns:
        S3 URL where the file was saved
    """
    try:
        from app.utils.s3_utils import upload_to_project_folder

        # Get user ID from auth token
        user_id = get_current_user_id(authorization)

        # Validate asset type
        if asset_type not in ['product', 'logo', 'guidelines']:
            raise HTTPException(status_code=400, detail=f"Invalid asset_type: {asset_type}")

        # Read file contents
        contents = await file.read()
        logger.info(f"Uploading {asset_type} file ({len(contents)} bytes) to S3")

        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"

        # Upload to S3
        # Map asset types to S3 subfolders
        subfolder = f"input/{asset_type}"
        proj_id = project_id if project_id else user_id  # Use user_id for temp uploads

        s3_result = await upload_to_project_folder(
            file_content=contents,
            project_id=str(proj_id),
            subfolder=subfolder,
            filename=unique_filename
        )

        logger.info(f"✅ Uploaded {len(contents)} bytes to S3: {s3_result['s3_key']}")

        return UploadResponse(
            file_path=s3_result['s3_key'],  # S3 key
            file_url=s3_result['url']  # S3 URL
        )

    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.delete("/cleanup-project/{project_id}", summary="Cleanup project temporary files")
async def cleanup_project_files(
    project_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Delete all temporary files for a project.
    Called after video generation completes or project is deleted.
    """
    try:
        user_id = get_current_user_id(authorization)
        
        project_dir = UPLOAD_BASE_DIR / str(user_id) / project_id
        
        if not project_dir.exists():
            return {"message": "No files to cleanup", "deleted_count": 0}
        
        # Count and delete all files
        deleted_count = 0
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                file_path.unlink()
                deleted_count += 1
        
        # Remove empty directories
        for dir_path in sorted(project_dir.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
        
        # Remove project directory
        if project_dir.exists():
            project_dir.rmdir()
        
        logger.info(f"✅ Cleaned up {deleted_count} files for project {project_id}")
        return {"message": f"Cleaned up {deleted_count} files", "deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"Failed to cleanup files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup files: {str(e)}")


class ReferenceImageUploadResponse(BaseModel):
    success: bool
    message: str


@router.post("/projects/{project_id}/reference-image", response_model=ReferenceImageUploadResponse)
async def upload_reference_image(
    project_id: str,
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """
    Upload reference image for visual style extraction.
    
    The reference image is saved locally and will be processed during generation
    to extract visual style (colors, lighting, mood, camera, atmosphere, texture).
    
    Args:
        project_id: Project UUID
        file: Reference image file (JPEG, PNG)
        authorization: JWT token
        
    Returns:
        Success message. Style extraction happens during generation.
    """
    try:
        from app.database.connection import get_db, init_db
        from sqlalchemy.orm import Session
        from contextlib import contextmanager
        from datetime import datetime
        
        # Initialize DB if needed
        init_db()
        
        # Get user ID
        user_id = get_current_user_id(authorization)
        logger.info(f"📤 Uploading reference image for project {project_id}")
        
        # Validate file size (max 5MB)
        MAX_SIZE = 5 * 1024 * 1024
        file_content = await file.read()
        if len(file_content) > MAX_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")
        
        # Validate file type (accept JPEG, PNG, WebP)
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP files allowed")
        
        # Get project to verify ownership
        db_gen = get_db()
        session = next(db_gen)
        try:
            project = get_project(session, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            if project.user_id != user_id:
                raise HTTPException(status_code=403, detail="Unauthorized")
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
        
        # Create project input directory
        project_input_dir = UPLOAD_BASE_DIR / str(project_id) / "input"
        project_input_dir.mkdir(parents=True, exist_ok=True)
        
        # Save reference image
        reference_image_path = project_input_dir / "reference_image.jpg"
        reference_image_path.write_bytes(file_content)
        
        logger.info(f"✅ Saved reference image: {reference_image_path}")
        
        # Update project JSON with reference image path
        db_gen = get_db()
        session = next(db_gen)
        try:
            project = get_project(session, project_id)
            
            if project.ad_project_json is None:
                project.ad_project_json = {}
            
            project.ad_project_json["referenceImage"] = {
                "localPath": str(reference_image_path),
                "uploadedAt": datetime.now().isoformat(),
            }
            
            session.commit()
            logger.info(f"✅ Updated project JSON with reference image path")
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
        
        return ReferenceImageUploadResponse(
            success=True,
            message="Reference image uploaded successfully."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to upload reference image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

