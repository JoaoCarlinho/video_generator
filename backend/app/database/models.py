"""SQLAlchemy ORM models for the database."""

from sqlalchemy import Column, String, Integer, DateTime, Numeric, Text, JSON, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Project(Base):
    """Project model for storing ad generation projects."""
    
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    ad_project_json = Column(JSONB, nullable=False)
    status = Column(String, default="pending", index=True)
    progress = Column(Integer, default=0)
    cost = Column(Numeric(10, 2), default=0)
    error_message = Column(Text, nullable=True)
    
    # S3 RESTRUCTURING: Per-project folder organization
    s3_project_folder = Column(String, nullable=True)        # projects/{id}/
    s3_project_folder_url = Column(String, nullable=True)    # https://bucket.s3.../projects/{id}/
    
    # VIDEO GENERATION SETTINGS
    aspect_ratio = Column(String, default='16:9')  # DEPRECATED: Use output_formats instead

    # MULTI-FORMAT OUTPUT (Story 3)
    product_images = Column(ARRAY(Text), nullable=True)      # Array of product image URLs (max 10)
    scene_backgrounds = Column(JSONB, nullable=True)         # JSON array of scene background mappings
    output_formats = Column(ARRAY(Text), nullable=True, default=['16:9'])  # Array of aspect ratios

    # LOCAL STORAGE: Local-first generation paths
    local_project_path = Column(String(500), nullable=True)    # /tmp/genads/{project_id}
    local_video_paths = Column(JSON, nullable=True)          # {"16:9": "/path/to/video.mp4", "9:16": "/path/to/video_9x16.mp4"}
    local_input_files = Column(JSON, nullable=True)          # {"product_image": "/path/to/image.png", ...}
    local_draft_files = Column(JSON, nullable=True)          # {"scene_1_bg": "/path/to/video.mp4", ...}
    
    # PHASE 7: Style Selection
    selected_style = Column(String(50), nullable=True)       # 'cinematic', 'dark_premium', 'minimal_studio', 'lifestyle', '2d_animated', or NULL
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Project {self.id} - {self.title}>"

