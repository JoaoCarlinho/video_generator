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

router = APIRouter()
logger = logging.getLogger(__name__)

# Base upload directory
UPLOAD_BASE_DIR = Path("/tmp/genads")
UPLOAD_BASE_DIR.mkdir(parents=True, exist_ok=True)

class UploadResponse(BaseModel):
    file_path: str
    file_url: str  # For backwards compatibility, returns local path

@router.post("/upload-asset", response_model=UploadResponse, summary="Upload asset file to local filesystem")
async def upload_asset(
    file: UploadFile = File(...),
    asset_type: str = Form(...),  # 'product', 'logo', 'guidelines'
    project_id: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None)
):
    """
    Upload an asset file (product image, logo, or guidelines) to local filesystem.
    
    Files are stored in: /tmp/genads/{user_id}/{project_id or 'temp'}/{asset_type}/
    
    Args:
        file: The file to upload
        asset_type: Type of asset ('product', 'logo', 'guidelines')
        project_id: Optional project ID (if not provided, uses 'temp')
        authorization: JWT token from Supabase
    
    Returns:
        Local file path where the file was saved
    """
    try:
        # Get user ID from auth token
        user_id = get_current_user_id(authorization)
        
        # Validate asset type
        if asset_type not in ['product', 'logo', 'guidelines']:
            raise HTTPException(status_code=400, detail=f"Invalid asset_type: {asset_type}")
        
        # Create directory structure: /tmp/genads/{user_id}/{project_id}/{asset_type}/
        proj_id = project_id if project_id else "temp"
        upload_dir = UPLOAD_BASE_DIR / str(user_id) / proj_id / asset_type
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file to disk
        logger.info(f"Saving {asset_type} file to {file_path}")
        contents = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"✅ Saved {len(contents)} bytes to {file_path}")
        
        return UploadResponse(
            file_path=str(file_path),
            file_url=str(file_path)  # Return local path
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

