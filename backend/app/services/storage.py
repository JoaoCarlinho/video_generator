"""S3 storage service for file uploads."""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.config import settings
import logging
from typing import Optional
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageService:
    """Service for handling S3 file uploads."""
    
    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = None
        self.bucket_name = settings.s3_bucket_name
        
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region,
                    config=Config(signature_version='s3v4')
                )
                logger.info(f"✅ S3 client initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize S3 client: {e}")
                self.s3_client = None
        else:
            logger.warning("⚠️ AWS credentials not configured, S3 uploads disabled")
    
    def generate_presigned_upload_url(
        self,
        folder: str,
        filename: str,
        content_type: str,
        user_id: str,
        expires_in: int = 3600
    ) -> Optional[dict]:
        """
        Generate a presigned URL for uploading a file to S3.
        
        Args:
            folder: Folder path in S3 (e.g., 'assets/logos', 'assets/products')
            filename: Original filename
            content_type: MIME type of the file
            user_id: User ID for organizing files
            expires_in: URL expiration time in seconds (default 1 hour)
        
        Returns:
            Dict with upload_url and file_url, or None if failed
        """
        if not self.s3_client or not self.bucket_name:
            logger.warning("⚠️ S3 not configured, cannot generate presigned URL")
            return None
        
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            unique_filename = f"{uuid.uuid4().hex}_{timestamp}"
            if file_extension:
                unique_filename += f".{file_extension}"
            
            # Construct S3 key
            s3_key = f"{folder}/{user_id}/{unique_filename}"
            
            # Generate presigned URL for PUT operation
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ContentType': content_type,
                },
                ExpiresIn=expires_in,
                HttpMethod='PUT'
            )
            
            # Construct public URL (if bucket is configured for public access)
            file_url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
            
            logger.info(f"✅ Generated presigned URL for: {s3_key}")
            
            return {
                'upload_url': presigned_url,
                'file_url': file_url,
                's3_key': s3_key
            }
            
        except ClientError as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            s3_key: S3 key of the file to delete
        
        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client or not self.bucket_name:
            logger.warning("⚠️ S3 not configured, cannot delete file")
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"✅ Deleted file: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Failed to delete file {s3_key}: {e}")
            return False
    
    def check_file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            s3_key: S3 key of the file to check

        Returns:
            True if file exists, False otherwise
        """
        if not self.s3_client or not self.bucket_name:
            return False

        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False

    async def upload_file(
        self,
        file_content: bytes,
        folder: str,
        filename: str,
        content_type: str,
        user_id: str
    ) -> Optional[str]:
        """
        Upload a file directly to S3.

        Args:
            file_content: File content as bytes
            folder: Folder path in S3 (e.g., 'products', 'brands')
            filename: Original filename
            content_type: MIME type of the file
            user_id: User ID for organizing files

        Returns:
            S3 URL of the uploaded file, or None if failed
        """
        if not self.s3_client or not self.bucket_name:
            logger.warning("⚠️ S3 not configured, cannot upload file")
            return None

        try:
            # Generate unique filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            unique_filename = f"{uuid.uuid4().hex}_{timestamp}"
            if file_extension:
                unique_filename += f".{file_extension}"

            # Construct S3 key
            s3_key = f"{folder}/{user_id}/{unique_filename}"

            # Upload file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )

            # Construct public URL
            file_url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"

            logger.info(f"✅ Uploaded file to S3: {s3_key}")

            return file_url

        except ClientError as e:
            logger.error(f"❌ Failed to upload file: {e}")
            return None


# Global storage service instance
storage_service = StorageService()

