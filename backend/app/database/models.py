"""SQLAlchemy ORM models for the database."""

from sqlalchemy import Column, String, Integer, DateTime, Numeric, Text
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
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Project {self.id} - {self.title}>"

