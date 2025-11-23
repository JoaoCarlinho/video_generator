"""Local filesystem storage utilities for local-first generation.

Handles creation, management, and cleanup of local campaign directories.
All intermediate and final videos stored locally until user finalizes.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Base directory for local storage
LOCAL_STORAGE_ROOT = os.getenv('LOCAL_STORAGE_PATH', '/tmp/genads')


class LocalStorageManager:
    """Manage local campaign storage directories and files."""
    
    @staticmethod
    def get_campaign_root(campaign_id: UUID) -> Path:
        """Get root directory for a campaign.
        
        Structure:
        /tmp/genads/{campaign_id}/
        ├── input/          # User uploaded files
        ├── drafts/         # Intermediate/draft videos
        └── final/          # Final videos (ready for S3)
        """
        return Path(LOCAL_STORAGE_ROOT) / str(campaign_id)
    
    @staticmethod
    def get_input_dir(campaign_id: UUID) -> Path:
        """Get input files directory (user uploads)."""
        return LocalStorageManager.get_campaign_root(campaign_id) / 'input'
    
    @staticmethod
    def get_drafts_dir(campaign_id: UUID) -> Path:
        """Get drafts directory (intermediate videos)."""
        return LocalStorageManager.get_campaign_root(campaign_id) / 'drafts'
    
    @staticmethod
    def get_final_dir(campaign_id: UUID) -> Path:
        """Get final videos directory."""
        return LocalStorageManager.get_campaign_root(campaign_id) / 'final'
    
    @staticmethod
    def initialize_campaign_storage(campaign_id: UUID) -> Dict[str, str]:
        """Create directory structure for a campaign.
        
        Returns:
            Dict with paths to subdirectories
        """
        try:
            input_dir = LocalStorageManager.get_input_dir(campaign_id)
            drafts_dir = LocalStorageManager.get_drafts_dir(campaign_id)
            final_dir = LocalStorageManager.get_final_dir(campaign_id)
            
            # Create all directories
            input_dir.mkdir(parents=True, exist_ok=True)
            drafts_dir.mkdir(parents=True, exist_ok=True)
            final_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"✅ Initialized local storage for campaign {campaign_id}")
            logger.info(f"   Input: {input_dir}")
            logger.info(f"   Drafts: {drafts_dir}")
            logger.info(f"   Final: {final_dir}")
            
            return {
                'campaign_root': str(LocalStorageManager.get_campaign_root(campaign_id)),
                'input_dir': str(input_dir),
                'drafts_dir': str(drafts_dir),
                'final_dir': str(final_dir)
            }
        except Exception as e:
            logger.error(f"❌ Failed to initialize local storage for {campaign_id}: {e}")
            raise
    
    @staticmethod
    def save_input_file(campaign_id: UUID, filename: str, file_content: bytes) -> str:
        """Save user-uploaded file to input directory.
        
        Args:
            campaign_id: Campaign UUID
            filename: Original filename
            file_content: File bytes
            
        Returns:
            Local file path
        """
        try:
            input_dir = LocalStorageManager.get_input_dir(campaign_id)
            file_path = input_dir / filename
            
            file_path.write_bytes(file_content)
            logger.info(f"✅ Saved input file: {file_path}")
            
            return str(file_path)
        except Exception as e:
            logger.error(f"❌ Failed to save input file: {e}")
            raise
    
    @staticmethod
    def save_draft_file(campaign_id: UUID, filename: str, file_path_or_bytes) -> str:
        """Save intermediate/draft file.
        
        Args:
            campaign_id: Campaign UUID
            filename: Filename in drafts folder
            file_path_or_bytes: Either a Path to copy from, or bytes to write
            
        Returns:
            Local file path
        """
        try:
            drafts_dir = LocalStorageManager.get_drafts_dir(campaign_id)
            dest_path = drafts_dir / filename
            
            if isinstance(file_path_or_bytes, (str, Path)):
                # Copy from source path
                shutil.copy2(file_path_or_bytes, dest_path)
            else:
                # Write bytes
                dest_path.write_bytes(file_path_or_bytes)
            
            logger.info(f"✅ Saved draft file: {dest_path}")
            return str(dest_path)
        except Exception as e:
            logger.error(f"❌ Failed to save draft file: {e}")
            raise
    
    @staticmethod
    def save_final_video(campaign_id: UUID, aspect_ratio: str, file_path: str, variation_index: int = None) -> str:
        """Save final video.
        
        Args:
            campaign_id: Campaign UUID
            aspect_ratio: '16:9'
            file_path: Path to video file to save
            variation_index: Optional variation index (0, 1, 2) for multi-variation support
            
        Returns:
            Local file path in final directory
        """
        try:
            final_dir = LocalStorageManager.get_final_dir(campaign_id)
            
            # Save with variation index if provided (for multi-variation support)
            if variation_index is not None:
                filename = f'video_{variation_index}.mp4'
            else:
                filename = 'video.mp4'
            dest_path = final_dir / filename
            
            # Copy video file
            shutil.copy2(file_path, dest_path)
            
            logger.info(f"✅ Saved final video: {dest_path}")
            return str(dest_path)
        except Exception as e:
            logger.error(f"❌ Failed to save final video: {e}")
            raise
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"❌ Failed to get file size for {file_path}: {e}")
            return 0
    
    @staticmethod
    def get_campaign_storage_size(campaign_id: UUID) -> int:
        """Get total size of all files for a campaign.
        
        Returns:
            Total size in bytes
        """
        try:
            campaign_root = LocalStorageManager.get_campaign_root(campaign_id)
            
            if not campaign_root.exists():
                return 0
            
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(campaign_root):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            
            return total_size
        except Exception as e:
            logger.error(f"❌ Failed to calculate storage size: {e}")
            return 0
    
    @staticmethod
    def cleanup_campaign_storage(campaign_id: UUID) -> bool:
        """Delete all local files for a campaign.
        
        Called after finalizing and uploading to S3.
        
        Args:
            campaign_id: Campaign UUID
            
        Returns:
            True if cleanup successful
        """
        try:
            campaign_root = LocalStorageManager.get_campaign_root(campaign_id)
            
            if campaign_root.exists():
                size_before = LocalStorageManager.get_campaign_storage_size(campaign_id)
                shutil.rmtree(campaign_root)
                
                logger.info(f"✅ Cleaned up local storage for campaign {campaign_id}")
                logger.info(f"   Freed {size_before / 1024 / 1024:.1f} MB")
                return True
            else:
                logger.warning(f"⚠️ Campaign storage already deleted: {campaign_root}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to cleanup campaign storage: {e}")
            return False
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """Check if file exists."""
        return os.path.exists(file_path)


def format_storage_size(bytes_size: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"

