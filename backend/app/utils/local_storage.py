"""Local filesystem storage utilities for local-first generation.

Handles creation, management, and cleanup of local project directories.
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
    """Manage local project storage directories and files."""
    
    @staticmethod
    def get_project_root(project_id: UUID) -> Path:
        """Get root directory for a project.
        
        Structure:
        /tmp/genads/{project_id}/
        ├── input/          # User uploaded files
        ├── drafts/         # Intermediate/draft videos
        └── final/          # Final videos (ready for S3)
        """
        return Path(LOCAL_STORAGE_ROOT) / str(project_id)
    
    @staticmethod
    def get_input_dir(project_id: UUID) -> Path:
        """Get input files directory (user uploads)."""
        return LocalStorageManager.get_project_root(project_id) / 'input'
    
    @staticmethod
    def get_drafts_dir(project_id: UUID) -> Path:
        """Get drafts directory (intermediate videos)."""
        return LocalStorageManager.get_project_root(project_id) / 'drafts'
    
    @staticmethod
    def get_final_dir(project_id: UUID) -> Path:
        """Get final videos directory."""
        return LocalStorageManager.get_project_root(project_id) / 'final'
    
    @staticmethod
    def initialize_project_storage(project_id: UUID) -> Dict[str, str]:
        """Create directory structure for a project.
        
        Returns:
            Dict with paths to subdirectories
        """
        try:
            input_dir = LocalStorageManager.get_input_dir(project_id)
            drafts_dir = LocalStorageManager.get_drafts_dir(project_id)
            final_dir = LocalStorageManager.get_final_dir(project_id)
            
            # Create all directories
            input_dir.mkdir(parents=True, exist_ok=True)
            drafts_dir.mkdir(parents=True, exist_ok=True)
            final_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"✅ Initialized local storage for project {project_id}")
            logger.info(f"   Input: {input_dir}")
            logger.info(f"   Drafts: {drafts_dir}")
            logger.info(f"   Final: {final_dir}")
            
            return {
                'project_root': str(LocalStorageManager.get_project_root(project_id)),
                'input_dir': str(input_dir),
                'drafts_dir': str(drafts_dir),
                'final_dir': str(final_dir)
            }
        except Exception as e:
            logger.error(f"❌ Failed to initialize local storage for {project_id}: {e}")
            raise
    
    @staticmethod
    def save_input_file(project_id: UUID, filename: str, file_content: bytes) -> str:
        """Save user-uploaded file to input directory.
        
        Args:
            project_id: Project UUID
            filename: Original filename
            file_content: File bytes
            
        Returns:
            Local file path
        """
        try:
            input_dir = LocalStorageManager.get_input_dir(project_id)
            file_path = input_dir / filename
            
            file_path.write_bytes(file_content)
            logger.info(f"✅ Saved input file: {file_path}")
            
            return str(file_path)
        except Exception as e:
            logger.error(f"❌ Failed to save input file: {e}")
            raise
    
    @staticmethod
    def save_draft_file(project_id: UUID, filename: str, file_path_or_bytes) -> str:
        """Save intermediate/draft file.
        
        Args:
            project_id: Project UUID
            filename: Filename in drafts folder
            file_path_or_bytes: Either a Path to copy from, or bytes to write
            
        Returns:
            Local file path
        """
        try:
            drafts_dir = LocalStorageManager.get_drafts_dir(project_id)
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
    def save_final_video(project_id: UUID, aspect_ratio: str, file_path: str) -> str:
        """Save final video.
        
        Args:
            project_id: Project UUID
            aspect_ratio: '9:16', '1:1', or '16:9'
            file_path: Path to video file to save
            
        Returns:
            Local file path in final directory
        """
        try:
            final_dir = LocalStorageManager.get_final_dir(project_id)
            
            # Map aspect ratio to filename
            aspect_map = {
                '9:16': 'video_9-16.mp4',
                '1:1': 'video_1-1.mp4',
                '16:9': 'video_16-9.mp4'
            }
            
            filename = aspect_map.get(aspect_ratio, f'video_{aspect_ratio}.mp4')
            dest_path = final_dir / filename
            
            # Copy video file
            shutil.copy2(file_path, dest_path)
            
            logger.info(f"✅ Saved final video {aspect_ratio}: {dest_path}")
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
    def get_project_storage_size(project_id: UUID) -> int:
        """Get total size of all files for a project.
        
        Returns:
            Total size in bytes
        """
        try:
            project_root = LocalStorageManager.get_project_root(project_id)
            
            if not project_root.exists():
                return 0
            
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(project_root):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            
            return total_size
        except Exception as e:
            logger.error(f"❌ Failed to calculate storage size: {e}")
            return 0
    
    @staticmethod
    def cleanup_project_storage(project_id: UUID) -> bool:
        """Delete all local files for a project.
        
        Called after finalizing and uploading to S3.
        
        Args:
            project_id: Project UUID
            
        Returns:
            True if cleanup successful
        """
        try:
            project_root = LocalStorageManager.get_project_root(project_id)
            
            if project_root.exists():
                size_before = LocalStorageManager.get_project_storage_size(project_id)
                shutil.rmtree(project_root)
                
                logger.info(f"✅ Cleaned up local storage for project {project_id}")
                logger.info(f"   Freed {size_before / 1024 / 1024:.1f} MB")
                return True
            else:
                logger.warning(f"⚠️ Project storage already deleted: {project_root}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to cleanup project storage: {e}")
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

