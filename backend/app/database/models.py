"""SQLAlchemy ORM models for the database."""

from sqlalchemy import Column, String, Integer, DateTime, Numeric, Text, Boolean, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, JSON
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
    creatives = relationship("Creative", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Campaign {self.id} - {self.name}>"

    @property
    def display_name(self):
        """Auto-generate display name from name, event, and year."""
        return f"{self.name}-{self.seasonal_event}-{self.year}"


class Creative(Base):
    """Creative model for storing individual creative executions within a campaign."""

    __tablename__ = "creatives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    ad_creative_json = Column(JSONB, nullable=False)  # Creative configuration and content
    status = Column(String(50), default="pending", index=True)  # pending, generating, completed, failed
    progress = Column(Integer, default=0)
    cost = Column(Numeric(10, 2), default=0)
    error_message = Column(Text, nullable=True)

    # S3 storage paths
    s3_campaign_folder = Column(String, nullable=True)
    s3_campaign_folder_url = Column(String, nullable=True)

    # Video settings
    aspect_ratio = Column(String, default='16:9')
    product_images = Column(ARRAY(Text), nullable=True)
    scene_backgrounds = Column(JSONB, nullable=True)
    output_formats = Column(ARRAY(Text), nullable=True, default=['16:9'])

    # Local storage paths
    local_campaign_path = Column(String(500), nullable=True)
    local_video_paths = Column(JSON, nullable=True)
    local_input_files = Column(JSON, nullable=True)
    local_draft_files = Column(JSON, nullable=True)

    # Style and provider settings
    selected_style = Column(String(50), nullable=True)
    video_provider = Column(String(20), nullable=False, default='replicate', server_default='replicate')
    video_provider_metadata = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="creatives")

    def __repr__(self):
        return f"<Creative {self.id} - {self.title}>"

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
