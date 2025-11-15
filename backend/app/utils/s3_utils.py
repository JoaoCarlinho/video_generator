"""
S3 utilities for file uploads and management.
Handles product image uploads and S3 integration.
"""

import logging
import boto3
from typing import Optional
import os
from uuid import uuid4

from app.config import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    """
    Get S3 client configured with AWS credentials.
    
    **Returns:**
    - boto3.client: Configured S3 client
    
    **Raises:**
    - RuntimeError: If AWS credentials not configured
    """
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        raise RuntimeError("AWS credentials not configured in .env")
    
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key
    )


async def upload_product_image(
    file_content: bytes,
    filename: str,
    project_id: str
) -> dict:
    """
    Upload product image to S3.
    
    **Arguments:**
    - file_content: File bytes to upload
    - filename: Original filename
    - project_id: Project UUID (used in S3 path)
    
    **Returns:**
    - dict: {
        "url": "https://s3.amazonaws.com/...",
        "s3_key": "products/...",
        "size_bytes": 123456,
        "filename": "product.jpg"
      }
    
    **Raises:**
    - RuntimeError: If upload fails
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")
        
        # Generate S3 key
        file_ext = os.path.splitext(filename)[1].lower()
        s3_key = f"products/{project_id}/{uuid4()}{file_ext}"
        
        # Upload to S3
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=get_content_type(file_ext),
            ACL="public-read"
        )
        
        # Generate public URL
        s3_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
        
        logger.info(f"✅ Uploaded product image: {s3_key}")
        
        return {
            "url": s3_url,
            "s3_key": s3_key,
            "size_bytes": len(file_content),
            "filename": filename
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to upload product image: {e}")
        raise RuntimeError(f"Failed to upload image: {str(e)}")


def get_content_type(file_ext: str) -> str:
    """
    Get MIME type for file extension.
    
    **Arguments:**
    - file_ext: File extension including dot (e.g., ".jpg")
    
    **Returns:**
    - str: MIME type
    """
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif"
    }
    return mime_types.get(file_ext, "application/octet-stream")


def validate_image_file(
    filename: str,
    file_size: int,
    max_size_mb: int = 10
) -> dict:
    """
    Validate product image file.
    
    **Arguments:**
    - filename: Original filename
    - file_size: File size in bytes
    - max_size_mb: Maximum file size in MB
    
    **Returns:**
    - dict: {"valid": bool, "error": "message or None"}
    
    **Validation:**
    - Only jpg, png, webp, gif allowed
    - Maximum size: 10MB
    """
    # Check extension
    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in allowed_ext:
        return {
            "valid": False,
            "error": f"File type not allowed. Only {', '.join(allowed_ext)} accepted"
        }
    
    # Check size
    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return {
            "valid": False,
            "error": f"File too large. Maximum {max_size_mb}MB allowed"
        }
    
    return {"valid": True, "error": None}


def delete_s3_file(s3_key: str) -> bool:
    """
    Delete a file from S3.
    
    **Arguments:**
    - s3_key: S3 object key (e.g., "products/xxx/file.jpg")
    
    **Returns:**
    - bool: True if deleted, False if error
    """
    try:
        if not settings.s3_bucket_name:
            logger.warning("S3_BUCKET_NAME not configured")
            return False
        
        s3 = get_s3_client()
        s3.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key
        )
        
        logger.info(f"✅ Deleted S3 file: {s3_key}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to delete S3 file {s3_key}: {e}")
        return False


def get_s3_file_url(s3_key: str) -> str:
    """
    Generate public URL for S3 file.
    
    **Arguments:**
    - s3_key: S3 object key
    
    **Returns:**
    - str: Public HTTPS URL
    """
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"


# ============================================================================
# S3 RESTRUCTURING: Per-project folder organization
# ============================================================================

async def create_project_folder_structure(project_id: str) -> dict:
    """
    Initialize project folder structure in S3.
    
    Creates the path structure for a new project:
    - projects/{project_id}/draft/ (for working files)
    - projects/{project_id}/final/ (for final rendered videos)
    
    S3 doesn't require explicit folder creation, just prefix usage.
    This function validates access and returns folder information.
    
    **Arguments:**
    - project_id: UUID of the project (as string)
    
    **Returns:**
    - dict: {
        "s3_folder": "projects/550e8400-...",
        "s3_url": "https://bucket.s3.../projects/550e8400-...",
        "draft_folder": "projects/550e8400-.../draft/",
        "draft_url": "https://bucket.s3.../projects/550e8400-.../draft/",
        "final_folder": "projects/550e8400-.../final/",
        "final_url": "https://bucket.s3.../projects/550e8400-.../final/",
        "subfolders": {...}
      }
    """
    try:
        project_folder = f"projects/{project_id}/"
        s3_url = get_s3_folder_url(project_folder)
        
        logger.info(f"✅ Initialized folder structure for project {project_id}")
        
        return {
            "s3_folder": project_folder,
            "s3_url": s3_url,
            "draft_folder": f"{project_folder}draft/",
            "draft_url": get_s3_folder_url(f"{project_folder}draft/"),
            "final_folder": f"{project_folder}final/",
            "final_url": get_s3_folder_url(f"{project_folder}final/"),
            "subfolders": {
                "product": f"{project_folder}draft/product/",
                "scene_videos": f"{project_folder}draft/scene_videos/",
                "composited_videos": f"{project_folder}draft/composited_videos/",
                "text_overlays": f"{project_folder}draft/text_overlays/",
                "music": f"{project_folder}draft/music/",
                "final": f"{project_folder}final/",
            }
        }
    except Exception as e:
        logger.error(f"❌ Failed to initialize folder structure: {e}")
        raise RuntimeError(f"Failed to create folder structure: {str(e)}")


def get_s3_folder_url(folder_path: str) -> str:
    """
    Generate public HTTPS URL for S3 folder.
    
    **Arguments:**
    - folder_path: S3 key prefix (e.g., "projects/{id}/draft/")
    
    **Returns:**
    - str: Public HTTPS URL
    """
    if not folder_path.endswith('/'):
        folder_path += '/'
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{folder_path}"


async def upload_to_project_folder(
    file_content: bytes,
    project_id: str,
    subfolder: str,
    filename: str
) -> dict:
    """
    Upload file to project-specific folder in S3.
    
    Automatically organizes files by project and subfolder.
    
    **Arguments:**
    - file_content: File bytes to upload
    - project_id: Project UUID (as string)
    - subfolder: Subfolder within project (e.g., "draft/product", "draft/scene_videos")
    - filename: Filename (can include extension)
    
    **Returns:**
    - dict: {
        "url": "https://...",
        "s3_key": "projects/.../...",
        "size_bytes": 12345,
        "filename": "..."
      }
    
    **Raises:**
    - RuntimeError: If upload fails
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")
        
        # Build S3 key
        s3_key = f"projects/{project_id}/{subfolder}/{filename}"
        
        # Upload to S3
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=get_content_type(os.path.splitext(filename)[1]),
            ACL="public-read"
        )
        
        # Generate URL
        s3_url = get_s3_file_url(s3_key)
        
        logger.info(f"✅ Uploaded to project folder: {s3_key}")
        
        return {
            "url": s3_url,
            "s3_key": s3_key,
            "size_bytes": len(file_content),
            "filename": filename
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to upload to project folder: {e}")
        raise RuntimeError(f"Upload failed: {str(e)}")


async def delete_project_folder(project_id: str) -> bool:
    """
    Recursively delete all files in project folder.
    
    Deletes entire project folder including all draft and final files.
    Called when user deletes a project.
    
    **Arguments:**
    - project_id: Project UUID (as string)
    
    **Returns:**
    - bool: True if successful, False if failed
    """
    try:
        if not settings.s3_bucket_name:
            logger.warning("S3_BUCKET_NAME not configured")
            return False
        
        s3 = get_s3_client()
        folder_prefix = f"projects/{project_id}/"
        
        # List all objects with this prefix
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=settings.s3_bucket_name,
            Prefix=folder_prefix
        )
        
        delete_count = 0
        error_count = 0
        
        # Delete in batches of 1000 (S3 limit per delete call)
        for page in pages:
            if 'Contents' not in page:
                continue
            
            objects_to_delete = [
                {'Key': obj['Key']} 
                for obj in page['Contents']
            ]
            
            if objects_to_delete:
                try:
                    response = s3.delete_objects(
                        Bucket=settings.s3_bucket_name,
                        Delete={'Objects': objects_to_delete}
                    )
                    deleted = response.get('Deleted', [])
                    delete_count += len(deleted)
                    
                    # Track any errors
                    errors = response.get('Errors', [])
                    if errors:
                        error_count += len(errors)
                        logger.warning(f"⚠️ {len(errors)} files failed to delete")
                except Exception as e:
                    logger.error(f"❌ Batch delete error: {e}")
                    error_count += len(objects_to_delete)
        
        logger.info(f"✅ Deleted {delete_count} files from {folder_prefix}")
        
        if error_count > 0:
            logger.warning(f"⚠️ {error_count} files had errors (non-critical)")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to delete project folder {project_id}: {e}")
        return False


async def get_project_folder_stats(project_id: str) -> dict:
    """
    Get statistics about project folder (file count, total size).
    
    **Arguments:**
    - project_id: Project UUID (as string)
    
    **Returns:**
    - dict: {
        "file_count": 123,
        "total_size_mb": 45.6,
        "exists": True,
        "subfolders": {
          "draft": {"count": 50, "size_mb": 30},
          "final": {"count": 3, "size_mb": 15.6}
        },
        "files": [...]  # First 10 files
      }
    """
    try:
        if not settings.s3_bucket_name:
            return {"error": "S3 not configured"}
        
        s3 = get_s3_client()
        folder_prefix = f"projects/{project_id}/"
        
        # List all objects
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=settings.s3_bucket_name,
            Prefix=folder_prefix
        )
        
        files = []
        for page in pages:
            if 'Contents' in page:
                files.extend(page['Contents'])
        
        if not files:
            return {
                "file_count": 0,
                "total_size_mb": 0,
                "exists": False
            }
        
        file_count = len(files)
        total_size = sum(f['Size'] for f in files)
        
        # Calculate subfolder stats
        draft_files = [f for f in files if '/draft/' in f['Key']]
        final_files = [f for f in files if '/final/' in f['Key']]
        
        subfolders = {
            "draft": {
                "count": len(draft_files),
                "size_mb": round(sum(f['Size'] for f in draft_files) / (1024*1024), 2)
            },
            "final": {
                "count": len(final_files),
                "size_mb": round(sum(f['Size'] for f in final_files) / (1024*1024), 2)
            }
        }
        
        return {
            "file_count": file_count,
            "total_size_mb": round(total_size / (1024*1024), 2),
            "exists": True,
            "subfolders": subfolders,
            "files": [
                {"key": f['Key'], "size_mb": round(f['Size']/(1024*1024), 2)}
                for f in sorted(files, key=lambda x: x['Key'])[:10]
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get folder stats: {e}")
        return {"error": str(e)}

