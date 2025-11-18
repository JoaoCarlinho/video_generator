# B2B SaaS Overhaul - Technical Architecture

**Version:** 1.0  
**Created:** November 18, 2025  
**Status:** Design Phase  
**Complexity:** HIGH - Major architectural refactor

---

## Architecture Overview

### System Transformation

**FROM (Current):**
```
auth.users → projects (flat structure, shared across users)
             ↓
        S3: projects/{project_id}/...
```

**TO (New):**
```
auth.users → brands → perfumes → campaigns (3-tier hierarchy)
                ↓        ↓          ↓
        S3: brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/...
```

### Key Architectural Changes

1. **Data Model:** Flat → 3-Tier Hierarchy
2. **Storage:** Project-centric → Brand-centric
3. **Access Control:** Shared → Brand-isolated
4. **Onboarding:** Optional → Mandatory
5. **Asset Management:** Per-campaign → Brand-level + Perfume-level

---

## Database Architecture

### Entity Relationship Diagram

```
┌─────────────────┐
│  auth.users     │  (Supabase Auth)
│  - id           │
│  - email        │
│  - created_at   │
└────────┬────────┘
         │ 1:1
         ▼
┌─────────────────┐
│  brands         │  (NEW)
│  - brand_id     │  PK
│  - user_id      │  FK (unique) → auth.users.id
│  - brand_name   │  UNIQUE
│  - logo_url     │
│  - guidelines   │
│  - onboarding   │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐
│  perfumes       │  (NEW)
│  - perfume_id   │  PK
│  - brand_id     │  FK → brands.brand_id
│  - name         │  UNIQUE per brand
│  - gender       │
│  - front_img    │  REQUIRED
│  - back_img     │  optional
│  - top_img      │  optional
│  - left_img     │  optional
│  - right_img    │  optional
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐
│  campaigns      │  (REPLACES projects)
│  - campaign_id  │  PK
│  - perfume_id   │  FK → perfumes.perfume_id
│  - brand_id     │  FK → brands.brand_id (denormalized)
│  - name         │  UNIQUE per perfume
│  - prompt       │
│  - style        │
│  - duration     │
│  - variations   │
│  - status       │
│  - cost         │
│  - campaign_json│
└─────────────────┘
```

### Table Definitions

#### 1. `brands` Table (NEW)

**Purpose:** One brand per user, stores brand identity

```sql
CREATE TABLE brands (
  -- Primary Key
  brand_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Foreign Keys
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Brand Identity
  brand_name VARCHAR(100) NOT NULL UNIQUE,
  brand_logo_url VARCHAR(500) NOT NULL,
  brand_guidelines_url VARCHAR(500) NOT NULL,
  
  -- Onboarding Flag
  onboarding_completed BOOLEAN DEFAULT false NOT NULL,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE INDEX idx_brands_user_id ON brands(user_id);
CREATE INDEX idx_brands_onboarding ON brands(onboarding_completed);
CREATE UNIQUE INDEX idx_brands_name ON brands(LOWER(brand_name));

-- Constraints
ALTER TABLE brands ADD CONSTRAINT check_brand_name_length 
  CHECK (char_length(brand_name) >= 2 AND char_length(brand_name) <= 100);
```

**Fields:**
- `brand_id` - UUID primary key
- `user_id` - FK to auth.users (1:1 relationship, UNIQUE)
- `brand_name` - Unique brand name (case-insensitive)
- `brand_logo_url` - S3 path: `brands/{brand_id}/brand_logo.png`
- `brand_guidelines_url` - S3 path: `brands/{brand_id}/brand_guidelines.pdf`
- `onboarding_completed` - Boolean flag for auth guard
- `created_at`, `updated_at` - Audit timestamps

**Business Rules:**
1. One user can have only ONE brand (enforced by UNIQUE on user_id)
2. Brand name must be globally unique (enforced by UNIQUE index)
3. Cannot delete brand if perfumes exist (enforced by FK constraint)
4. Logo and guidelines are REQUIRED (NOT NULL)

---

#### 2. `perfumes` Table (NEW)

**Purpose:** Perfume library per brand, stores product images

```sql
CREATE TABLE perfumes (
  -- Primary Key
  perfume_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Foreign Keys
  brand_id UUID NOT NULL REFERENCES brands(brand_id) ON DELETE CASCADE,
  
  -- Perfume Details
  perfume_name VARCHAR(200) NOT NULL,
  perfume_gender VARCHAR(20) NOT NULL 
    CHECK (perfume_gender IN ('masculine', 'feminine', 'unisex')),
  
  -- Product Images (S3 URLs)
  front_image_url VARCHAR(500) NOT NULL,  -- REQUIRED
  back_image_url VARCHAR(500),            -- optional
  top_image_url VARCHAR(500),             -- optional
  left_image_url VARCHAR(500),            -- optional
  right_image_url VARCHAR(500),           -- optional
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  
  -- Unique constraint: perfume name unique within brand
  CONSTRAINT unique_perfume_per_brand UNIQUE(brand_id, perfume_name)
);

-- Indexes
CREATE INDEX idx_perfumes_brand_id ON perfumes(brand_id);
CREATE INDEX idx_perfumes_gender ON perfumes(perfume_gender);
CREATE INDEX idx_perfumes_created_at ON perfumes(created_at DESC);

-- Constraints
ALTER TABLE perfumes ADD CONSTRAINT check_perfume_name_length 
  CHECK (char_length(perfume_name) >= 2 AND char_length(perfume_name) <= 200);
```

**Fields:**
- `perfume_id` - UUID primary key
- `brand_id` - FK to brands (1:N relationship)
- `perfume_name` - Unique within brand (enforced by composite UNIQUE)
- `perfume_gender` - Enum: masculine/feminine/unisex
- `front_image_url` - REQUIRED, S3 path: `brands/{brand_id}/perfumes/{perfume_id}/front.png`
- `back_image_url` - Optional, S3 path: `brands/{brand_id}/perfumes/{perfume_id}/back.png`
- `top_image_url` - Optional, S3 path: `brands/{brand_id}/perfumes/{perfume_id}/top.png`
- `left_image_url` - Optional, S3 path: `brands/{brand_id}/perfumes/{perfume_id}/left.png`
- `right_image_url` - Optional, S3 path: `brands/{brand_id}/perfumes/{perfume_id}/right.png`

**Business Rules:**
1. Perfume name must be unique within brand (not globally)
2. Front image is REQUIRED (NOT NULL)
3. Other images are OPTIONAL (can be NULL)
4. Cannot delete perfume if campaigns exist (application-level check)
5. Gender must be one of three values (enforced by CHECK)

---

#### 3. `campaigns` Table (REPLACES `projects`)

**Purpose:** Ad campaigns per perfume, stores generation results

```sql
CREATE TABLE campaigns (
  -- Primary Key
  campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Foreign Keys
  perfume_id UUID NOT NULL REFERENCES perfumes(perfume_id) ON DELETE CASCADE,
  brand_id UUID NOT NULL REFERENCES brands(brand_id) ON DELETE CASCADE,  -- Denormalized
  
  -- Campaign Details
  campaign_name VARCHAR(200) NOT NULL,
  creative_prompt TEXT NOT NULL,
  
  -- Video Settings
  selected_style VARCHAR(50) NOT NULL 
    CHECK (selected_style IN ('gold_luxe', 'dark_elegance', 'romantic_floral')),
  target_duration INTEGER NOT NULL 
    CHECK (target_duration BETWEEN 15 AND 60),
  
  -- Variation Settings
  num_variations INTEGER DEFAULT 1 NOT NULL 
    CHECK (num_variations BETWEEN 1 AND 3),
  selected_variation_index INTEGER 
    CHECK (selected_variation_index IS NULL OR selected_variation_index BETWEEN 0 AND 2),
  
  -- Generation Status
  status VARCHAR(50) DEFAULT 'pending' NOT NULL
    CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  progress INTEGER DEFAULT 0 NOT NULL 
    CHECK (progress BETWEEN 0 AND 100),
  cost DECIMAL(10,2) DEFAULT 0 NOT NULL,
  error_message TEXT,
  
  -- Campaign Data (JSONB)
  campaign_json JSONB NOT NULL,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  
  -- Unique constraint: campaign name unique within perfume
  CONSTRAINT unique_campaign_per_perfume UNIQUE(perfume_id, campaign_name)
);

-- Indexes
CREATE INDEX idx_campaigns_perfume_id ON campaigns(perfume_id);
CREATE INDEX idx_campaigns_brand_id ON campaigns(brand_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_created_at ON campaigns(created_at DESC);
CREATE INDEX idx_campaigns_cost ON campaigns(cost);

-- Constraints
ALTER TABLE campaigns ADD CONSTRAINT check_campaign_name_length 
  CHECK (char_length(campaign_name) >= 2 AND char_length(campaign_name) <= 200);

ALTER TABLE campaigns ADD CONSTRAINT check_creative_prompt_length 
  CHECK (char_length(creative_prompt) >= 10 AND char_length(creative_prompt) <= 2000);
```

**Fields:**
- `campaign_id` - UUID primary key
- `perfume_id` - FK to perfumes (1:N relationship)
- `brand_id` - FK to brands (denormalized for quick queries)
- `campaign_name` - Unique within perfume
- `creative_prompt` - Required, 10-2000 chars
- `selected_style` - Enum: gold_luxe/dark_elegance/romantic_floral
- `target_duration` - 15-60 seconds (TikTok limit)
- `num_variations` - 1-3 variations
- `selected_variation_index` - Selected variation (0-2, nullable)
- `status` - Enum: pending/processing/completed/failed
- `progress` - 0-100%
- `cost` - Total cost in USD
- `error_message` - Nullable error text
- `campaign_json` - JSONB (scene data, style spec, video metadata)

**campaign_json Structure:**
```json
{
  "scenes": [
    {
      "sceneId": "scene_1",
      "role": "hook",
      "backgroundPrompt": "...",
      "duration": 4,
      "overlay": {...}
    }
  ],
  "styleSpec": {
    "lighting": "...",
    "camera": "...",
    "mood": "...",
    "colors": [...]
  },
  "videoMetadata": {
    "resolution": "1080x1920",
    "aspectRatio": "9:16",
    "totalDuration": 30,
    "selectedStyle": "dark_elegance"
  },
  "costBreakdown": {
    "scenePlanning": 0.01,
    "videoGeneration": 0.80,
    "musicGeneration": 0.20,
    "total": 1.01
  },
  "variationPaths": {
    "variation_0": {
      "draft": {
        "scene_1": "s3://bucket/brands/.../variation_0/draft/scene_1_bg.mp4",
        "scene_2": "s3://bucket/brands/.../variation_0/draft/scene_2_bg.mp4",
        "scene_3": "s3://bucket/brands/.../variation_0/draft/scene_3_bg.mp4",
        "scene_4": "s3://bucket/brands/.../variation_0/draft/scene_4_bg.mp4",
        "music": "s3://bucket/brands/.../variation_0/draft/music.mp3"
      },
      "final": "s3://bucket/brands/.../variation_0/final_video.mp4"
    },
    "variation_1": {...},
    "variation_2": {...}
  }
}
```

**Business Rules:**
1. Campaign name must be unique within perfume (not globally)
2. Creative prompt is REQUIRED (10-2000 chars)
3. Style must be one of 3 perfume styles
4. Duration must be 15-60 seconds (TikTok constraint)
5. Variations: 1-3 only
6. Cannot delete campaign if status = 'processing'

---

### Foreign Key Relationships

```sql
-- Cascade Deletes
auth.users (DELETE) 
  → brands (CASCADE DELETE) 
    → perfumes (CASCADE DELETE) 
      → campaigns (CASCADE DELETE)

-- Example: Delete user deletes entire brand hierarchy
DELETE FROM auth.users WHERE id = 'xxx';
  → Deletes brand
    → Deletes all perfumes
      → Deletes all campaigns
```

**Cascade Behavior:**
- Delete user → Deletes brand + all perfumes + all campaigns
- Delete brand → Deletes all perfumes + all campaigns
- Delete perfume → Deletes all campaigns for that perfume
- Delete campaign → Only deletes that campaign

**Business Logic Constraints (Application-Level):**
- Cannot delete brand if `perfumes_count > 0` (show error)
- Cannot delete perfume if `campaigns_count > 0` (show error)
- Cannot delete campaign if `status = 'processing'` (show error)

---

## S3 Storage Architecture

### Storage Hierarchy

```
s3://genads-videos/
  brands/
    {brand_id}/                              # Brand folder (UUID)
      ├── brand_logo.png                     # Brand logo (PNG/JPG)
      ├── brand_guidelines.pdf               # Brand guidelines (PDF/DOCX)
      │
      └── perfumes/
          {perfume_id}/                      # Perfume folder (UUID)
            ├── front.png                    # REQUIRED
            ├── back.png                     # optional
            ├── top.png                      # optional
            ├── left.png                     # optional
            ├── right.png                    # optional
            │
            └── campaigns/
                {campaign_id}/               # Campaign folder (UUID)
                  └── variations/
                      ├── variation_0/
                      │   ├── draft/
                      │   │   ├── scene_1_bg.mp4
                      │   │   ├── scene_2_bg.mp4
                      │   │   ├── scene_3_bg.mp4
                      │   │   ├── scene_4_bg.mp4
                      │   │   └── music.mp3
                      │   └── final_video.mp4
                      │
                      ├── variation_1/
                      │   ├── draft/
                      │   │   └── ...
                      │   └── final_video.mp4
                      │
                      └── variation_2/
                          ├── draft/
                          │   └── ...
                          └── final_video.mp4
```

### Storage Rules

#### Brand-Level Storage

**Files:**
- `brand_logo.png` - Brand logo image
- `brand_guidelines.pdf` - Brand guidelines document

**Constraints:**
- Logo: PNG/JPG/WebP, max 5MB
- Guidelines: PDF/DOCX, max 10MB
- Lifecycle: **KEEP FOREVER** (no auto-delete)

**S3 Tags:**
```json
{
  "type": "brand_asset",
  "brand_id": "xxx",
  "lifecycle": "permanent"
}
```

---

#### Perfume-Level Storage

**Files:**
- `front.png` - Front view (REQUIRED)
- `back.png` - Back view (optional)
- `top.png` - Top view (optional)
- `left.png` - Left view (optional)
- `right.png` - Right view (optional)

**Constraints:**
- Format: PNG/JPG/WebP
- Size: Max 5MB per image
- Lifecycle: **KEEP FOREVER** (no auto-delete)

**S3 Tags:**
```json
{
  "type": "perfume_image",
  "brand_id": "xxx",
  "perfume_id": "xxx",
  "angle": "front|back|top|left|right",
  "lifecycle": "permanent"
}
```

---

#### Campaign-Level Storage (NEW STRUCTURE)

**Directory Structure:**
```
campaigns/{campaign_id}/variations/
  variation_0/
    draft/              # Intermediate files (delete after 30 days)
      scene_1_bg.mp4
      scene_2_bg.mp4
      scene_3_bg.mp4
      scene_4_bg.mp4
      music.mp3
    final_video.mp4     # Final output (delete after 90 days)
```

**Draft Files (delete after 30 days):**
- `scene_N_bg.mp4` - Generated background videos (before compositing)
- `music.mp3` - Generated background music
- Format: MP4 (H.264), MP3
- Size: ~5-10MB per scene, ~2-5MB for music
- Lifecycle: **DELETE AFTER 30 DAYS**

**Final Files (delete after 90 days):**
- `final_video.mp4` - Final composited video (with product + text + music)
- Format: MP4 (H.264, 1080x1920, 30fps)
- Size: ~15-30MB per video
- Lifecycle: **DELETE AFTER 90 DAYS**

**S3 Tags:**
```json
{
  "type": "campaign_video",
  "subtype": "draft|final",
  "brand_id": "xxx",
  "perfume_id": "xxx",
  "campaign_id": "xxx",
  "variation_index": "0|1|2",
  "lifecycle": "30days|90days"
}
```

---

### S3 Lifecycle Policy (Updated)

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
      "Expiration": {"Days": 30},
      "NoncurrentVersionExpiration": {"NoncurrentDays": 1}
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
      "Expiration": {"Days": 90},
      "NoncurrentVersionExpiration": {"NoncurrentDays": 1}
    }
  ]
}
```

---

### Storage Utility Functions (Updated)

#### Current (Old):
```python
def get_project_s3_path(project_id: str) -> str:
    return f"projects/{project_id}/"

def upload_product_image(project_id: str, file) -> str:
    path = f"projects/{project_id}/product/original.jpg"
    s3.upload(path, file)
    return path
```

#### New:
```python
def get_brand_s3_path(brand_id: str) -> str:
    return f"brands/{brand_id}/"

def get_perfume_s3_path(brand_id: str, perfume_id: str) -> str:
    return f"brands/{brand_id}/perfumes/{perfume_id}/"

def get_campaign_s3_path(brand_id: str, perfume_id: str, campaign_id: str) -> str:
    return f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"

def upload_brand_logo(brand_id: str, file) -> str:
    path = f"brands/{brand_id}/brand_logo.png"
    s3.upload(path, file, tags={"type": "brand_asset", "lifecycle": "permanent"})
    return path

def upload_brand_guidelines(brand_id: str, file) -> str:
    path = f"brands/{brand_id}/brand_guidelines.pdf"
    s3.upload(path, file, tags={"type": "brand_asset", "lifecycle": "permanent"})
    return path

def upload_perfume_image(brand_id: str, perfume_id: str, angle: str, file) -> str:
    path = f"brands/{brand_id}/perfumes/{perfume_id}/{angle}.png"
    s3.upload(path, file, tags={
        "type": "perfume_image",
        "brand_id": brand_id,
        "perfume_id": perfume_id,
        "angle": angle,
        "lifecycle": "permanent"
    })
    return path

def upload_draft_video(brand_id: str, perfume_id: str, campaign_id: str, 
                       variation_index: int, scene_index: int, file) -> str:
    path = f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/variations/variation_{variation_index}/draft/scene_{scene_index}_bg.mp4"
    s3.upload(path, file, tags={
        "type": "campaign_video",
        "subtype": "draft",
        "brand_id": brand_id,
        "perfume_id": perfume_id,
        "campaign_id": campaign_id,
        "variation_index": str(variation_index),
        "lifecycle": "30days"
    })
    return path

def upload_final_video(brand_id: str, perfume_id: str, campaign_id: str, 
                       variation_index: int, file) -> str:
    path = f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/variations/variation_{variation_index}/final_video.mp4"
    s3.upload(path, file, tags={
        "type": "campaign_video",
        "subtype": "final",
        "brand_id": brand_id,
        "perfume_id": perfume_id,
        "campaign_id": campaign_id,
        "variation_index": str(variation_index),
        "lifecycle": "90days"
    })
    return path
```

---

## API Architecture

### RESTful API Structure (NEW)

#### Before (Current):
```
POST   /api/projects              # Create project
GET    /api/projects              # List ALL projects (no isolation)
GET    /api/projects/:id          # Get project
POST   /api/generation/...        # Generate
```

#### After (New):
```
# Brand Management
POST   /api/brands/onboard                    # Onboard brand
GET    /api/brands/me                         # Get current brand
GET    /api/brands/me/stats                   # Brand stats

# Perfume Management
POST   /api/perfumes                          # Create perfume
GET    /api/perfumes                          # List brand's perfumes
GET    /api/perfumes/:perfumeId               # Get perfume
PUT    /api/perfumes/:perfumeId               # Update perfume (future)
DELETE /api/perfumes/:perfumeId               # Delete perfume

# Campaign Management
POST   /api/campaigns                         # Create campaign
GET    /api/campaigns?perfume_id=xxx          # List perfume's campaigns
GET    /api/campaigns/:campaignId             # Get campaign
DELETE /api/campaigns/:campaignId             # Delete campaign

# Generation (same as current)
POST   /api/generation/campaigns/:id/generate
GET    /api/generation/campaigns/:id/progress
POST   /api/generation/campaigns/:id/select-variation
```

### API Endpoints (Detailed)

#### 1. Brand Endpoints (NEW)

##### POST `/api/brands/onboard`

**Purpose:** Complete brand onboarding (one-time setup)

**Request:**
```typescript
// Multipart form data
{
  brand_name: string;           // Required, 2-100 chars
  logo: File;                   // Required, PNG/JPG/WebP, max 5MB
  guidelines: File;             // Required, PDF/DOCX, max 10MB
}
```

**Response (201 Created):**
```typescript
{
  brand_id: string;
  brand_name: string;
  brand_logo_url: string;       // S3 URL
  brand_guidelines_url: string; // S3 URL
  onboarding_completed: true;
  created_at: string;
}
```

**Errors:**
- 400 Bad Request - Invalid file format or size
- 409 Conflict - Brand name already taken
- 422 Unprocessable Entity - Validation failed

---

##### GET `/api/brands/me`

**Purpose:** Get current user's brand

**Response (200 OK):**
```typescript
{
  brand_id: string;
  brand_name: string;
  brand_logo_url: string;
  brand_guidelines_url: string;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}
```

**Errors:**
- 404 Not Found - User has no brand (not onboarded)

---

##### GET `/api/brands/me/stats`

**Purpose:** Get brand statistics

**Response (200 OK):**
```typescript
{
  total_perfumes: number;
  total_campaigns: number;
  total_cost: number;           // Sum of all campaign costs
  completed_campaigns: number;
  processing_campaigns: number;
  failed_campaigns: number;
}
```

---

#### 2. Perfume Endpoints (NEW)

##### POST `/api/perfumes`

**Purpose:** Create new perfume

**Request:**
```typescript
// Multipart form data
{
  perfume_name: string;         // Required, 2-200 chars
  perfume_gender: 'masculine' | 'feminine' | 'unisex';  // Required
  front_image: File;            // Required, PNG/JPG/WebP, max 5MB
  back_image?: File;            // Optional
  top_image?: File;             // Optional
  left_image?: File;            // Optional
  right_image?: File;           // Optional
}
```

**Response (201 Created):**
```typescript
{
  perfume_id: string;
  brand_id: string;
  perfume_name: string;
  perfume_gender: string;
  front_image_url: string;
  back_image_url?: string;
  top_image_url?: string;
  left_image_url?: string;
  right_image_url?: string;
  images_count: number;         // 1-5
  created_at: string;
}
```

**Errors:**
- 400 Bad Request - Invalid file format or size
- 409 Conflict - Perfume name already exists within brand
- 422 Unprocessable Entity - Missing front image

---

##### GET `/api/perfumes`

**Purpose:** List all perfumes for current brand

**Query Parameters:**
```typescript
{
  page?: number;                // Default: 1
  limit?: number;               // Default: 20, max: 100
  gender?: 'masculine' | 'feminine' | 'unisex';  // Filter by gender
  sort?: 'created_at' | 'name'; // Sort field
  order?: 'asc' | 'desc';       // Sort order
}
```

**Response (200 OK):**
```typescript
{
  perfumes: [
    {
      perfume_id: string;
      perfume_name: string;
      perfume_gender: string;
      front_image_url: string;
      images_count: number;
      campaigns_count: number;  // Computed from campaigns table
      created_at: string;
    }
  ],
  total: number;
  page: number;
  limit: number;
  pages: number;
}
```

---

##### GET `/api/perfumes/:perfumeId`

**Purpose:** Get perfume details

**Response (200 OK):**
```typescript
{
  perfume_id: string;
  brand_id: string;
  perfume_name: string;
  perfume_gender: string;
  front_image_url: string;
  back_image_url?: string;
  top_image_url?: string;
  left_image_url?: string;
  right_image_url?: string;
  images_count: number;
  campaigns_count: number;
  created_at: string;
  updated_at: string;
}
```

**Errors:**
- 404 Not Found - Perfume not found or not owned by current brand

---

##### DELETE `/api/perfumes/:perfumeId`

**Purpose:** Delete perfume

**Response (204 No Content):**

**Errors:**
- 404 Not Found - Perfume not found
- 409 Conflict - Cannot delete perfume with existing campaigns
- 403 Forbidden - Perfume not owned by current brand

---

#### 3. Campaign Endpoints (UPDATED)

##### POST `/api/campaigns`

**Purpose:** Create new campaign

**Request:**
```typescript
{
  perfume_id: string;           // Required, FK to perfumes
  campaign_name: string;        // Required, 2-200 chars
  creative_prompt: string;      // Required, 10-2000 chars
  selected_style: 'gold_luxe' | 'dark_elegance' | 'romantic_floral';  // Required
  target_duration: number;      // Required, 15-60
  num_variations: 1 | 2 | 3;    // Default: 1
}
```

**Note:** `brand_id` is inferred from authenticated user

**Response (201 Created):**
```typescript
{
  campaign_id: string;
  perfume_id: string;
  brand_id: string;
  campaign_name: string;
  status: 'pending';
  progress: 0;
  created_at: string;
}
```

**Errors:**
- 400 Bad Request - Invalid request body
- 404 Not Found - Perfume not found
- 409 Conflict - Campaign name already exists for this perfume
- 422 Unprocessable Entity - Validation failed

---

##### GET `/api/campaigns`

**Purpose:** List campaigns (filtered by perfume)

**Query Parameters:**
```typescript
{
  perfume_id?: string;          // Filter by perfume (required in practice)
  page?: number;                // Default: 1
  limit?: number;               // Default: 20, max: 100
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  sort?: 'created_at' | 'cost'; // Sort field
  order?: 'asc' | 'desc';       // Sort order
}
```

**Response (200 OK):**
```typescript
{
  campaigns: [
    {
      campaign_id: string;
      perfume_id: string;
      brand_id: string;
      campaign_name: string;
      status: string;
      progress: number;
      cost: number;
      target_duration: number;
      num_variations: number;
      selected_variation_index?: number;
      created_at: string;
    }
  ],
  total: number;
  page: number;
  limit: number;
  pages: number;
}
```

---

##### GET `/api/campaigns/:campaignId`

**Purpose:** Get campaign details

**Response (200 OK):**
```typescript
{
  campaign_id: string;
  perfume_id: string;
  brand_id: string;
  campaign_name: string;
  creative_prompt: string;
  selected_style: string;
  target_duration: number;
  num_variations: number;
  selected_variation_index?: number;
  status: string;
  progress: number;
  cost: number;
  error_message?: string;
  campaign_json: {
    scenes: Scene[];
    styleSpec: StyleSpec;
    videoMetadata: VideoMetadata;
    costBreakdown: CostBreakdown;
    variationPaths: VariationPaths;
  };
  created_at: string;
  updated_at: string;
}
```

**Errors:**
- 404 Not Found - Campaign not found or not owned by current brand

---

##### DELETE `/api/campaigns/:campaignId`

**Purpose:** Delete campaign

**Response (204 No Content):**

**Errors:**
- 404 Not Found - Campaign not found
- 409 Conflict - Cannot delete campaign with status 'processing'
- 403 Forbidden - Campaign not owned by current brand

---

### Authentication & Authorization

#### Current (Old):
```python
# No isolation, anyone can access any project
@router.get("/api/projects")
async def list_projects(user_id: str = Depends(get_current_user)):
    return crud.get_all_projects()  # Returns ALL projects
```

#### New:
```python
# Brand isolation enforced at API level
@router.get("/api/perfumes")
async def list_perfumes(
    brand_id: str = Depends(get_current_brand_id)
):
    return crud.get_perfumes_by_brand(brand_id)  # Only current brand's perfumes

@router.get("/api/campaigns")
async def list_campaigns(
    perfume_id: str,
    brand_id: str = Depends(get_current_brand_id)
):
    # Verify perfume belongs to current brand
    perfume = crud.get_perfume(perfume_id)
    if perfume.brand_id != brand_id:
        raise HTTPException(403, "Forbidden")
    
    return crud.get_campaigns_by_perfume(perfume_id)
```

**Key Changes:**
1. All endpoints check brand ownership
2. `get_current_brand_id()` dependency extracts brand_id from auth user
3. Cross-brand access blocked at API level
4. Foreign key constraints prevent orphaned data

---

### Dependency Functions (NEW)

```python
# app/api/auth.py (UPDATED)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Extract user_id from JWT token (Supabase)"""
    # ... existing logic ...
    return user_id

async def get_current_brand_id(user_id: str = Depends(get_current_user)) -> str:
    """Get brand_id for current user"""
    brand = await crud.get_brand_by_user_id(user_id)
    if not brand:
        raise HTTPException(404, "Brand not found. Please complete onboarding.")
    return brand.brand_id

async def verify_onboarding(user_id: str = Depends(get_current_user)) -> bool:
    """Check if user has completed onboarding"""
    brand = await crud.get_brand_by_user_id(user_id)
    if not brand or not brand.onboarding_completed:
        raise HTTPException(403, "Onboarding not completed")
    return True

async def verify_perfume_ownership(
    perfume_id: str,
    brand_id: str = Depends(get_current_brand_id)
) -> Perfume:
    """Verify perfume belongs to current brand"""
    perfume = await crud.get_perfume(perfume_id)
    if not perfume or perfume.brand_id != brand_id:
        raise HTTPException(404, "Perfume not found")
    return perfume

async def verify_campaign_ownership(
    campaign_id: str,
    brand_id: str = Depends(get_current_brand_id)
) -> Campaign:
    """Verify campaign belongs to current brand"""
    campaign = await crud.get_campaign(campaign_id)
    if not campaign or campaign.brand_id != brand_id:
        raise HTTPException(404, "Campaign not found")
    return campaign
```

---

## Backend Service Updates

### Services That Need NO Changes (Keep As-Is)

✅ **Scene Planner** (`scene_planner.py`)
- Perfume shot grammar logic
- LLM scene generation
- Style spec creation
- NO CHANGES

✅ **Video Generator** (`video_generator.py`)
- Wān model integration
- Batch generation
- Multi-variation support
- NO CHANGES

✅ **Compositor** (`compositor.py`)
- Product overlay
- Frame-by-frame blending
- NO CHANGES

✅ **Text Overlay** (`text_overlay.py`)
- FFmpeg text rendering
- Luxury fonts
- NO CHANGES

✅ **Audio Engine** (`audio_engine.py`)
- MusicGen integration
- Gender-aware prompts
- NO CHANGES

✅ **Renderer** (`renderer.py`)
- Video concatenation
- Audio-video muxing
- NO CHANGES

✅ **Perfume Grammar Loader** (`perfume_grammar_loader.py`)
- Grammar validation
- NO CHANGES

---

### Services That Need UPDATES

#### 1. Product Extractor (MINOR UPDATE)

**Current:**
```python
async def extract_product(project_id: str, image_url: str) -> str:
    # Download image
    # Remove background with rembg
    # Upload to S3: projects/{project_id}/product/masked.png
```

**New:**
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
        return perfume.front_image_url  # Fallback

async def extract_perfume_for_campaign(campaign: Campaign, perfume: Perfume) -> str:
    """Extract product from perfume images"""
    # Use front image for extraction
    image_url = perfume.front_image_url
    
    # Download image
    # Remove background with rembg
    # Upload to campaign temp folder (local /tmp)
    # Return local path (no S3 upload for extracted product)
```

**Changes:**
- Read perfume images from perfumes table
- Fallback to front image if other angles missing
- Extract product to local /tmp (not S3)

---

#### 2. Brand Guidelines Extractor (UPDATE)

**Current:**
```python
async def extract_brand_guidelines(guidelines_url: str) -> dict:
    # Called per campaign
    # Extracts from ad_project_json.brandGuidelinesUrl
```

**New:**
```python
async def extract_brand_guidelines_from_brand(brand: Brand) -> dict:
    """Extract brand guidelines (called once, cached)"""
    # Download from S3: brand.brand_guidelines_url
    # Parse PDF/DOCX
    # Extract colors, tone, dos/donts with GPT-4o-mini
    # Return structured style data
    
    return {
        "colors": ["#...", "#..."],
        "tone": "elegant, sophisticated",
        "dos": ["Use soft lighting", "Show luxury materials"],
        "donts": ["Avoid harsh colors", "No cluttered backgrounds"]
    }

# Cache extracted guidelines per brand (Redis or in-memory)
@lru_cache(maxsize=100)
async def get_brand_style(brand_id: str) -> dict:
    brand = await crud.get_brand(brand_id)
    return await extract_brand_guidelines_from_brand(brand)
```

**Changes:**
- Extract guidelines from brand table (not per campaign)
- Cache extracted style per brand (performance optimization)
- Called once during campaign generation

---

#### 3. Generation Pipeline (MAJOR UPDATE)

**Current:**
```python
async def run(project_id: str):
    # Load project from database
    project = crud.get_project(project_id)
    
    # STEP 0: Extract reference image (REMOVE THIS)
    # STEP 1: Extract brand guidelines (UPDATE THIS)
    # STEP 2: Plan scenes
    # STEP 3: Extract product
    # STEP 4: Generate videos
    # ... rest of pipeline ...
```

**New:**
```python
async def run(campaign_id: str):
    # Load campaign + perfume + brand from database
    campaign = await crud.get_campaign(campaign_id)
    perfume = await crud.get_perfume(campaign.perfume_id)
    brand = await crud.get_brand(campaign.brand_id)
    
    # STEP 0: REMOVED (no reference image)
    
    # STEP 1: Extract brand guidelines (UPDATED)
    brand_style = await get_brand_style(brand.brand_id)  # Cached
    
    # STEP 2: Plan scenes (UPDATED)
    scenes = await scene_planner.plan_scenes(
        creative_prompt=campaign.creative_prompt,
        brand_name=brand.brand_name,
        perfume_name=perfume.perfume_name,
        perfume_gender=perfume.perfume_gender,
        selected_style=campaign.selected_style,
        duration=campaign.target_duration,
        brand_style=brand_style,  # From brand guidelines
        num_variations=campaign.num_variations
    )
    
    # STEP 3: Extract perfume product (UPDATED)
    product_mask = await product_extractor.extract_perfume_for_campaign(
        campaign, perfume
    )
    
    # STEP 4: Generate videos (SAME)
    for variation_index in range(campaign.num_variations):
        scene_videos = await video_generator.generate_scene_videos_batch(
            scenes[variation_index],
            style_spec,
            variation_index
        )
        
        # Upload to S3 with new paths
        for scene_index, video in enumerate(scene_videos):
            s3_path = upload_draft_video(
                brand.brand_id,
                perfume.perfume_id,
                campaign.campaign_id,
                variation_index,
                scene_index,
                video
            )
    
    # ... rest of pipeline (compositing, text, audio, rendering) ...
    
    # STEP 8: Upload final videos (UPDATED)
    for variation_index in range(campaign.num_variations):
        final_video_path = upload_final_video(
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
            "variationPaths": variation_paths
        }
    })
```

**Key Changes:**
1. Load campaign + perfume + brand (3 DB calls)
2. Remove reference image extraction
3. Use brand guidelines from brand table
4. Use perfume images from perfumes table
5. Update S3 paths to new hierarchy
6. Store results in campaign_json

---

## Frontend Architecture

### Component Structure (NEW)

```
pages/
  Landing.tsx                    # Public landing page
  Login.tsx                      # Login page
  Signup.tsx                     # Signup page
  Onboarding.tsx                 # Brand onboarding (NEW, mandatory)
  Dashboard.tsx                  # Main dashboard (perfume list) (UPDATED)
  AddPerfume.tsx                 # Add perfume form (NEW)
  CampaignDashboard.tsx          # Campaign list per perfume (NEW)
  CreateCampaign.tsx             # Create campaign form (UPDATED)
  GenerationProgress.tsx         # Real-time progress (SAME)
  VideoSelection.tsx             # Variation selection (SAME)
  CampaignResults.tsx            # Campaign results (UPDATED)

components/
  OnboardingForm.tsx             # Brand setup form (NEW)
  PerfumeCard.tsx                # Perfume card component (NEW)
  AddPerfumeModal.tsx            # Add perfume modal (NEW)
  CampaignCard.tsx               # Campaign card component (NEW)
  CreateCampaignForm.tsx         # Campaign form (UPDATED)
  ProtectedRoute.tsx             # Auth guard (UPDATED with onboarding check)
```

### Routing (UPDATED)

```typescript
// src/App.tsx

<Routes>
  {/* Public Routes */}
  <Route path="/" element={<Landing />} />
  <Route path="/login" element={<Login />} />
  <Route path="/signup" element={<Signup />} />
  
  {/* Onboarding Route (protected, but no onboarding check) */}
  <Route path="/onboarding" element={
    <ProtectedRoute skipOnboardingCheck>
      <Onboarding />
    </ProtectedRoute>
  } />
  
  {/* Protected Routes (require onboarding) */}
  <Route path="/dashboard" element={
    <ProtectedRoute>
      <Dashboard />  {/* Perfume list */}
    </ProtectedRoute>
  } />
  
  <Route path="/perfumes/add" element={
    <ProtectedRoute>
      <AddPerfume />
    </ProtectedRoute>
  } />
  
  <Route path="/perfumes/:perfumeId" element={
    <ProtectedRoute>
      <CampaignDashboard />  {/* Campaign list per perfume */}
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

### Protected Route (UPDATED)

```typescript
// src/components/ProtectedRoute.tsx

interface ProtectedRouteProps {
  children: React.ReactNode;
  skipOnboardingCheck?: boolean;  // Allow access to onboarding page
}

export function ProtectedRoute({ children, skipOnboardingCheck }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const { brand, loading: brandLoading } = useBrand();
  const navigate = useNavigate();
  
  useEffect(() => {
    if (loading || brandLoading) return;
    
    // Check authentication
    if (!user) {
      navigate('/login');
      return;
    }
    
    // Check onboarding (unless skipped)
    if (!skipOnboardingCheck && (!brand || !brand.onboarding_completed)) {
      navigate('/onboarding');
      return;
    }
  }, [user, brand, loading, brandLoading, skipOnboardingCheck]);
  
  if (loading || brandLoading) {
    return <LoadingSpinner />;
  }
  
  if (!user) {
    return null;
  }
  
  if (!skipOnboardingCheck && (!brand || !brand.onboarding_completed)) {
    return null;
  }
  
  return <>{children}</>;
}
```

---

## Data Flow (End-to-End)

### Flow 1: Onboarding

```
1. User signs up (Supabase Auth)
   ↓
2. User lands on /onboarding page
   ↓
3. User fills brand form (name, logo, guidelines)
   ↓
4. Frontend: POST /api/brands/onboard
   - Upload logo to S3: brands/{brand_id}/brand_logo.png
   - Upload guidelines to S3: brands/{brand_id}/brand_guidelines.pdf
   - Create brand record in DB
   - Set onboarding_completed = true
   ↓
5. Backend returns brand_id
   ↓
6. Frontend redirects to /dashboard
```

---

### Flow 2: Add Perfume

```
1. User clicks "+ Add Perfume" on dashboard
   ↓
2. Modal opens with perfume form
   ↓
3. User fills form (name, gender, images)
   ↓
4. Frontend: POST /api/perfumes
   - Upload images to S3:
     brands/{brand_id}/perfumes/{perfume_id}/front.png
     brands/{brand_id}/perfumes/{perfume_id}/back.png (if provided)
     ...
   - Create perfume record in DB
   ↓
5. Backend returns perfume_id
   ↓
6. Frontend closes modal, refreshes dashboard
```

---

### Flow 3: Create Campaign

```
1. User clicks "+ Create Campaign" on campaign dashboard
   ↓
2. Form opens with campaign fields
   ↓
3. User fills form (name, prompt, style, duration, variations)
   ↓
4. Frontend: POST /api/campaigns
   - Create campaign record (status: pending)
   - brand_id inferred from auth user
   - perfume_id from URL params
   ↓
5. Backend returns campaign_id
   ↓
6. Frontend: POST /api/generation/campaigns/:id/generate
   - Enqueue generation job in RQ
   ↓
7. Backend starts generation pipeline:
   
   a. Load campaign + perfume + brand from DB
   
   b. Extract brand guidelines (cached)
      - Download from S3: brand.brand_guidelines_url
      - Parse with GPT-4o-mini
      - Return colors, tone, dos/donts
   
   c. Plan scenes (for N variations)
      - Use brand_style + creative_prompt + selected_style + perfume_gender
      - Generate scene plans with perfume shot grammar
   
   d. Extract perfume product
      - Download perfume.front_image_url
      - Remove background with rembg
      - Save to /tmp (local temp)
   
   e. Generate videos (parallel for N variations)
      - For each variation:
        - Generate 4 scene background videos
        - Upload to S3:
          brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/
          variations/variation_N/draft/scene_1_bg.mp4
          (repeat for scene_2_bg.mp4, scene_3_bg.mp4, scene_4_bg.mp4)
   
   f. Composite perfume onto videos
      - Overlay product mask onto each scene
      - Save composited videos to /tmp
   
   g. Add text overlays
      - Use luxury fonts
      - Render text with FFmpeg
   
   h. Generate music
      - Use perfume_gender for mood
      - Upload to S3:
        brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/
        variations/variation_N/draft/music.mp3
   
   i. Render final videos
      - Concatenate scenes + mux audio
      - Upload to S3:
        brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/
        variations/variation_N/final_video.mp4
   
   j. Update campaign record
      - Set status = 'completed'
      - Set progress = 100
      - Store all S3 paths in campaign_json.variationPaths
   ↓
8. Frontend polls GET /api/generation/campaigns/:id/progress
   - Shows real-time progress (0-100%)
   ↓
9. When complete:
   - If num_variations > 1: Navigate to /campaigns/:id/select
   - If num_variations = 1: Navigate to /campaigns/:id/results
```

---

## Performance Considerations

### Database Query Optimization

**Indexes (Already Defined):**
```sql
-- Brand lookups
CREATE INDEX idx_brands_user_id ON brands(user_id);

-- Perfume lookups
CREATE INDEX idx_perfumes_brand_id ON perfumes(brand_id);

-- Campaign lookups
CREATE INDEX idx_campaigns_perfume_id ON campaigns(perfume_id);
CREATE INDEX idx_campaigns_brand_id ON campaigns(brand_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_created_at ON campaigns(created_at DESC);
```

**Query Patterns:**
```sql
-- Get brand for user (1:1 lookup)
SELECT * FROM brands WHERE user_id = ?;  -- Uses idx_brands_user_id

-- Get perfumes for brand (1:N lookup)
SELECT * FROM perfumes WHERE brand_id = ? ORDER BY created_at DESC;  -- Uses idx_perfumes_brand_id

-- Get campaigns for perfume (1:N lookup)
SELECT * FROM campaigns WHERE perfume_id = ? ORDER BY created_at DESC;  -- Uses idx_campaigns_perfume_id

-- Get campaigns for brand (1:N lookup, denormalized)
SELECT * FROM campaigns WHERE brand_id = ? ORDER BY created_at DESC;  -- Uses idx_campaigns_brand_id
```

**Performance:**
- All queries use indexes (no full table scans)
- Foreign keys enforce referential integrity
- Denormalized brand_id in campaigns for quick brand-level queries

---

### Caching Strategy

**Brand Guidelines Extraction:**
```python
# Cache extracted brand guidelines per brand (expensive operation)
@lru_cache(maxsize=100)
async def get_brand_style(brand_id: str) -> dict:
    brand = await crud.get_brand(brand_id)
    guidelines = await extract_brand_guidelines_from_brand(brand)
    return guidelines

# TTL: 24 hours (or until brand guidelines updated)
# Invalidate cache when brand updates guidelines
```

**Perfume Images:**
```python
# Cache perfume image URLs (frequent access during generation)
@lru_cache(maxsize=500)
async def get_perfume_images(perfume_id: str) -> dict:
    perfume = await crud.get_perfume(perfume_id)
    return {
        "front": perfume.front_image_url,
        "back": perfume.back_image_url,
        "top": perfume.top_image_url,
        "left": perfume.left_image_url,
        "right": perfume.right_image_url,
    }
```

---

### S3 Performance

**Parallel Uploads:**
```python
# Upload all draft videos in parallel
async def upload_draft_videos_parallel(videos: list):
    tasks = [
        upload_draft_video(brand_id, perfume_id, campaign_id, var_idx, scene_idx, video)
        for var_idx, scenes in enumerate(videos)
        for scene_idx, video in enumerate(scenes)
    ]
    return await asyncio.gather(*tasks)
```

**Presigned URLs:**
```python
# Generate presigned URL for final video download (avoid proxying through API)
def get_presigned_url(s3_path: str, expiration: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_path},
        ExpiresIn=expiration
    )
```

---

## Migration Plan

### Step 1: Database Migration

```sql
-- Drop old table (data loss confirmed by user)
DROP TABLE IF EXISTS projects CASCADE;

-- Create new tables
CREATE TABLE brands (...);
CREATE TABLE perfumes (...);
CREATE TABLE campaigns (...);

-- Create indexes
CREATE INDEX ...;

-- Create foreign keys
ALTER TABLE ...;
```

### Step 2: Backend Migration

1. Update database models (SQLAlchemy)
2. Update Pydantic schemas
3. Update CRUD operations
4. Update API endpoints
5. Update storage utility functions
6. Update generation pipeline
7. Remove reference image extractor
8. Test all endpoints

### Step 3: Frontend Migration

1. Update TypeScript types
2. Create new pages (Onboarding, AddPerfume, CampaignDashboard)
3. Update existing pages (Dashboard, CreateCampaign, CampaignResults)
4. Update routing
5. Update API service layer
6. Update ProtectedRoute with onboarding check
7. Test all flows

### Step 4: S3 Migration

1. Update S3 utility functions
2. Update S3 lifecycle policies
3. Test upload/download
4. Test lifecycle policies (manual verification)

### Step 5: Integration Testing

1. End-to-end onboarding flow
2. End-to-end perfume creation flow
3. End-to-end campaign creation flow
4. Brand isolation testing (no cross-brand access)
5. S3 storage verification (correct paths)
6. Cascade delete testing

---

## Security Considerations

### Brand Isolation

**Enforcement Points:**
1. **API Layer:** All endpoints check brand ownership
2. **Database Layer:** Foreign keys prevent orphaned data
3. **S3 Layer:** Pre-signed URLs scoped to brand folder

**Isolation Tests:**
```python
# Test: User A cannot access User B's perfumes
async def test_brand_isolation():
    user_a = create_user("userA")
    user_b = create_user("userB")
    
    brand_a = create_brand(user_a)
    brand_b = create_brand(user_b)
    
    perfume_a = create_perfume(brand_a)
    perfume_b = create_perfume(brand_b)
    
    # User A tries to access User B's perfume
    response = await client.get(
        f"/api/perfumes/{perfume_b.perfume_id}",
        headers={"Authorization": f"Bearer {user_a.token}"}
    )
    
    assert response.status_code == 404  # Not found (not 403 to avoid info leak)
```

---

### S3 Security

**Bucket Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAccessToOtherBrands",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::genads-videos/brands/*",
      "Condition": {
        "StringNotLike": {
          "s3:prefix": "brands/${aws:userid}/*"
        }
      }
    }
  ]
}
```

**Presigned URL Security:**
- Expiration: 1 hour (3600 seconds)
- Scope: Single file only (not directory)
- No list permissions

---

## Monitoring & Observability

### Key Metrics

**Database Metrics:**
- Brand count
- Perfume count per brand
- Campaign count per perfume
- Average campaigns per brand
- Storage usage per brand

**API Metrics:**
- Request rate per endpoint
- Error rate per endpoint
- Response time per endpoint
- Auth failure rate

**Generation Metrics:**
- Generation success rate
- Average generation time
- Average cost per campaign
- S3 upload success rate

**Business Metrics:**
- New brand signups per day
- Onboarding completion rate
- Perfumes created per brand
- Campaigns created per perfume
- Total cost spent per brand

---

## Rollback Strategy

### If Issues Discovered

**Database Rollback:**
```sql
-- Revert to old schema
DROP TABLE campaigns CASCADE;
DROP TABLE perfumes CASCADE;
DROP TABLE brands CASCADE;

CREATE TABLE projects (...);  -- Old schema
```

**Code Rollback:**
- Keep old code in separate branch
- Git revert to previous commit
- Redeploy old version

**S3 Rollback:**
- Old paths still accessible
- Lifecycle policies can be updated
- No data loss (files remain)

---

**Status:** Design Complete  
**Next:** Review Task List  
**Last Updated:** November 18, 2025

