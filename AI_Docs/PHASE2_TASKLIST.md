# B2B SaaS Overhaul - Implementation Task List

**Version:** 1.0  
**Created:** November 18, 2025  
**Estimated Duration:** 120-160 hours (3-4 weeks)  
**Complexity:** HIGH

---

## Overview

This task list breaks down the B2B SaaS transformation into **8 phases** with **87 specific tasks**. Each phase has clear deliverables, testing requirements, and GO/NO-GO checkpoints.

### Phase Summary

| Phase | Focus | Duration | Tasks | Status |
|-------|-------|----------|-------|--------|
| Phase 1 | Database & Models | 16-24h | 12 | ⏳ Not Started |
| Phase 2 | S3 Storage Refactor | 16h | 10 | ⏳ Not Started |
| Phase 3 | Backend API - Brands & Perfumes | 24-32h | 15 | ⏳ Not Started |
| Phase 4 | Backend API - Campaigns | 16-24h | 12 | ⏳ Not Started |
| Phase 5 | Generation Pipeline Updates | 16-20h | 10 | ⏳ Not Started |
| Phase 6 | Frontend - Pages | 32-40h | 18 | ⏳ Not Started |
| Phase 7 | Frontend - Components & Routing | 16-24h | 12 | ⏳ Not Started |
| Phase 8 | Integration & Testing | 24-32h | 8 | ⏳ Not Started |

**Total:** 160-216 hours (estimated)

---

## Phase 1: Database & Models (2-3 days, 16-24 hours)

**Goal:** Create new database schema with 3-tier hierarchy

### Tasks

#### 1.1 Create Alembic Migration for New Tables ✅

**File:** `backend/alembic/versions/008_create_b2b_schema.py`

**Actions:**
- [ ] Drop old `projects` table (confirmed: no data migration needed)
- [ ] Create `brands` table with all fields
- [ ] Create `perfumes` table with all fields
- [ ] Create `campaigns` table (replaces `projects`)
- [ ] Create all indexes (user_id, brand_id, perfume_id, status, created_at)
- [ ] Create foreign key constraints
- [ ] Add CHECK constraints (gender, style, duration, variations)
- [ ] Add UNIQUE constraints (user_id, brand_name, perfume_name, campaign_name)

**SQL Example:**
```sql
-- Drop old table
DROP TABLE IF EXISTS projects CASCADE;

-- Create brands table
CREATE TABLE brands (
  brand_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_name VARCHAR(100) NOT NULL UNIQUE,
  brand_logo_url VARCHAR(500) NOT NULL,
  brand_guidelines_url VARCHAR(500) NOT NULL,
  onboarding_completed BOOLEAN DEFAULT false NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_brands_user_id ON brands(user_id);
CREATE INDEX idx_brands_onboarding ON brands(onboarding_completed);
CREATE UNIQUE INDEX idx_brands_name ON brands(LOWER(brand_name));

-- Create perfumes table
CREATE TABLE perfumes (
  perfume_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  brand_id UUID NOT NULL REFERENCES brands(brand_id) ON DELETE CASCADE,
  perfume_name VARCHAR(200) NOT NULL,
  perfume_gender VARCHAR(20) NOT NULL CHECK (perfume_gender IN ('masculine', 'feminine', 'unisex')),
  front_image_url VARCHAR(500) NOT NULL,
  back_image_url VARCHAR(500),
  top_image_url VARCHAR(500),
  left_image_url VARCHAR(500),
  right_image_url VARCHAR(500),
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT unique_perfume_per_brand UNIQUE(brand_id, perfume_name)
);

CREATE INDEX idx_perfumes_brand_id ON perfumes(brand_id);
CREATE INDEX idx_perfumes_gender ON perfumes(perfume_gender);

-- Create campaigns table
CREATE TABLE campaigns (
  campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  perfume_id UUID NOT NULL REFERENCES perfumes(perfume_id) ON DELETE CASCADE,
  brand_id UUID NOT NULL REFERENCES brands(brand_id) ON DELETE CASCADE,
  campaign_name VARCHAR(200) NOT NULL,
  creative_prompt TEXT NOT NULL,
  selected_style VARCHAR(50) NOT NULL CHECK (selected_style IN ('gold_luxe', 'dark_elegance', 'romantic_floral')),
  target_duration INTEGER NOT NULL CHECK (target_duration BETWEEN 15 AND 60),
  num_variations INTEGER DEFAULT 1 NOT NULL CHECK (num_variations BETWEEN 1 AND 3),
  selected_variation_index INTEGER CHECK (selected_variation_index BETWEEN 0 AND 2),
  status VARCHAR(50) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  progress INTEGER DEFAULT 0 NOT NULL CHECK (progress BETWEEN 0 AND 100),
  cost DECIMAL(10,2) DEFAULT 0 NOT NULL,
  error_message TEXT,
  campaign_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT unique_campaign_per_perfume UNIQUE(perfume_id, campaign_name)
);

CREATE INDEX idx_campaigns_perfume_id ON campaigns(perfume_id);
CREATE INDEX idx_campaigns_brand_id ON campaigns(brand_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_created_at ON campaigns(created_at DESC);
```

**Testing:**
```bash
cd backend
alembic upgrade head
psql -d genads -c "\d brands"
psql -d genads -c "\d perfumes"
psql -d genads -c "\d campaigns"
```

---

#### 1.2 Update SQLAlchemy Models ✅

**File:** `backend/app/database/models.py`

**Actions:**
- [ ] Remove old `Project` model
- [ ] Create `Brand` model
- [ ] Create `Perfume` model
- [ ] Create `Campaign` model (replaces Project)
- [ ] Define relationships (brand → perfumes → campaigns)
- [ ] Add __repr__ methods for debugging

**Code Example:**
```python
from sqlalchemy import Column, String, Boolean, Integer, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .connection import Base
import uuid

class Brand(Base):
    __tablename__ = "brands"
    
    brand_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, unique=True)
    brand_name = Column(String(100), nullable=False, unique=True)
    brand_logo_url = Column(String(500), nullable=False)
    brand_guidelines_url = Column(String(500), nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    perfumes = relationship("Perfume", back_populates="brand", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="brand", cascade="all, delete-orphan")

class Perfume(Base):
    __tablename__ = "perfumes"
    
    perfume_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.brand_id", ondelete="CASCADE"), nullable=False)
    perfume_name = Column(String(200), nullable=False)
    perfume_gender = Column(String(20), nullable=False)
    front_image_url = Column(String(500), nullable=False)
    back_image_url = Column(String(500))
    top_image_url = Column(String(500))
    left_image_url = Column(String(500))
    right_image_url = Column(String(500))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    brand = relationship("Brand", back_populates="perfumes")
    campaigns = relationship("Campaign", back_populates="perfume", cascade="all, delete-orphan")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perfume_id = Column(UUID(as_uuid=True), ForeignKey("perfumes.perfume_id", ondelete="CASCADE"), nullable=False)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.brand_id", ondelete="CASCADE"), nullable=False)
    campaign_name = Column(String(200), nullable=False)
    creative_prompt = Column(Text, nullable=False)
    selected_style = Column(String(50), nullable=False)
    target_duration = Column(Integer, nullable=False)
    num_variations = Column(Integer, default=1, nullable=False)
    selected_variation_index = Column(Integer)
    status = Column(String(50), default='pending', nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    cost = Column(Numeric(10, 2), default=0, nullable=False)
    error_message = Column(Text)
    campaign_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    brand = relationship("Brand", back_populates="campaigns")
    perfume = relationship("Perfume", back_populates="campaigns")
```

**Testing:**
```python
# Test models can be imported
from app.database.models import Brand, Perfume, Campaign
print("✓ Models imported successfully")
```

---

#### 1.3 Update Pydantic Schemas ✅

**File:** `backend/app/models/schemas.py`

**Actions:**
- [ ] Remove old `ProjectCreate`, `ProjectDetail` schemas
- [ ] Create `BrandCreate`, `BrandDetail` schemas
- [ ] Create `PerfumeCreate`, `PerfumeDetail` schemas
- [ ] Create `CampaignCreate`, `CampaignDetail` schemas (replaces Project)
- [ ] Add field validators (brand_name length, perfume_name length, etc.)
- [ ] Update enums (PerfumeGender, CampaignStatus)

**Code Example:**
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums
class PerfumeGender(str, Enum):
    MASCULINE = "masculine"
    FEMININE = "feminine"
    UNISEX = "unisex"

class CampaignStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class VideoStyle(str, Enum):
    GOLD_LUXE = "gold_luxe"
    DARK_ELEGANCE = "dark_elegance"
    ROMANTIC_FLORAL = "romantic_floral"

# Brand Schemas
class BrandCreate(BaseModel):
    brand_name: str = Field(..., min_length=2, max_length=100)

class BrandDetail(BaseModel):
    brand_id: str
    brand_name: str
    brand_logo_url: str
    brand_guidelines_url: str
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime

# Perfume Schemas
class PerfumeCreate(BaseModel):
    perfume_name: str = Field(..., min_length=2, max_length=200)
    perfume_gender: PerfumeGender

class PerfumeDetail(BaseModel):
    perfume_id: str
    brand_id: str
    perfume_name: str
    perfume_gender: PerfumeGender
    front_image_url: str
    back_image_url: Optional[str]
    top_image_url: Optional[str]
    left_image_url: Optional[str]
    right_image_url: Optional[str]
    campaigns_count: int  # Computed field
    created_at: datetime
    updated_at: datetime

# Campaign Schemas
class CampaignCreate(BaseModel):
    perfume_id: str
    campaign_name: str = Field(..., min_length=2, max_length=200)
    creative_prompt: str = Field(..., min_length=10, max_length=2000)
    selected_style: VideoStyle
    target_duration: int = Field(..., ge=15, le=60)
    num_variations: int = Field(default=1, ge=1, le=3)

class CampaignDetail(BaseModel):
    campaign_id: str
    perfume_id: str
    brand_id: str
    campaign_name: str
    creative_prompt: str
    selected_style: VideoStyle
    target_duration: int
    num_variations: int
    selected_variation_index: Optional[int]
    status: CampaignStatus
    progress: int
    cost: float
    error_message: Optional[str]
    campaign_json: dict
    created_at: datetime
    updated_at: datetime
```

**Testing:**
```python
# Test schemas can be imported and validated
from app.models.schemas import BrandCreate, PerfumeCreate, CampaignCreate

brand = BrandCreate(brand_name="Test Brand")
perfume = PerfumeCreate(perfume_name="Test Perfume", perfume_gender="unisex")
campaign = CampaignCreate(
    perfume_id="xxx",
    campaign_name="Test Campaign",
    creative_prompt="Test prompt for campaign",
    selected_style="gold_luxe",
    target_duration=30,
    num_variations=2
)
print("✓ Schemas validated successfully")
```

---

#### 1.4 Create Brand CRUD Operations ✅

**File:** `backend/app/database/crud.py` (add functions)

**Actions:**
- [ ] `create_brand(user_id, brand_name, logo_url, guidelines_url) -> Brand`
- [ ] `get_brand_by_user_id(user_id) -> Brand | None`
- [ ] `get_brand_by_id(brand_id) -> Brand | None`
- [ ] `update_brand(brand_id, updates) -> Brand`
- [ ] `get_brand_stats(brand_id) -> dict` (perfumes count, campaigns count, total cost)

**Code Example:**
```python
async def create_brand(
    db: Session,
    user_id: str,
    brand_name: str,
    brand_logo_url: str,
    brand_guidelines_url: str
) -> Brand:
    brand = Brand(
        user_id=user_id,
        brand_name=brand_name,
        brand_logo_url=brand_logo_url,
        brand_guidelines_url=brand_guidelines_url,
        onboarding_completed=True
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand

async def get_brand_by_user_id(db: Session, user_id: str) -> Brand | None:
    return db.query(Brand).filter(Brand.user_id == user_id).first()

async def get_brand_stats(db: Session, brand_id: str) -> dict:
    perfumes_count = db.query(Perfume).filter(Perfume.brand_id == brand_id).count()
    campaigns_count = db.query(Campaign).filter(Campaign.brand_id == brand_id).count()
    total_cost = db.query(func.sum(Campaign.cost)).filter(Campaign.brand_id == brand_id).scalar() or 0
    
    return {
        "total_perfumes": perfumes_count,
        "total_campaigns": campaigns_count,
        "total_cost": float(total_cost)
    }
```

---

#### 1.5 Create Perfume CRUD Operations ✅

**File:** `backend/app/database/crud.py` (add functions)

**Actions:**
- [ ] `create_perfume(brand_id, name, gender, image_urls) -> Perfume`
- [ ] `get_perfumes_by_brand(brand_id, page, limit) -> list[Perfume]`
- [ ] `get_perfume_by_id(perfume_id) -> Perfume | None`
- [ ] `update_perfume(perfume_id, updates) -> Perfume`
- [ ] `delete_perfume(perfume_id) -> bool`
- [ ] `get_perfume_campaigns_count(perfume_id) -> int`

**Code Example:**
```python
async def create_perfume(
    db: Session,
    brand_id: str,
    perfume_name: str,
    perfume_gender: str,
    front_image_url: str,
    back_image_url: Optional[str] = None,
    top_image_url: Optional[str] = None,
    left_image_url: Optional[str] = None,
    right_image_url: Optional[str] = None
) -> Perfume:
    perfume = Perfume(
        brand_id=brand_id,
        perfume_name=perfume_name,
        perfume_gender=perfume_gender,
        front_image_url=front_image_url,
        back_image_url=back_image_url,
        top_image_url=top_image_url,
        left_image_url=left_image_url,
        right_image_url=right_image_url
    )
    db.add(perfume)
    db.commit()
    db.refresh(perfume)
    return perfume

async def get_perfumes_by_brand(
    db: Session,
    brand_id: str,
    page: int = 1,
    limit: int = 20
) -> tuple[list[Perfume], int]:
    offset = (page - 1) * limit
    perfumes = db.query(Perfume)\
        .filter(Perfume.brand_id == brand_id)\
        .order_by(Perfume.created_at.desc())\
        .offset(offset)\
        .limit(limit)\
        .all()
    
    total = db.query(Perfume).filter(Perfume.brand_id == brand_id).count()
    
    return perfumes, total
```

---

#### 1.6 Create Campaign CRUD Operations ✅

**File:** `backend/app/database/crud.py` (add functions)

**Actions:**
- [ ] `create_campaign(perfume_id, brand_id, name, prompt, style, duration, variations) -> Campaign`
- [ ] `get_campaigns_by_perfume(perfume_id, page, limit) -> list[Campaign]`
- [ ] `get_campaigns_by_brand(brand_id, page, limit) -> list[Campaign]`
- [ ] `get_campaign_by_id(campaign_id) -> Campaign | None`
- [ ] `update_campaign(campaign_id, updates) -> Campaign`
- [ ] `delete_campaign(campaign_id) -> bool`

**Code Example:**
```python
async def create_campaign(
    db: Session,
    perfume_id: str,
    brand_id: str,
    campaign_name: str,
    creative_prompt: str,
    selected_style: str,
    target_duration: int,
    num_variations: int = 1
) -> Campaign:
    campaign = Campaign(
        perfume_id=perfume_id,
        brand_id=brand_id,
        campaign_name=campaign_name,
        creative_prompt=creative_prompt,
        selected_style=selected_style,
        target_duration=target_duration,
        num_variations=num_variations,
        status='pending',
        progress=0,
        cost=0,
        campaign_json={}
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign
```

---

#### 1.7 Update Auth Dependency Functions ✅

**File:** `backend/app/api/auth.py`

**Actions:**
- [ ] Keep `get_current_user()` (existing)
- [ ] Add `get_current_brand_id()` dependency
- [ ] Add `verify_onboarding()` dependency
- [ ] Add `verify_perfume_ownership()` dependency
- [ ] Add `verify_campaign_ownership()` dependency

**Code Example:**
```python
async def get_current_brand_id(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> str:
    """Get brand_id for current user"""
    brand = await crud.get_brand_by_user_id(db, user_id)
    if not brand:
        raise HTTPException(404, "Brand not found. Please complete onboarding.")
    return brand.brand_id

async def verify_onboarding(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """Check if user has completed onboarding"""
    brand = await crud.get_brand_by_user_id(db, user_id)
    if not brand or not brand.onboarding_completed:
        raise HTTPException(403, "Onboarding not completed")
    return True
```

---

#### 1.8 Test Database Schema ✅

**File:** `backend/tests/test_database_schema.py` (NEW)

**Test Cases:**
- [ ] Test brand creation
- [ ] Test perfume creation with all images
- [ ] Test perfume creation with only front image
- [ ] Test campaign creation
- [ ] Test foreign key constraints (cascade delete)
- [ ] Test unique constraints (brand_name, perfume_name, campaign_name)
- [ ] Test CHECK constraints (gender, style, duration, variations)

**Code Example:**
```python
import pytest
from app.database.models import Brand, Perfume, Campaign
from app.database.crud import create_brand, create_perfume, create_campaign

@pytest.mark.asyncio
async def test_brand_creation(db_session):
    brand = await create_brand(
        db_session,
        user_id="user_123",
        brand_name="Test Brand",
        brand_logo_url="s3://bucket/brands/xxx/logo.png",
        brand_guidelines_url="s3://bucket/brands/xxx/guidelines.pdf"
    )
    assert brand.brand_id is not None
    assert brand.brand_name == "Test Brand"
    assert brand.onboarding_completed == True

@pytest.mark.asyncio
async def test_cascade_delete(db_session):
    # Create brand → perfume → campaign
    brand = await create_brand(...)
    perfume = await create_perfume(brand.brand_id, ...)
    campaign = await create_campaign(perfume.perfume_id, brand.brand_id, ...)
    
    # Delete brand
    db_session.delete(brand)
    db_session.commit()
    
    # Verify perfume and campaign are also deleted
    assert db_session.query(Perfume).filter(Perfume.perfume_id == perfume.perfume_id).first() is None
    assert db_session.query(Campaign).filter(Campaign.campaign_id == campaign.campaign_id).first() is None
```

---

### Phase 1 Deliverables

- [x] Alembic migration created and tested
- [x] SQLAlchemy models updated
- [x] Pydantic schemas updated
- [x] CRUD operations for brands, perfumes, campaigns
- [x] Auth dependency functions updated
- [x] Database schema tests passing

### Phase 1 GO/NO-GO Checkpoint

**Criteria:**
- ✅ Migration runs without errors
- ✅ All tables exist with correct columns
- ✅ All indexes created
- ✅ Foreign keys work (cascade delete)
- ✅ CRUD functions work
- ✅ Tests pass (10+ tests)

**If NO-GO:** Rollback migration, fix issues, retry

---

## Phase 2: S3 Storage Refactor (2 days, 16 hours)

**Goal:** Update S3 storage utilities to new hierarchy

### Tasks

#### 2.1 Update S3 Utility Functions ✅

**File:** `backend/app/utils/s3_utils.py`

**Actions:**
- [ ] Remove old `get_project_s3_path()`
- [ ] Add `get_brand_s3_path(brand_id)`
- [ ] Add `get_perfume_s3_path(brand_id, perfume_id)`
- [ ] Add `get_campaign_s3_path(brand_id, perfume_id, campaign_id)`
- [ ] Add `upload_brand_logo(brand_id, file)`
- [ ] Add `upload_brand_guidelines(brand_id, file)`
- [ ] Add `upload_perfume_image(brand_id, perfume_id, angle, file)`
- [ ] Add `upload_draft_video(brand_id, perfume_id, campaign_id, variation_index, scene_index, file)`
- [ ] Add `upload_draft_music(brand_id, perfume_id, campaign_id, variation_index, file)`
- [ ] Add `upload_final_video(brand_id, perfume_id, campaign_id, variation_index, file)`
- [ ] Add S3 tagging logic (type, subtype, lifecycle)

**Code Example:**
```python
def get_brand_s3_path(brand_id: str) -> str:
    return f"brands/{brand_id}/"

def get_perfume_s3_path(brand_id: str, perfume_id: str) -> str:
    return f"brands/{brand_id}/perfumes/{perfume_id}/"

def get_campaign_s3_path(brand_id: str, perfume_id: str, campaign_id: str) -> str:
    return f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"

async def upload_brand_logo(brand_id: str, file: UploadFile) -> str:
    """Upload brand logo to S3"""
    path = f"brands/{brand_id}/brand_logo.png"
    
    # Upload to S3
    s3_client.upload_fileobj(
        file.file,
        BUCKET_NAME,
        path,
        ExtraArgs={
            "ContentType": "image/png",
            "Tagging": "type=brand_asset&lifecycle=permanent"
        }
    )
    
    return f"s3://{BUCKET_NAME}/{path}"

async def upload_draft_video(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int,
    scene_index: int,
    file: str  # Local file path
) -> str:
    """Upload draft scene video to S3"""
    path = f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/variations/variation_{variation_index}/draft/scene_{scene_index}_bg.mp4"
    
    with open(file, 'rb') as f:
        s3_client.upload_fileobj(
            f,
            BUCKET_NAME,
            path,
            ExtraArgs={
                "ContentType": "video/mp4",
                "Tagging": f"type=campaign_video&subtype=draft&brand_id={brand_id}&perfume_id={perfume_id}&campaign_id={campaign_id}&variation_index={variation_index}&lifecycle=30days"
            }
        )
    
    return f"s3://{BUCKET_NAME}/{path}"
```

---

#### 2.2 Update S3 Lifecycle Policy ✅

**File:** S3 Bucket configuration (AWS Console or CLI)

**Actions:**
- [ ] Create lifecycle rule for draft videos (delete after 30 days)
- [ ] Create lifecycle rule for final videos (delete after 90 days)
- [ ] No lifecycle for brand assets (permanent)
- [ ] No lifecycle for perfume images (permanent)

**AWS CLI Command:**
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket genads-videos \
  --lifecycle-configuration file://lifecycle-policy.json
```

**lifecycle-policy.json:**
```json
{
  "Rules": [
    {
      "Id": "DeleteDraftVideosAfter30Days",
      "Filter": {
        "And": {
          "Prefix": "brands/",
          "Tags": [
            {"Key": "type", "Value": "campaign_video"},
            {"Key": "subtype", "Value": "draft"}
          ]
        }
      },
      "Status": "Enabled",
      "Expiration": {"Days": 30}
    },
    {
      "Id": "DeleteFinalVideosAfter90Days",
      "Filter": {
        "And": {
          "Prefix": "brands/",
          "Tags": [
            {"Key": "type", "Value": "campaign_video"},
            {"Key": "subtype", "Value": "final"}
          ]
        }
      },
      "Status": "Enabled",
      "Expiration": {"Days": 90}
    }
  ]
}
```

---

#### 2.3 Test S3 Upload Functions ✅

**File:** `backend/tests/test_s3_uploads.py` (NEW)

**Test Cases:**
- [ ] Test brand logo upload
- [ ] Test brand guidelines upload
- [ ] Test perfume image upload (all angles)
- [ ] Test draft video upload
- [ ] Test final video upload
- [ ] Test S3 paths are correct
- [ ] Test S3 tags are applied

**Code Example:**
```python
import pytest
from app.utils.s3_utils import upload_brand_logo, upload_perfume_image

@pytest.mark.asyncio
async def test_brand_logo_upload():
    brand_id = "test_brand_123"
    
    # Create mock file
    with open("test_logo.png", "rb") as f:
        file = UploadFile(filename="logo.png", file=f)
        url = await upload_brand_logo(brand_id, file)
    
    # Verify S3 path
    assert url == f"s3://{BUCKET_NAME}/brands/{brand_id}/brand_logo.png"
    
    # Verify file exists in S3
    assert s3_file_exists(url)
```

---

### Phase 2 Deliverables

- [x] S3 utility functions updated
- [x] S3 lifecycle policy configured
- [x] S3 upload tests passing

### Phase 2 GO/NO-GO Checkpoint

**Criteria:**
- ✅ Upload functions work for all file types
- ✅ S3 paths match new hierarchy
- ✅ S3 tags applied correctly
- ✅ Lifecycle policy configured
- ✅ Tests pass (5+ tests)

---

## Phase 3: Backend API - Brands & Perfumes (3-4 days, 24-32 hours)

**Goal:** Create API endpoints for brands and perfumes

### Tasks

#### 3.1 Create Brand Onboarding Endpoint ✅

**File:** `backend/app/api/brands.py` (NEW)

**Endpoint:** `POST /api/brands/onboard`

**Actions:**
- [ ] Accept multipart form data (brand_name, logo, guidelines)
- [ ] Validate file formats and sizes
- [ ] Upload logo to S3
- [ ] Upload guidelines to S3
- [ ] Create brand record in database
- [ ] Set onboarding_completed = true
- [ ] Return brand details

**Code Example:**
```python
@router.post("/api/brands/onboard", response_model=BrandDetail)
async def onboard_brand(
    brand_name: str = Form(...),
    logo: UploadFile = File(...),
    guidelines: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file formats
    if logo.content_type not in ["image/png", "image/jpeg", "image/webp"]:
        raise HTTPException(400, "Invalid logo format")
    if guidelines.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(400, "Invalid guidelines format")
    
    # Create brand_id
    brand_id = str(uuid.uuid4())
    
    # Upload files to S3
    logo_url = await upload_brand_logo(brand_id, logo)
    guidelines_url = await upload_brand_guidelines(brand_id, guidelines)
    
    # Create brand record
    brand = await crud.create_brand(
        db, user_id, brand_name, logo_url, guidelines_url
    )
    
    return brand
```

---

#### 3.2 Create Brand Info Endpoints ✅

**File:** `backend/app/api/brands.py`

**Endpoints:**
- `GET /api/brands/me` - Get current brand
- `GET /api/brands/me/stats` - Get brand statistics

**Code Example:**
```python
@router.get("/api/brands/me", response_model=BrandDetail)
async def get_my_brand(
    brand_id: str = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
):
    brand = await crud.get_brand_by_id(db, brand_id)
    return brand

@router.get("/api/brands/me/stats")
async def get_brand_stats(
    brand_id: str = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
):
    stats = await crud.get_brand_stats(db, brand_id)
    return stats
```

---

#### 3.3 Create Perfume CRUD Endpoints ✅

**File:** `backend/app/api/perfumes.py` (NEW)

**Endpoints:**
- `POST /api/perfumes` - Create perfume
- `GET /api/perfumes` - List perfumes
- `GET /api/perfumes/:perfumeId` - Get perfume
- `DELETE /api/perfumes/:perfumeId` - Delete perfume

**Code Example:**
```python
@router.post("/api/perfumes", response_model=PerfumeDetail)
async def create_perfume(
    perfume_name: str = Form(...),
    perfume_gender: str = Form(...),
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    top_image: Optional[UploadFile] = File(None),
    left_image: Optional[UploadFile] = File(None),
    right_image: Optional[UploadFile] = File(None),
    brand_id: str = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
):
    # Validate perfume_gender
    if perfume_gender not in ["masculine", "feminine", "unisex"]:
        raise HTTPException(400, "Invalid perfume_gender")
    
    # Create perfume_id
    perfume_id = str(uuid.uuid4())
    
    # Upload images to S3
    front_url = await upload_perfume_image(brand_id, perfume_id, "front", front_image)
    
    back_url = None
    if back_image:
        back_url = await upload_perfume_image(brand_id, perfume_id, "back", back_image)
    
    # ... same for top, left, right ...
    
    # Create perfume record
    perfume = await crud.create_perfume(
        db, brand_id, perfume_name, perfume_gender,
        front_url, back_url, top_url, left_url, right_url
    )
    
    return perfume

@router.get("/api/perfumes", response_model=PaginatedPerfumes)
async def list_perfumes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    brand_id: str = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
):
    perfumes, total = await crud.get_perfumes_by_brand(db, brand_id, page, limit)
    
    # Add campaigns_count to each perfume
    for perfume in perfumes:
        perfume.campaigns_count = await crud.get_perfume_campaigns_count(db, perfume.perfume_id)
    
    return {
        "perfumes": perfumes,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }
```

---

#### 3.4 Test Brand API Endpoints ✅

**File:** `backend/tests/test_api_brands.py` (NEW)

**Test Cases:**
- [ ] Test onboarding with valid data
- [ ] Test onboarding with invalid file format
- [ ] Test onboarding with duplicate brand name
- [ ] Test get brand info
- [ ] Test brand stats

---

#### 3.5 Test Perfume API Endpoints ✅

**File:** `backend/tests/test_api_perfumes.py` (NEW)

**Test Cases:**
- [ ] Test create perfume with all images
- [ ] Test create perfume with only front image
- [ ] Test list perfumes (pagination)
- [ ] Test get perfume details
- [ ] Test delete perfume (allowed if no campaigns)
- [ ] Test delete perfume (blocked if campaigns exist)

---

### Phase 3 Deliverables

- [x] Brand onboarding endpoint
- [x] Brand info endpoints
- [x] Perfume CRUD endpoints
- [x] API tests passing

### Phase 3 GO/NO-GO Checkpoint

**Criteria:**
- ✅ Onboarding flow works end-to-end
- ✅ Files upload to S3 correctly
- ✅ Perfume creation works with all/only-front images
- ✅ Brand isolation enforced
- ✅ Tests pass (10+ tests)

---

## Phase 4: Backend API - Campaigns (2-3 days, 16-24 hours)

**Goal:** Update campaign endpoints for new structure

### Tasks

#### 4.1 Create Campaign CRUD Endpoints ✅

**File:** `backend/app/api/campaigns.py` (UPDATED)

**Endpoints:**
- `POST /api/campaigns` - Create campaign
- `GET /api/campaigns?perfume_id=xxx` - List campaigns
- `GET /api/campaigns/:campaignId` - Get campaign
- `DELETE /api/campaigns/:campaignId` - Delete campaign

**Changes from Current:**
- Remove `brand_description`, `target_audience`, `reference_image` fields
- Add `perfume_id` field (required)
- Add `campaign_name` field (required)
- Infer `brand_id` from auth user
- Validate perfume ownership

**Code Example:**
```python
@router.post("/api/campaigns", response_model=CampaignDetail)
async def create_campaign(
    data: CampaignCreate,
    brand_id: str = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
):
    # Verify perfume belongs to brand
    perfume = await verify_perfume_ownership(data.perfume_id, brand_id, db)
    
    # Check campaign name uniqueness within perfume
    existing = db.query(Campaign).filter(
        Campaign.perfume_id == data.perfume_id,
        Campaign.campaign_name == data.campaign_name
    ).first()
    if existing:
        raise HTTPException(409, "Campaign name already exists for this perfume")
    
    # Create campaign
    campaign = await crud.create_campaign(
        db,
        perfume_id=data.perfume_id,
        brand_id=brand_id,
        campaign_name=data.campaign_name,
        creative_prompt=data.creative_prompt,
        selected_style=data.selected_style,
        target_duration=data.target_duration,
        num_variations=data.num_variations
    )
    
    return campaign

@router.get("/api/campaigns", response_model=PaginatedCampaigns)
async def list_campaigns(
    perfume_id: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    brand_id: str = Depends(get_current_brand_id),
    db: Session = Depends(get_db)
):
    # Verify perfume belongs to brand
    await verify_perfume_ownership(perfume_id, brand_id, db)
    
    # Get campaigns for perfume
    campaigns, total = await crud.get_campaigns_by_perfume(db, perfume_id, page, limit)
    
    return {
        "campaigns": campaigns,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }
```

---

#### 4.2 Update Generation Endpoints ✅

**File:** `backend/app/api/generation.py` (UPDATED)

**Endpoints:**
- `POST /api/generation/campaigns/:id/generate` (UPDATED)
- `GET /api/generation/campaigns/:id/progress` (UPDATED)
- `POST /api/generation/campaigns/:id/select-variation` (UPDATED)

**Changes:**
- Replace `project_id` with `campaign_id`
- Verify campaign ownership
- Load campaign + perfume + brand in pipeline

---

#### 4.3 Test Campaign API Endpoints ✅

**File:** `backend/tests/test_api_campaigns.py` (UPDATED)

**Test Cases:**
- [ ] Test create campaign
- [ ] Test create campaign with duplicate name (should fail)
- [ ] Test list campaigns for perfume
- [ ] Test get campaign details
- [ ] Test delete campaign (allowed if not processing)
- [ ] Test delete campaign (blocked if processing)
- [ ] Test campaign ownership verification

---

### Phase 4 Deliverables

- [x] Campaign CRUD endpoints updated
- [x] Generation endpoints updated
- [x] API tests passing

### Phase 4 GO/NO-GO Checkpoint

**Criteria:**
- ✅ Campaign creation works
- ✅ Campaign listing filtered by perfume
- ✅ Ownership verification works
- ✅ Tests pass (8+ tests)

---

## Phase 5: Generation Pipeline Updates (2-2.5 days, 16-20 hours)

**Goal:** Update generation pipeline for new data structure

### Tasks

#### 5.1 Update Pipeline to Use New Data Models ✅

**File:** `backend/app/jobs/generation_pipeline.py`

**Changes:**
- [ ] Replace `project_id` with `campaign_id` in run() method
- [ ] Load campaign + perfume + brand from database
- [ ] Use brand guidelines from brand table (not per-campaign)
- [ ] Use perfume images from perfumes table
- [ ] Remove reference image extraction (STEP 0)
- [ ] Update S3 paths to new hierarchy
- [ ] Store results in campaign_json

**Code Example:**
```python
async def run(campaign_id: str):
    """Generate video for campaign"""
    
    # LOAD DATA (3 DB calls)
    campaign = await crud.get_campaign(campaign_id)
    perfume = await crud.get_perfume(campaign.perfume_id)
    brand = await crud.get_brand(campaign.brand_id)
    
    # REMOVED: STEP 0 - Reference image extraction
    
    # STEP 1: Extract brand guidelines (UPDATED - use brand table)
    brand_style = await get_brand_style(brand.brand_id)  # Cached
    
    # STEP 2: Plan scenes (UPDATED - use perfume data)
    scenes = await scene_planner.plan_scenes(
        creative_prompt=campaign.creative_prompt,
        brand_name=brand.brand_name,
        perfume_name=perfume.perfume_name,
        perfume_gender=perfume.perfume_gender,
        selected_style=campaign.selected_style,
        duration=campaign.target_duration,
        brand_style=brand_style,
        num_variations=campaign.num_variations
    )
    
    # STEP 3: Extract perfume product (UPDATED - use perfume images)
    product_mask = await product_extractor.extract_perfume_for_campaign(
        campaign, perfume
    )
    
    # STEP 4: Generate videos (UPDATED - new S3 paths)
    for variation_index in range(campaign.num_variations):
        scene_videos = await video_generator.generate_scene_videos_batch(
            scenes[variation_index],
            style_spec,
            variation_index
        )
        
        # Upload to S3 with NEW paths
        for scene_index, video in enumerate(scene_videos):
            s3_path = await upload_draft_video(
                brand.brand_id,
                perfume.perfume_id,
                campaign.campaign_id,
                variation_index,
                scene_index,
                video
            )
    
    # ... rest of pipeline (compositing, text, audio, rendering) ...
    
    # STEP 8: Upload final videos (UPDATED - new S3 paths)
    for variation_index in range(campaign.num_variations):
        final_video_path = await upload_final_video(
            brand.brand_id,
            perfume.perfume_id,
            campaign.campaign_id,
            variation_index,
            final_video
        )
    
    # Update campaign with results
    await crud.update_campaign(campaign_id, {
        "status": "completed",
        "progress": 100,
        "campaign_json": {
            "scenes": scenes,
            "styleSpec": style_spec,
            "variationPaths": variation_paths,
            "costBreakdown": cost_breakdown
        }
    })
```

---

#### 5.2 Update Product Extractor ✅

**File:** `backend/app/services/product_extractor.py`

**Changes:**
- [ ] Add `get_perfume_image(perfume, angle)` method with fallback logic
- [ ] Add `extract_perfume_for_campaign(campaign, perfume)` method
- [ ] Use perfume.front_image_url for extraction
- [ ] Fallback to front image if other angles missing

**Code Example:**
```python
async def get_perfume_image(perfume: Perfume, angle: str) -> str:
    """Get perfume image with fallback to front"""
    if angle == "front":
        return perfume.front_image_url
    elif angle == "back" and perfume.back_image_url:
        return perfume.back_image_url
    elif angle == "top" and perfume.top_image_url:
        return perfume.top_image_url
    elif angle == "left" and perfume.left_image_url:
        return perfume.left_image_url
    elif angle == "right" and perfume.right_image_url:
        return perfume.right_image_url
    else:
        logger.warning(f"Perfume {perfume.perfume_id} missing {angle} image, falling back to front")
        return perfume.front_image_url
```

---

#### 5.3 Remove Reference Image Extractor ✅

**File:** `backend/app/services/reference_image_extractor.py`

**Actions:**
- [ ] Delete file entirely (feature removed)
- [ ] Remove from `app/services/__init__.py`
- [ ] Remove from pipeline imports

---

#### 5.4 Test Generation Pipeline ✅

**File:** `backend/tests/test_generation_pipeline.py` (UPDATED)

**Test Cases:**
- [ ] Test pipeline with new data models
- [ ] Test brand guidelines extraction
- [ ] Test perfume image fallback
- [ ] Test S3 paths are correct
- [ ] Test campaign_json structure

---

### Phase 5 Deliverables

- [x] Pipeline updated for new data models
- [x] Product extractor updated
- [x] Reference image extractor removed
- [x] Pipeline tests passing

### Phase 5 GO/NO-GO Checkpoint

**Criteria:**
- ✅ Pipeline generates videos successfully
- ✅ Brand guidelines applied correctly
- ✅ Perfume images used correctly
- ✅ S3 paths match new hierarchy
- ✅ Tests pass (5+ tests)

---

## Phase 6: Frontend - Pages (4-5 days, 32-40 hours)

**Goal:** Create and update frontend pages

### Tasks

#### 6.1 Create Onboarding Page ✅

**File:** `frontend/src/pages/Onboarding.tsx` (NEW)

**Components:**
- [ ] Brand name input
- [ ] Logo upload drag-and-drop
- [ ] Guidelines upload drag-and-drop
- [ ] "Complete Onboarding" button
- [ ] Loading spinner during upload
- [ ] Success message

**Functionality:**
- [ ] Validate brand name (2-100 chars)
- [ ] Validate logo file (PNG/JPG/WebP, max 5MB)
- [ ] Validate guidelines file (PDF/DOCX, max 10MB)
- [ ] Upload files to API
- [ ] Show progress during upload
- [ ] Redirect to /dashboard on success

---

#### 6.2 Update Dashboard Page (Perfume List) ✅

**File:** `frontend/src/pages/Dashboard.tsx` (UPDATED)

**Layout:**
- [ ] Header: "Your Perfumes" + brand name
- [ ] "+ Add Perfume" button
- [ ] Grid of perfume cards (responsive)
- [ ] Empty state if no perfumes

**Functionality:**
- [ ] Fetch perfumes from API (GET /api/perfumes)
- [ ] Display perfume cards with:
  - Front image thumbnail
  - Perfume name
  - Gender badge
  - Campaign count
- [ ] Click card → navigate to /perfumes/:perfumeId
- [ ] "+ Add Perfume" → open modal

---

#### 6.3 Create Add Perfume Modal/Page ✅

**File:** `frontend/src/pages/AddPerfume.tsx` (NEW) or Modal in Dashboard

**Components:**
- [ ] Perfume name input
- [ ] Gender selector (3 buttons: M/F/U)
- [ ] Front image upload (required, red border if empty)
- [ ] Additional images upload (4 slots, optional)
- [ ] "Add Perfume" button

**Functionality:**
- [ ] Validate perfume name (2-200 chars)
- [ ] Validate front image (required)
- [ ] Upload images to API
- [ ] Show loading spinner
- [ ] Close modal and refresh dashboard on success

---

#### 6.4 Create Campaign Dashboard Page ✅

**File:** `frontend/src/pages/CampaignDashboard.tsx` (NEW)

**Layout:**
- [ ] Breadcrumb: "Your Perfumes > [Perfume Name]"
- [ ] Back button to /dashboard
- [ ] Perfume details card (large image, name, gender, image count)
- [ ] "Ad Campaigns" section
- [ ] "+ Create Campaign" button
- [ ] Grid of campaign cards (responsive)
- [ ] Empty state if no campaigns

**Functionality:**
- [ ] Fetch perfume details (GET /api/perfumes/:perfumeId)
- [ ] Fetch campaigns (GET /api/campaigns?perfume_id=xxx)
- [ ] Display campaign cards with:
  - Thumbnail (first frame of video or placeholder)
  - Campaign name
  - Status badge
  - Duration
  - Variations count
  - Cost
  - Created date
- [ ] Click card → navigate to /campaigns/:campaignId/results
- [ ] "+ Create Campaign" → navigate to create page

---

#### 6.5 Update Create Campaign Page ✅

**File:** `frontend/src/pages/CreateCampaign.tsx` (UPDATED)

**Changes:**
- [ ] REMOVE: Brand name input (auto-filled from brand table)
- [ ] REMOVE: Brand description input (auto-filled from brand table)
- [ ] REMOVE: Target audience input (feature removed)
- [ ] REMOVE: Reference image upload (feature removed)
- [ ] REMOVE: Perfume name input (auto-filled from selected perfume)
- [ ] REMOVE: Perfume gender input (auto-filled from selected perfume)
- [ ] REMOVE: Product image upload (auto-filled from perfume images)
- [ ] ADD: Campaign name input (NEW, required)
- [ ] KEEP: Creative prompt (required)
- [ ] KEEP: Video style selector (3 perfume styles)
- [ ] KEEP: Duration slider (15-60s)
- [ ] KEEP: Variations selector (1-3)

**Auto-populated badges (read-only):**
- [ ] Brand: Show brand name from context
- [ ] Perfume: Show perfume name from URL params
- [ ] Gender: Show perfume gender
- [ ] Images: Show "N images available"

**Functionality:**
- [ ] Fetch perfume details on load
- [ ] Validate campaign name (2-200 chars)
- [ ] Validate creative prompt (10-2000 chars)
- [ ] Submit to POST /api/campaigns
- [ ] Navigate to /campaigns/:id/progress on success

---

#### 6.6 Update Campaign Results Page ✅

**File:** `frontend/src/pages/CampaignResults.tsx` (UPDATED from VideoResults)

**Changes:**
- [ ] Update breadcrumb: "Your Perfumes > [Perfume Name] > [Campaign Name]"
- [ ] Update back button: Navigate to /perfumes/:perfumeId
- [ ] Display perfume name (not brand description)
- [ ] Display campaign name
- [ ] KEEP: Video player with variation tabs
- [ ] KEEP: Download button
- [ ] UPDATE: API calls use campaign_id

**Functionality:**
- [ ] Fetch campaign details (GET /api/campaigns/:campaignId)
- [ ] Fetch perfume details (GET /api/perfumes/:perfumeId)
- [ ] Display video player with correct variation
- [ ] Download final_video.mp4 for selected variation

---

### Phase 6 Deliverables

- [x] Onboarding page created
- [x] Dashboard updated (perfume list)
- [x] Add perfume modal created
- [x] Campaign dashboard created
- [x] Create campaign page updated
- [x] Campaign results page updated

### Phase 6 GO/NO-GO Checkpoint

**Criteria:**
- ✅ All pages render correctly
- ✅ Navigation works
- ✅ Form validation works
- ✅ API calls succeed
- ✅ No TypeScript errors

---

## Phase 7: Frontend - Components & Routing (2-3 days, 16-24 hours)

**Goal:** Create reusable components and update routing

### Tasks

#### 7.1 Create PerfumeCard Component ✅

**File:** `frontend/src/components/PerfumeCard.tsx` (NEW)

**Props:**
- perfume: Perfume
- onClick: () => void

**UI:**
- Front image thumbnail
- Perfume name
- Gender badge
- Campaign count badge
- Hover effects (gold ring)

---

#### 7.2 Create CampaignCard Component ✅

**File:** `frontend/src/components/CampaignCard.tsx` (NEW)

**Props:**
- campaign: Campaign
- onClick: () => void

**UI:**
- Video thumbnail or placeholder
- Campaign name
- Status badge (processing/completed/failed)
- Duration + variations
- Cost
- Created date

---

#### 7.3 Update ProtectedRoute Component ✅

**File:** `frontend/src/components/ProtectedRoute.tsx` (UPDATED)

**Changes:**
- [ ] Add `useBrand()` hook call
- [ ] Check onboarding_completed flag
- [ ] Redirect to /onboarding if not completed
- [ ] Allow `skipOnboardingCheck` prop for /onboarding route

**Code Example:**
```typescript
interface ProtectedRouteProps {
  children: React.ReactNode;
  skipOnboardingCheck?: boolean;
}

export function ProtectedRoute({ children, skipOnboardingCheck }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const { brand, loading: brandLoading } = useBrand();
  const navigate = useNavigate();
  
  useEffect(() => {
    if (loading || brandLoading) return;
    
    if (!user) {
      navigate('/login');
      return;
    }
    
    if (!skipOnboardingCheck && (!brand || !brand.onboarding_completed)) {
      navigate('/onboarding');
      return;
    }
  }, [user, brand, loading, brandLoading, skipOnboardingCheck]);
  
  // ... rest ...
}
```

---

#### 7.4 Create useBrand Hook ✅

**File:** `frontend/src/hooks/useBrand.ts` (NEW)

**Functionality:**
- [ ] Fetch brand details (GET /api/brands/me)
- [ ] Cache brand in context
- [ ] Return brand, loading, error

---

#### 7.5 Update Routing ✅

**File:** `frontend/src/App.tsx`

**Routes:**
```typescript
<Routes>
  {/* Public */}
  <Route path="/" element={<Landing />} />
  <Route path="/login" element={<Login />} />
  <Route path="/signup" element={<Signup />} />
  
  {/* Onboarding (protected, no onboarding check) */}
  <Route path="/onboarding" element={
    <ProtectedRoute skipOnboardingCheck>
      <Onboarding />
    </ProtectedRoute>
  } />
  
  {/* Main App (protected, require onboarding) */}
  <Route path="/dashboard" element={
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  } />
  
  <Route path="/perfumes/add" element={
    <ProtectedRoute>
      <AddPerfume />
    </ProtectedRoute>
  } />
  
  <Route path="/perfumes/:perfumeId" element={
    <ProtectedRoute>
      <CampaignDashboard />
    </ProtectedRoute>
  } />
  
  <Route path="/perfumes/:perfumeId/campaigns/create" element={
    <ProtectedRoute>
      <CreateCampaign />
    </ProtectedRoute>
  } />
  
  <Route path="/campaigns/:campaignId/progress" element={
    <ProtectedRoute>
      <GenerationProgress />
    </ProtectedRoute>
  } />
  
  <Route path="/campaigns/:campaignId/select" element={
    <ProtectedRoute>
      <VideoSelection />
    </ProtectedRoute>
  } />
  
  <Route path="/campaigns/:campaignId/results" element={
    <ProtectedRoute>
      <CampaignResults />
    </ProtectedRoute>
  } />
</Routes>
```

---

### Phase 7 Deliverables

- [x] PerfumeCard component
- [x] CampaignCard component
- [x] ProtectedRoute updated
- [x] useBrand hook created
- [x] Routing updated

### Phase 7 GO/NO-GO Checkpoint

**Criteria:**
- ✅ All routes work
- ✅ Onboarding guard works
- ✅ Components render correctly
- ✅ Navigation works end-to-end

---

## Phase 8: Integration & Testing (3-4 days, 24-32 hours)

**Goal:** End-to-end testing and bug fixes

### Tasks

#### 8.1 End-to-End Onboarding Test ✅

**Test Flow:**
1. Sign up new user
2. Land on onboarding page
3. Fill brand form
4. Upload logo and guidelines
5. Submit
6. Verify brand created in database
7. Verify files uploaded to S3
8. Verify redirected to dashboard

---

#### 8.2 End-to-End Perfume Creation Test ✅

**Test Flow:**
1. Login as existing user
2. Click "+ Add Perfume"
3. Fill perfume form
4. Upload only front image
5. Submit
6. Verify perfume created in database
7. Verify image uploaded to S3
8. Verify perfume appears in dashboard

---

#### 8.3 End-to-End Campaign Creation Test ✅

**Test Flow:**
1. Click on perfume card
2. Click "+ Create Campaign"
3. Fill campaign form
4. Submit
5. Watch generation progress
6. Verify campaign created in database
7. Verify videos generated and uploaded to S3
8. Verify campaign appears in campaign dashboard

---

#### 8.4 Brand Isolation Test ✅

**Test:**
- Create User A with Brand A
- Create User B with Brand B
- Verify User A cannot access Brand B's perfumes
- Verify User A cannot access Brand B's campaigns
- Verify API returns 404 (not 403) to avoid info leak

---

#### 8.5 Cascade Delete Test ✅

**Test:**
- Create brand → perfume → campaign
- Delete brand
- Verify perfume deleted
- Verify campaign deleted
- Verify S3 files remain (lifecycle will delete later)

---

#### 8.6 S3 Storage Verification Test ✅

**Test:**
- Create brand with logo and guidelines
- Create perfume with 3 images
- Create campaign with 2 variations
- Verify S3 structure matches:
  ```
  brands/{brand_id}/
    brand_logo.png
    brand_guidelines.pdf
    perfumes/{perfume_id}/
      front.png
      back.png
      top.png
      campaigns/{campaign_id}/
        variations/
          variation_0/
            draft/
              scene_1_bg.mp4
              ...
              music.mp3
            final_video.mp4
          variation_1/
            ...
  ```

---

#### 8.7 Performance Test ✅

**Test:**
- Create 10 perfumes
- Create 50 campaigns
- Measure:
  - Dashboard load time (<2s)
  - Campaign list load time (<1s)
  - Video generation time (~5-7 min per campaign)

---

#### 8.8 Bug Fixes & Polish ✅

**Actions:**
- [ ] Fix any bugs discovered during testing
- [ ] Add loading spinners where missing
- [ ] Add error messages where missing
- [ ] Improve UX based on feedback
- [ ] Add toast notifications
- [ ] Polish UI animations

---

### Phase 8 Deliverables

- [x] All E2E tests passing
- [x] Brand isolation verified
- [x] S3 storage verified
- [x] Performance acceptable
- [x] All bugs fixed

### Phase 8 GO/NO-GO Checkpoint

**Criteria:**
- ✅ Onboarding flow works 100%
- ✅ Perfume creation works 100%
- ✅ Campaign creation works 100%
- ✅ Brand isolation verified
- ✅ No critical bugs
- ✅ Performance meets targets

---

## Summary Checklist

### Database & Models
- [ ] Migration created and run
- [ ] 3 tables created (brands, perfumes, campaigns)
- [ ] All indexes created
- [ ] Foreign keys working
- [ ] CRUD operations working
- [ ] Tests passing

### S3 Storage
- [ ] S3 utility functions updated
- [ ] Lifecycle policy configured
- [ ] Upload functions tested
- [ ] Storage hierarchy verified

### Backend API
- [ ] Brand endpoints working
- [ ] Perfume endpoints working
- [ ] Campaign endpoints working
- [ ] Generation endpoints updated
- [ ] Auth guards working
- [ ] Tests passing

### Generation Pipeline
- [ ] Pipeline updated for new data models
- [ ] Brand guidelines extraction working
- [ ] Perfume images working
- [ ] Reference image removed
- [ ] S3 paths correct
- [ ] Tests passing

### Frontend
- [ ] Onboarding page working
- [ ] Dashboard showing perfumes
- [ ] Add perfume working
- [ ] Campaign dashboard showing campaigns
- [ ] Create campaign updated
- [ ] Campaign results updated
- [ ] Routing working
- [ ] No TypeScript errors

### Integration Testing
- [ ] E2E onboarding test passing
- [ ] E2E perfume creation passing
- [ ] E2E campaign creation passing
- [ ] Brand isolation verified
- [ ] Cascade deletes working
- [ ] S3 storage verified
- [ ] Performance acceptable
- [ ] All bugs fixed

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] No TypeScript errors
- [ ] No linting errors
- [ ] Database migration ready
- [ ] S3 lifecycle policy configured
- [ ] Environment variables set

### Deployment
- [ ] Run database migration
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel
- [ ] Verify backend health check
- [ ] Verify frontend loads
- [ ] Smoke test critical flows

### Post-Deployment
- [ ] Create test brand
- [ ] Create test perfume
- [ ] Create test campaign
- [ ] Verify videos generate
- [ ] Monitor error logs
- [ ] Monitor performance

---

**Status:** Ready for Implementation  
**Estimated Duration:** 3-4 weeks (120-160 hours)  
**Last Updated:** November 18, 2025

