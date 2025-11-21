"""SQLAlchemy ORM models for the database."""

from sqlalchemy import Column, String, Integer, DateTime, Numeric, Text, Boolean, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


class Brand(Base):
    """Brand model for storing brand identity information."""

    __tablename__ = "brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    brand_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    guidelines = Column(Text, nullable=True)
    logo_urls = Column(JSONB, nullable=True)  # Array of S3 logo URLs

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    products = relationship("Product", back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Brand {self.id} - {self.company_name}>"


class Product(Base):
    """Product model for storing product catalog information."""

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey('brands.id', ondelete='CASCADE'), nullable=False, index=True)
    product_type = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    icp_segment = Column(Text, nullable=True)
    image_urls = Column(JSONB, nullable=True)  # Array of S3 product image URLs

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    brand = relationship("Brand", back_populates="products")
    campaigns = relationship("Campaign", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product {self.id} - {self.name}>"


class Campaign(Base):
    """Campaign model for storing marketing campaign configurations."""

    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    seasonal_event = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)  # Duration in seconds: 15, 30, 45, 60
    scene_configs = Column(JSONB, nullable=False)  # Array of scene configuration objects
    status = Column(String(50), default="draft", index=True)  # draft, generating, completed, failed

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="campaigns")

    def __repr__(self):
        return f"<Campaign {self.id} - {self.name}>"

    @property
    def display_name(self):
        """Auto-generate display name from name, event, and year."""
        return f"{self.name}-{self.seasonal_event}-{self.year}"


# ============================================================================
# Auth Users Model (for foreign key reference)
# This is a minimal model to satisfy SQLAlchemy foreign key constraints
# The actual auth.users table is managed by Supabase Auth
# ============================================================================
class AuthUser(Base):
    """Minimal model for auth.users table (managed by Supabase).
    
    This model exists only to satisfy SQLAlchemy foreign key constraints.
    We don't create/modify this table - it's managed by Supabase Auth.
    """
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    
    def __repr__(self):
        return f"<AuthUser {self.id}>"


# ============================================================================
# DEPRECATED: Project model (will be removed in Phase 3-4)
# Kept temporarily for backward compatibility with existing API endpoints
# ============================================================================
class Project(Base):
    """DEPRECATED: Project model - replaced by Campaign in Phase 2.
    
    This model is kept temporarily for backward compatibility.
    Will be removed when API endpoints are updated in Phase 3-4.
    """
    
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

    # WAN 2.5: Video Provider Tracking
    video_provider = Column(String(20), nullable=False, default='replicate', server_default='replicate')  # 'replicate' or 'ecs'
    video_provider_metadata = Column(JSONB, nullable=True)   # Provider-specific metadata (endpoint version, failover events)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @validates('video_provider')
    def validate_video_provider(self, key, value):
        """Validate that video_provider is either 'replicate' or 'ecs'."""
        valid_providers = ['replicate', 'ecs']
        if value not in valid_providers:
            raise ValueError(
                f"Invalid video provider: '{value}'. "
                f"Must be one of: {', '.join(valid_providers)}"
            )
        return value
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Project {self.id} - {self.title} (provider: {self.video_provider})>"


# ============================================================================
# Phase 2 B2B SaaS Models
# ============================================================================

class Brand(Base):
    """Brand model - one brand per user (B2B SaaS)."""
    
    __tablename__ = "brands"
    
    brand_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Foreign key to auth.users - AuthUser model defined above allows SQLAlchemy to resolve this
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, unique=True)
    brand_name = Column(String(100), nullable=False, unique=True)
    brand_logo_url = Column(String(500), nullable=False)
    brand_guidelines_url = Column(String(500), nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    perfumes = relationship("Perfume", back_populates="brand", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="brand", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Brand {self.brand_id} - {self.brand_name}>"


class Perfume(Base):
    """Perfume model - many perfumes per brand."""
    
    __tablename__ = "perfumes"
    
    perfume_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.brand_id", ondelete="CASCADE"), nullable=False)
    perfume_name = Column(String(200), nullable=False)
    perfume_gender = Column(String(20), nullable=False)  # 'masculine', 'feminine', 'unisex'
    front_image_url = Column(String(500), nullable=False)
    back_image_url = Column(String(500), nullable=True)
    top_image_url = Column(String(500), nullable=True)
    left_image_url = Column(String(500), nullable=True)
    right_image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    brand = relationship("Brand", back_populates="perfumes")
    campaigns = relationship("Campaign", back_populates="perfume", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("perfume_gender IN ('masculine', 'feminine', 'unisex')", name='ck_perfumes_gender'),
        UniqueConstraint('brand_id', 'perfume_name', name='uq_perfumes_brand_perfume'),
    )
    
    def __repr__(self):
        return f"<Perfume {self.perfume_id} - {self.perfume_name}>"


class Campaign(Base):
    """Campaign model - replaces Project, many campaigns per perfume."""
    
    __tablename__ = "campaigns"
    
    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perfume_id = Column(UUID(as_uuid=True), ForeignKey("perfumes.perfume_id", ondelete="CASCADE"), nullable=False)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.brand_id", ondelete="CASCADE"), nullable=False)
    campaign_name = Column(String(200), nullable=False)
    creative_prompt = Column(Text, nullable=False)
    selected_style = Column(String(50), nullable=False)  # 'gold_luxe', 'dark_elegance', 'romantic_floral'
    target_duration = Column(Integer, nullable=False)  # 15-60 seconds
    num_variations = Column(Integer, default=1, nullable=False)  # 1-3 variations
    selected_variation_index = Column(Integer, nullable=True)  # 0-2, NULL if not selected
    status = Column(String(50), default='pending', nullable=False)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    cost = Column(Numeric(10, 2), default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    campaign_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    brand = relationship("Brand", back_populates="campaigns")
    perfume = relationship("Perfume", back_populates="campaigns")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("selected_style IN ('gold_luxe', 'dark_elegance', 'romantic_floral')", name='ck_campaigns_style'),
        CheckConstraint('target_duration BETWEEN 15 AND 60', name='ck_campaigns_duration'),
        CheckConstraint('num_variations BETWEEN 1 AND 3', name='ck_campaigns_variations'),
        CheckConstraint('selected_variation_index IS NULL OR selected_variation_index BETWEEN 0 AND 2', name='ck_campaigns_selected_variation'),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='ck_campaigns_status'),
        CheckConstraint('progress BETWEEN 0 AND 100', name='ck_campaigns_progress'),
        UniqueConstraint('perfume_id', 'campaign_name', name='uq_campaigns_perfume_campaign'),
    )
    
    def __repr__(self):
        return f"<Campaign {self.campaign_id} - {self.campaign_name}>"

