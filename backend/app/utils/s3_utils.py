"""
S3 utilities for file uploads and management.
Handles brand assets, perfume images, and campaign video uploads.

Phase 2: Updated for B2B SaaS hierarchy (brands → perfumes → campaigns)
"""

import logging
import boto3
from typing import Optional, Union
import os
from uuid import uuid4
from urllib.parse import urlencode

from app.config import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    """
    Get S3 client configured with AWS credentials.

    Uses explicit credentials from environment if available,
    otherwise falls back to AWS default credential chain
    (IAM role, instance profile, etc.)

    **Returns:**
    - boto3.client: Configured S3 client

    **Note:**
    - In Lambda/EC2: Uses IAM role credentials automatically
    - In local dev: Uses explicit AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
    """
    # If explicit credentials are provided, use them
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        logger.debug("🔑 Using explicit AWS credentials from environment")
        return boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
    else:
        # Use default credential chain (IAM role, instance profile, etc.)
        logger.debug("🔑 Using AWS default credential chain (IAM role)")
        return boto3.client("s3", region_name=settings.aws_region)


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
            ContentType=get_content_type(file_ext)
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
        ".gif": "image/gif",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".mp3": "audio/mpeg"
    }
    return mime_types.get(file_ext, "application/octet-stream")


def _format_s3_tags(tags: dict) -> str:
    """
    Format tags dict into S3 TagSet string format.
    
    **Arguments:**
    - tags: Dictionary of tag key-value pairs
    
    **Returns:**
    - str: URL-encoded tag string for S3 Tagging parameter
    """
    return urlencode(tags)


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


def get_presigned_video_url(s3_key: str, expiration: int = 3600) -> str:
    """
    Generate presigned URL for S3 video file.
    Presigned URLs bypass CORS restrictions and allow temporary access.
    
    **Arguments:**
    - s3_key: S3 object key
    - expiration: URL expiration time in seconds (default: 1 hour)
    
    **Returns:**
    - str: Presigned HTTPS URL that can be accessed from frontend
    
    **Raises:**
    - RuntimeError: If AWS credentials not configured
    """
    try:
        s3 = get_s3_client()
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.s3_bucket_name,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        logger.info(f"✅ Generated presigned URL for {s3_key} (expires in {expiration}s)")
        return presigned_url
    except Exception as e:
        logger.error(f"❌ Failed to generate presigned URL for {s3_key}: {e}")
        # Fallback to public URL if presigned URL generation fails
        logger.warning(f"⚠️ Falling back to public URL for {s3_key}")
        return get_s3_file_url(s3_key)


def parse_s3_url(s3_url: str) -> tuple[str, str]:
    """
    Parse S3 URL to extract bucket name and S3 key.
    
    Supports multiple S3 URL formats:
    - https://bucket.s3.region.amazonaws.com/key
    - https://s3.region.amazonaws.com/bucket/key
    - https://s3.amazonaws.com/bucket/key
    - Presigned URLs: https://bucket.s3.region.amazonaws.com/key?X-Amz-Algorithm=...
    
    **Arguments:**
    - s3_url: S3 URL string (can be presigned URL with query parameters)
    
    **Returns:**
    - tuple: (bucket_name, s3_key)
    
    **Raises:**
    - ValueError: If URL format is not recognized
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(s3_url)
    
    # Format 1: https://bucket.s3.region.amazonaws.com/key
    if '.s3.' in parsed.netloc:
        # Extract bucket from netloc (first part before .s3.)
        bucket_name = parsed.netloc.split('.')[0]
        s3_key = parsed.path.lstrip('/')
        return bucket_name, s3_key
    
    # Format 2: https://s3.region.amazonaws.com/bucket/key
    # Format 3: https://s3.amazonaws.com/bucket/key
    if 's3' in parsed.netloc:
        path_parts = parsed.path.lstrip('/').split('/', 1)
        if len(path_parts) >= 2:
            bucket_name = path_parts[0]
            s3_key = path_parts[1]
            return bucket_name, s3_key
    
    raise ValueError(f"Unrecognized S3 URL format: {s3_url}")


def download_from_s3(s3_url: str, output_path: str) -> None:
    """
    Download file from S3 URL to local path.
    
    **Arguments:**
    - s3_url: S3 URL of the file
    - output_path: Local file path to save the file
    
    **Raises:**
    - RuntimeError: If download fails
    """
    try:
        bucket_name, s3_key = parse_s3_url(s3_url)
        
        s3 = get_s3_client()
        s3.download_file(
            Bucket=bucket_name,
            Key=s3_key,
            Filename=output_path
        )
        
        logger.info(f"✅ Downloaded from S3: {s3_key} → {output_path}")
        
    except Exception as e:
        logger.error(f"❌ Failed to download from S3 {s3_url}: {e}")
        raise RuntimeError(f"Failed to download from S3: {str(e)}")


# ============================================================================
# PHASE 2: B2B SaaS S3 Hierarchy Functions
# New hierarchy: brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/
# ============================================================================

def get_brand_s3_path(brand_id: str) -> str:
    """
    Get S3 path prefix for brand folder.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    
    **Returns:**
    - str: S3 path prefix (e.g., "brands/{brand_id}/")
    """
    return f"brands/{brand_id}/"


def get_perfume_s3_path(brand_id: str, perfume_id: str) -> str:
    """
    Get S3 path prefix for perfume folder.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    - perfume_id: Product UUID (as string)
    
    **Returns:**
    - str: S3 path prefix (e.g., "brands/{brand_id}/perfumes/{perfume_id}/")
    """
    return f"brands/{brand_id}/perfumes/{perfume_id}/"


def get_campaign_s3_path(brand_id: str, perfume_id: str, campaign_id: str) -> str:
    """
    Get S3 path prefix for campaign folder.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    - perfume_id: Product UUID (as string)
    - campaign_id: Campaign UUID (as string)
    
    **Returns:**
    - str: S3 path prefix (e.g., "brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/")
    """
    return f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"


async def upload_brand_logo(
    brand_id: str,
    file_content: bytes,
    filename: str
) -> dict:
    """
    Upload brand logo to S3.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    - file_content: File bytes to upload
    - filename: Original filename (used to determine extension)
    
    **Returns:**
    - dict: {
        "url": "https://...",
        "s3_key": "brands/{brand_id}/brand_logo.png",
        "size_bytes": 12345,
        "filename": "logo.png"
      }
    
    **Raises:**
    - RuntimeError: If upload fails
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")
        
        bucket_name = settings.s3_bucket_name
        logger.info(f"📦 Using S3 bucket: {bucket_name}")
        
        # Determine file extension and normalize to PNG
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".webp"]:
            file_ext = ".png"
        
        s3_key = f"brands/{brand_id}/brand_logo{file_ext}"
        logger.info(f"📤 Uploading to S3: s3://{bucket_name}/{s3_key} ({len(file_content)} bytes)")
        
        # Prepare S3 tags
        tags = {
            "type": "brand_asset",
            "brand_id": brand_id,
            "lifecycle": "permanent"
        }
        
        # Upload to S3
        s3 = get_s3_client()
        try:
            response = s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=get_content_type(file_ext),
                Tagging=_format_s3_tags(tags)
            )
            logger.info(f"✅ S3 upload response: {response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'unknown')}")
        except Exception as upload_error:
            logger.error(f"❌ S3 put_object failed: {upload_error}", exc_info=True)
            raise
        
        s3_url = get_s3_file_url(s3_key)
        
        logger.info(f"✅ Uploaded brand logo to s3://{bucket_name}/{s3_key}")
        logger.info(f"✅ Public URL: {s3_url}")
        
        return {
            "url": s3_url,
            "s3_key": s3_key,
            "bucket": bucket_name,
            "size_bytes": len(file_content),
            "filename": f"brand_logo{file_ext}"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to upload brand logo: {e}", exc_info=True)
        raise RuntimeError(f"Failed to upload brand logo: {str(e)}")


async def upload_brand_guidelines(
    brand_id: str,
    file_content: bytes,
    filename: str
) -> dict:
    """
    Upload brand guidelines document to S3.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    - file_content: File bytes to upload
    - filename: Original filename (used to determine extension)
    
    **Returns:**
    - dict: {
        "url": "https://...",
        "s3_key": "brands/{brand_id}/brand_guidelines.pdf",
        "size_bytes": 12345,
        "filename": "guidelines.pdf"
      }
    
    **Raises:**
    - RuntimeError: If upload fails
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")
        
        bucket_name = settings.s3_bucket_name
        logger.info(f"📦 Using S3 bucket: {bucket_name}")
        
        # Determine file extension and normalize to PDF
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in [".pdf", ".docx"]:
            file_ext = ".pdf"
        
        s3_key = f"brands/{brand_id}/brand_guidelines{file_ext}"
        logger.info(f"📤 Uploading to S3: s3://{bucket_name}/{s3_key} ({len(file_content)} bytes)")
        
        # Prepare S3 tags
        tags = {
            "type": "brand_asset",
            "brand_id": brand_id,
            "lifecycle": "permanent"
        }
        
        # Upload to S3
        s3 = get_s3_client()
        try:
            response = s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=get_content_type(file_ext),
                Tagging=_format_s3_tags(tags)
            )
            logger.info(f"✅ S3 upload response: {response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'unknown')}")
        except Exception as upload_error:
            logger.error(f"❌ S3 put_object failed: {upload_error}", exc_info=True)
            raise
        
        s3_url = get_s3_file_url(s3_key)
        
        logger.info(f"✅ Uploaded brand guidelines to s3://{bucket_name}/{s3_key}")
        logger.info(f"✅ Public URL: {s3_url}")
        
        return {
            "url": s3_url,
            "s3_key": s3_key,
            "bucket": bucket_name,
            "size_bytes": len(file_content),
            "filename": f"brand_guidelines{file_ext}"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to upload brand guidelines: {e}", exc_info=True)
        raise RuntimeError(f"Failed to upload brand guidelines: {str(e)}")


async def upload_perfume_image(
    brand_id: str,
    perfume_id: str,
    angle: str,
    file_content: bytes,
    filename: str
) -> dict:
    """
    Upload perfume product image to S3.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    - perfume_id: Product UUID (as string)
    - angle: Image angle ("front", "back", "top", "left", "right")
    - file_content: File bytes to upload
    - filename: Original filename (used to determine extension)
    
    **Returns:**
    - dict: {
        "url": "https://...",
        "s3_key": "brands/{brand_id}/perfumes/{perfume_id}/{angle}.png",
        "size_bytes": 12345,
        "filename": "front.png"
      }
    
    **Raises:**
    - RuntimeError: If upload fails
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")
        
        # Validate angle
        valid_angles = ["front", "back", "top", "left", "right"]
        if angle not in valid_angles:
            raise ValueError(f"Invalid angle. Must be one of: {valid_angles}")
        
        # Determine file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".webp"]:
            file_ext = ".png"
        
        s3_key = f"brands/{brand_id}/perfumes/{perfume_id}/{angle}{file_ext}"
        
        # Prepare S3 tags
        tags = {
            "type": "perfume_image",
            "brand_id": brand_id,
            "perfume_id": perfume_id,
            "angle": angle,
            "lifecycle": "permanent"
        }
        
        # Upload to S3
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=get_content_type(file_ext),
            Tagging=_format_s3_tags(tags)
        )
        
        s3_url = get_s3_file_url(s3_key)
        
        logger.info(f"✅ Uploaded perfume image ({angle}): {s3_key}")
        
        return {
            "url": s3_url,
            "s3_key": s3_key,
            "size_bytes": len(file_content),
            "filename": f"{angle}{file_ext}"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to upload perfume image: {e}")
        raise RuntimeError(f"Failed to upload perfume image: {str(e)}")


async def upload_draft_video(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int,
    scene_index: int,
    file_path: str
) -> dict:
    """
    Upload draft scene video to S3.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    - perfume_id: Product UUID (as string)
    - campaign_id: Campaign UUID (as string)
    - variation_index: Variation index (0, 1, or 2)
    - scene_index: Scene index (1-4)
    - file_path: Local file path to upload
    
    **Returns:**
    - dict: {
        "url": "https://...",
        "s3_key": "brands/.../variation_0/draft/scene_1_bg.mp4",
        "size_bytes": 12345,
        "filename": "scene_1_bg.mp4"
      }
    
    **Raises:**
    - RuntimeError: If upload fails
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")
        
        # Validate variation_index
        if variation_index not in [0, 1, 2]:
            raise ValueError("variation_index must be 0, 1, or 2")
        
        # Validate scene_index
        if scene_index < 1 or scene_index > 4:
            raise ValueError("scene_index must be between 1 and 4")
        
        s3_key = f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/variation_{variation_index}/draft/scene_{scene_index}_bg.mp4"
        
        # Prepare S3 tags
        tags = {
            "type": "campaign_video",
            "subtype": "draft",
            "brand_id": brand_id,
            "perfume_id": perfume_id,
            "campaign_id": campaign_id,
            "variation_index": str(variation_index),
            "lifecycle": "30days"
        }
        
        # Read file and upload to S3
        s3 = get_s3_client()
        with open(file_path, 'rb') as f:
            file_content = f.read()
            s3.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType="video/mp4",
                Tagging=_format_s3_tags(tags)
            )
        
        s3_url = get_s3_file_url(s3_key)
        
        logger.info(f"✅ Uploaded draft video: {s3_key}")
        
        return {
            "url": s3_url,
            "s3_key": s3_key,
            "size_bytes": len(file_content),
            "filename": f"scene_{scene_index}_bg.mp4"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to upload draft video: {e}")
        raise RuntimeError(f"Failed to upload draft video: {str(e)}")


async def upload_draft_music(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int,
    file_path: str
) -> dict:
    """
    Upload draft background music to S3.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    - perfume_id: Product UUID (as string)
    - campaign_id: Campaign UUID (as string)
    - variation_index: Variation index (0, 1, or 2)
    - file_path: Local file path to upload
    
    **Returns:**
    - dict: {
        "url": "https://...",
        "s3_key": "brands/.../variation_0/draft/music.mp3",
        "size_bytes": 12345,
        "filename": "music.mp3"
      }
    
    **Raises:**
    - RuntimeError: If upload fails
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")
        
        # Validate variation_index
        if variation_index not in [0, 1, 2]:
            raise ValueError("variation_index must be 0, 1, or 2")
        
        s3_key = f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/variation_{variation_index}/draft/music.mp3"
        
        # Prepare S3 tags
        tags = {
            "type": "campaign_video",
            "subtype": "draft",
            "brand_id": brand_id,
            "perfume_id": perfume_id,
            "campaign_id": campaign_id,
            "variation_index": str(variation_index),
            "lifecycle": "30days"
        }
        
        # Read file and upload to S3
        s3 = get_s3_client()
        with open(file_path, 'rb') as f:
            file_content = f.read()
            s3.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType="audio/mpeg",
                Tagging=_format_s3_tags(tags)
            )
        
        s3_url = get_s3_file_url(s3_key)
        
        logger.info(f"✅ Uploaded draft music: {s3_key}")
        
        return {
            "url": s3_url,
            "s3_key": s3_key,
            "size_bytes": len(file_content),
            "filename": "music.mp3"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to upload draft music: {e}")
        raise RuntimeError(f"Failed to upload draft music: {str(e)}")


async def upload_final_video(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int,
    file_path: str
) -> dict:
    """
    Upload final rendered video to S3.
    
    **Arguments:**
    - brand_id: Brand UUID (as string)
    - perfume_id: Product UUID (as string)
    - campaign_id: Campaign UUID (as string)
    - variation_index: Variation index (0, 1, or 2)
    - file_path: Local file path to upload
    
    **Returns:**
    - dict: {
        "url": "https://...",
        "s3_key": "brands/.../variation_0/final/final_video.mp4",
        "size_bytes": 12345,
        "filename": "final_video.mp4"
      }
    
    **Raises:**
    - RuntimeError: If upload fails
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")
        
        # Validate variation_index
        if variation_index not in [0, 1, 2]:
            raise ValueError("variation_index must be 0, 1, or 2")
        
        s3_key = f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/variation_{variation_index}/final/final_video.mp4"
        
        # Prepare S3 tags
        tags = {
            "type": "campaign_video",
            "subtype": "final",
            "brand_id": brand_id,
            "perfume_id": perfume_id,
            "campaign_id": campaign_id,
            "variation_index": str(variation_index),
            "lifecycle": "90days"
        }
        
        # Read file and upload to S3
        s3 = get_s3_client()
        with open(file_path, 'rb') as f:
            file_content = f.read()
            s3.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType="video/mp4",
                Tagging=_format_s3_tags(tags)
            )
        
        # Generate presigned URL for frontend access (bypasses CORS)
        # Presigned URLs are valid for 7 days (604800 seconds)
        presigned_url = get_presigned_video_url(s3_key, expiration=604800)
        
        logger.info(f"✅ Uploaded final video: {s3_key}")
        
        return {
            "url": presigned_url,  # Use presigned URL instead of public URL
            "s3_key": s3_key,
            "size_bytes": len(file_content),
            "filename": "final_video.mp4"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to upload final video: {e}")
        raise RuntimeError(f"Failed to upload final video: {str(e)}")


# ============================================================================
# DEPRECATED: Old project-based functions (kept for backward compatibility)
# These will be removed in Phase 5 when pipeline is updated
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
            ContentType=get_content_type(os.path.splitext(filename)[1])
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


def upload_video_to_s3(
    local_video_path: str,
    project_id: str,
    aspect_ratio: str
) -> dict:
    """
    Upload a generated video file to S3 preview folder.

    Uploads video to: s3://bucket/projects/{project_id}/preview/video_{aspect_ratio}.mp4

    **Arguments:**
    - local_video_path: Local filesystem path to video file
    - project_id: Project UUID (as string)
    - aspect_ratio: Aspect ratio (e.g., "16:9", "9:16", "1:1")

    **Returns:**
    - dict: {
        "url": "https://...",
        "s3_key": "projects/.../preview/video_16-9.mp4",
        "size_bytes": 12345,
        "aspect_ratio": "16:9"
      }

    **Raises:**
    - RuntimeError: If upload fails
    - FileNotFoundError: If local video file doesn't exist
    """
    try:
        if not settings.s3_bucket_name:
            raise RuntimeError("S3_BUCKET_NAME not configured in .env")

        # Check if file exists
        if not os.path.exists(local_video_path):
            raise FileNotFoundError(f"Video file not found: {local_video_path}")

        # Read video file
        with open(local_video_path, 'rb') as f:
            file_content = f.read()

        # Generate S3 key (replace : with - for aspect ratio)
        aspect_safe = aspect_ratio.replace(':', '-')
        filename = f"video_{aspect_safe}.mp4"
        s3_key = f"projects/{project_id}/preview/{filename}"

        # Upload to S3
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType='video/mp4'
        )

        # Generate URL
        s3_url = get_s3_file_url(s3_key)

        logger.info(f"✅ Uploaded video to S3: {s3_key} ({len(file_content) / (1024*1024):.1f} MB)")

        return {
            "url": s3_url,
            "s3_key": s3_key,
            "size_bytes": len(file_content),
            "aspect_ratio": aspect_ratio
        }

    except Exception as e:
        logger.error(f"❌ Failed to upload video to S3: {e}")
        raise RuntimeError(f"Video upload failed: {str(e)}")


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


# ============================================================================
# Phase 3: Scene Editing S3 Helper Functions
# ============================================================================

def get_scene_s3_url(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int,
    scene_index: int  # 0-based
) -> str:
    """
    Construct S3 URL for a scene video.
    
    **Arguments:**
    - brand_id: Brand UUID string
    - perfume_id: Product UUID string
    - campaign_id: Campaign UUID string
    - variation_index: Variation index (0, 1, 2)
    - scene_index: Scene index (0-based)
    
    **Returns:**
    - Full S3 URL string
    """
    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME not configured in .env")
    
    s3_key = (
        f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"
        f"variation_{variation_index}/draft/scene_{scene_index+1}_bg.mp4"
    )
    
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"


def get_final_video_s3_url(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int
) -> str:
    """
    Construct S3 URL for final video.
    
    **Arguments:**
    - brand_id: Brand UUID string
    - perfume_id: Product UUID string
    - campaign_id: Campaign UUID string
    - variation_index: Variation index (0, 1, 2)
    
    **Returns:**
    - Full S3 URL string
    """
    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME not configured in .env")
    
    s3_key = (
        f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"
        f"variation_{variation_index}/final/final_video.mp4"
    )
    
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"


def get_audio_s3_url(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int
) -> str:
    """
    Construct S3 URL for audio/music file.
    
    **Arguments:**
    - brand_id: Brand UUID string
    - perfume_id: Product UUID string
    - campaign_id: Campaign UUID string
    - variation_index: Variation index (0, 1, 2)
    
    **Returns:**
    - Full S3 URL string
    """
    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME not configured in .env")
    
    s3_key = (
        f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"
        f"variation_{variation_index}/draft/music.mp3"
    )
    
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"


