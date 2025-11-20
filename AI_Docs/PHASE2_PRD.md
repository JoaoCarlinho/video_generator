# B2B SaaS Overhaul - Product Requirements Document

**Version:** 1.0  
**Created:** November 18, 2025  
**Status:** Planning Phase  
**Estimated Timeline:** 3-4 weeks (120-160 hours)

---

## Executive Summary

GenAds is transforming from a shared multi-user platform to a **B2B SaaS model** where each perfume brand has their own isolated account with brand-specific assets and campaigns. This architectural overhaul introduces a 3-tier hierarchy: **Brand → Perfumes → Campaigns**.

### Key Changes

**FROM (Current):**
- All users share the same project pool
- Brand info entered per campaign
- No product (perfume) persistence
- Flat project structure

**TO (New):**
- Each brand has isolated account
- One-time brand onboarding
- Perfume library per brand
- Campaign organized under perfumes
- S3 storage reflects brand hierarchy

---

## Product Vision

### The New GenAds

**GenAds becomes a white-label ad generation platform for perfume brands**, where each brand manages:
1. **Brand Identity** (logo, guidelines) - Set once
2. **Perfume Portfolio** (products with multi-angle images)
3. **Ad Campaigns** (TikTok ads per perfume)

### User Persona: Perfume Brand Marketing Manager

**Meet Sarah - Marketing Manager at "Noir Élégance" perfume brand:**
- Manages 5-10 perfume SKUs
- Needs to create TikTok ads for each perfume
- Wants brand consistency across all campaigns
- Creates 2-4 ad variations per perfume monthly
- Budget-conscious, wants cost-effective production

**Sarah's Pain Points (Current System):**
- ❌ Re-enters brand name every campaign
- ❌ Re-uploads brand guidelines every time
- ❌ Can't organize campaigns by perfume
- ❌ Sees other brands' projects (privacy concern)
- ❌ No way to manage perfume catalog

**Sarah's Gains (New System):**
- ✅ Sets brand identity once during onboarding
- ✅ Builds perfume library with images
- ✅ All campaigns auto-use brand guidelines
- ✅ Organized by perfume (easy to find campaigns)
- ✅ Fully isolated brand account

---

## Core Requirements

### 1. Authentication & Brand Model

#### 1.1 User-Brand Relationship
- **1 User = 1 Brand** (1:1 mapping)
- User signs up → Creates brand account
- No multi-user teams in MVP
- User ID = Brand ID conceptually

#### 1.2 Onboarding Flow (MANDATORY)

**New User Journey:**
```
Step 1: Sign up (email + password via Supabase)
  ↓
Step 2: Onboarding Form (CANNOT SKIP)
  - Brand Name (required, text input, max 100 chars)
  - Brand Logo (required, PNG/JPG, max 5MB)
  - Brand Guidelines (required, PDF/DOCX, max 10MB)
  ↓
Step 3: Save to database + S3
  - Set onboarding_completed = true
  ↓
Step 4: Redirect to Main Dashboard
```

**Database Flag:**
- `brands.onboarding_completed` (boolean, default: false)
- If `false` → Redirect to onboarding page
- If `true` → Allow access to dashboard

**Future Enhancement (Post-MVP):**
- Settings page to update brand name/logo/guidelines
- For MVP: Onboarding is one-time only

---

### 2. Brand Management

#### 2.1 Brand Entity

**Fields:**
- `brand_id` (UUID, primary key)
- `user_id` (UUID, foreign key to auth.users, unique)
- `brand_name` (String, max 100 chars)
- `brand_logo_url` (String, S3 path)
- `brand_guidelines_url` (String, S3 path)
- `onboarding_completed` (Boolean, default: false)
- `created_at` (Timestamp)
- `updated_at` (Timestamp)

**S3 Storage:**
```
s3://bucket/brands/{brand_id}/
  ├── brand_logo.png
  └── brand_guidelines.pdf
```

**Business Rules:**
- Brand name must be unique (index + validation)
- Logo formats: PNG, JPG, WebP (max 5MB)
- Guidelines formats: PDF, DOCX (max 10MB)
- Cannot delete brand if perfumes exist

---

### 3. Perfume Management

#### 3.1 Perfume Entity

**Fields:**
- `perfume_id` (UUID, primary key)
- `brand_id` (UUID, foreign key, indexed)
- `perfume_name` (String, max 200 chars)
- `perfume_gender` (Enum: 'masculine', 'feminine', 'unisex')
- `front_image_url` (String, S3 path, REQUIRED)
- `back_image_url` (String, S3 path, OPTIONAL)
- `top_image_url` (String, S3 path, OPTIONAL)
- `left_image_url` (String, S3 path, OPTIONAL)
- `right_image_url` (String, S3 path, OPTIONAL)
- `created_at` (Timestamp)
- `updated_at` (Timestamp)

**S3 Storage:**
```
s3://bucket/brands/{brand_id}/perfumes/{perfume_id}/
  ├── front.png          (REQUIRED)
  ├── back.png           (optional)
  ├── top.png            (optional)
  ├── left.png           (optional)
  └── right.png          (optional)
```

**Business Rules:**
- Perfume name must be unique within brand
- Front image is REQUIRED
- Back/top/left/right are OPTIONAL
- If optional images not provided:
  - Use `front.png` as fallback for all angles
  - Show warning: "Only front image provided"
- Image formats: PNG, JPG, WebP (max 5MB each)
- Cannot delete perfume if campaigns exist

#### 3.2 Perfume Images - Fallback Logic

**Scenario: User only uploads front image**
```python
def get_perfume_image(perfume, angle):
    if angle == "front":
        return perfume.front_image_url  # Always exists
    elif angle == "back" and perfume.back_image_url:
        return perfume.back_image_url
    elif angle == "top" and perfume.top_image_url:
        return perfume.top_image_url
    elif angle == "left" and perfume.left_image_url:
        return perfume.left_image_url
    elif angle == "right" and perfume.right_image_url:
        return perfume.right_image_url
    else:
        return perfume.front_image_url  # Fallback to front
```

---

### 4. Campaign Management

#### 4.1 Campaign Entity

**Fields (New):**
- `campaign_id` (UUID, primary key)
- `perfume_id` (UUID, foreign key, indexed)
- `brand_id` (UUID, foreign key, indexed) - For quick brand-level queries
- `campaign_name` (String, max 200 chars)
- `creative_prompt` (Text, max 2000 chars)
- `selected_style` (Enum: 'gold_luxe', 'dark_elegance', 'romantic_floral')
- `target_duration` (Integer, 15-60 seconds)
- `num_variations` (Integer, 1-3, default: 1)
- `selected_variation_index` (Integer, 0-2, nullable)
- `status` (Enum: 'pending', 'processing', 'completed', 'failed')
- `progress` (Integer, 0-100)
- `cost` (Decimal)
- `error_message` (Text, nullable)
- `campaign_json` (JSONB) - Scene data, style spec, etc.
- `created_at` (Timestamp)
- `updated_at` (Timestamp)

**Fields REMOVED (from current system):**
- ❌ `brand_description` - Now from brand table
- ❌ `target_audience` - Removed entirely
- ❌ `reference_image` - Removed entirely
- ❌ `ad_project_json` - Renamed to `campaign_json`

**S3 Storage (Updated Structure):**
```
s3://bucket/brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/
  ├── variations/
  │   ├── variation_0/
  │   │   ├── draft/
  │   │   │   ├── scene_1_bg.mp4
  │   │   │   ├── scene_2_bg.mp4
  │   │   │   ├── scene_3_bg.mp4
  │   │   │   ├── scene_4_bg.mp4
  │   │   │   └── music.mp3
  │   │   └── final_video.mp4
  │   ├── variation_1/
  │   │   ├── draft/
  │   │   │   └── ...
  │   │   └── final_video.mp4
  │   └── variation_2/
  │       ├── draft/
  │       │   └── ...
  │       └── final_video.mp4
```

**Storage Details:**
- Each variation has its own folder
- `draft/` subfolder contains:
  - Scene background videos (scene_1_bg.mp4, scene_2_bg.mp4, etc.)
  - Generated music (music.mp3)
- Root of variation folder contains:
  - Final composited video (final_video.mp4)

**Business Rules:**
- Campaign name must be unique within perfume
- Creative prompt is REQUIRED
- Style selection is REQUIRED
- Duration: 15-60 seconds only (TikTok limit)
- Variations: 1-3 only
- Cannot delete campaign if status = 'processing'

---

### 5. Style Cascading System (Updated)

**Style Inputs (Priority Order):**

1. **Brand Guidelines** (Highest Priority)
   - Extracted from brand's uploaded PDF/DOCX
   - Colors, tone, dos/donts
   - Automatically applied to ALL campaigns

2. **Creative Prompt** (High Priority)
   - User's creative direction per campaign
   - Describes mood, setting, vibe

3. **Video Style** (High Priority)
   - User selects: gold_luxe, dark_elegance, or romantic_floral
   - Defines visual treatment

4. **Perfume Gender** (Medium Priority)
   - Masculine, Feminine, Unisex
   - Influences music prompt and scene descriptions

**Removed:**
- ❌ Reference Image (removed entirely from system)

**Style Merge Logic:**
```python
def create_style_spec(brand, campaign, perfume):
    # Extract brand guidelines (colors, tone, dos/donts)
    brand_style = extract_brand_guidelines(brand.brand_guidelines_url)
    
    # Get selected video style config
    video_style = get_style_config(campaign.selected_style)
    
    # Merge with priority
    final_style = {
        "colors": brand_style.colors or video_style.colors,
        "lighting": video_style.lighting,  # From selected style
        "mood": infer_mood_from_prompt(campaign.creative_prompt),
        "camera": video_style.camera,
        "tone": brand_style.tone or video_style.tone,
        "gender": perfume.perfume_gender,  # For music generation
        "dos": brand_style.dos,
        "donts": brand_style.donts,
    }
    
    return final_style
```

---

## User Flows

### Flow 1: New User Onboarding (First Time)

```
1. User visits app → Clicks "Sign Up"
   
2. Signup Page
   - Email input
   - Password input (min 8 chars, validation)
   - Confirm password
   - Terms checkbox
   - Click "Create Account"
   
3. Supabase creates auth user
   - Redirect to Onboarding page (CANNOT SKIP)
   
4. Onboarding Page (3 sections)
   
   Section 1: Brand Name
   - Text input: "Enter your brand name"
   - Placeholder: "e.g., Noir Élégance"
   - Max 100 characters
   
   Section 2: Brand Logo
   - Drag-and-drop upload area
   - Or click to browse
   - Preview image after upload
   - Format: PNG, JPG, WebP (max 5MB)
   - Required: Show red border if empty
   
   Section 3: Brand Guidelines
   - Drag-and-drop upload area
   - Or click to browse
   - Show filename after upload
   - Format: PDF, DOCX (max 10MB)
   - Required: Show red border if empty
   
   Bottom:
   - "Complete Onboarding" button (disabled until all fields filled)
   - Shows loading spinner during upload
   
5. Submit Onboarding
   - Upload logo to S3: brands/{brand_id}/brand_logo.png
   - Upload guidelines to S3: brands/{brand_id}/brand_guidelines.pdf
   - Create brand record in database
   - Set onboarding_completed = true
   - Show success message: "✓ Brand setup complete!"
   - Redirect to Main Dashboard

6. Main Dashboard (empty state)
   - Header: "Your Perfumes"
   - Empty state message:
     "No perfumes yet. Add your first perfume to start creating campaigns!"
   - Button: "+ Add Perfume"
```

---

### Flow 2: Add New Perfume

```
1. Main Dashboard → Click "+ Add Perfume" button

2. Add Perfume Modal/Page (Form)
   
   Field 1: Perfume Name
   - Text input
   - Placeholder: "e.g., Midnight Rose"
   - Max 200 characters
   - Required
   
   Field 2: Gender
   - 3-button selector (similar to current variation selector)
   - Options: Masculine | Feminine | Unisex
   - Default: Unisex selected
   - Required
   
   Field 3: Front Image (REQUIRED)
   - Label: "Front View (Required) *"
   - Drag-and-drop upload
   - Preview thumbnail after upload
   - Format: PNG, JPG, WebP (max 5MB)
   - Red border if empty and user tries to submit
   
   Field 4: Additional Images (Optional)
   - Label: "Additional Views (Optional)"
   - 4 upload slots in a row:
     [Back] [Top] [Left] [Right]
   - Each slot has mini drag-and-drop area
   - Optional helper text: "These views help create more dynamic shots"
   
   Bottom:
   - "Cancel" button (gray)
   - "Add Perfume" button (gold, disabled until name + gender + front image provided)
   
3. Submit
   - Upload images to S3:
     brands/{brand_id}/perfumes/{perfume_id}/front.png (required)
     brands/{brand_id}/perfumes/{perfume_id}/back.png (if provided)
     brands/{brand_id}/perfumes/{perfume_id}/top.png (if provided)
     brands/{brand_id}/perfumes/{perfume_id}/left.png (if provided)
     brands/{brand_id}/perfumes/{perfume_id}/right.png (if provided)
   - Create perfume record in database
   - Show success toast: "✓ Perfume added successfully"
   - Close modal, refresh dashboard

4. Main Dashboard (with perfumes)
   - Shows grid of perfume cards
   - Each card shows:
     - Front image (thumbnail)
     - Perfume name
     - Gender badge (M/F/U)
     - Number of campaigns badge ("5 campaigns")
     - Click card → Navigate to Campaign Dashboard
```

---

### Flow 3: View Campaign Dashboard (Per Perfume)

```
1. Main Dashboard → Click on a perfume card
   
2. Campaign Dashboard Page
   
   Header:
   - Breadcrumb: "Your Perfumes > Midnight Rose"
   - Perfume name (large)
   - Back button to Main Dashboard
   
   Perfume Details Card (top):
   - Large front image
   - Perfume name
   - Gender badge
   - Image count: "3 images uploaded (front, back, top)"
   - Button: "Edit Perfume" (future - gray out for MVP)
   
   Campaigns Section:
   - Header: "Ad Campaigns" + "+ Create Campaign" button (gold)
   - If no campaigns:
     Empty state: "No campaigns yet. Create your first TikTok ad!"
   - If campaigns exist:
     Grid of campaign cards
     
   Campaign Card:
   - Thumbnail: First frame of final video (or placeholder)
   - Campaign name
   - Status badge: Processing / Completed / Failed
   - Duration: "30s"
   - Variations: "3 variations"
   - Created date: "2 days ago"
   - Cost: "$1.05"
   - Click card → Navigate to Campaign Results
```

---

### Flow 4: Create New Campaign

```
1. Campaign Dashboard → Click "+ Create Campaign" button

2. Create Campaign Page (Similar to current CreateProject)
   
   Header:
   - Breadcrumb: "Your Perfumes > Midnight Rose > New Campaign"
   - Title: "Create Ad Campaign"
   
   Form Fields (Updated):
   
   ✅ KEEP (from current):
   - Campaign Name (new field, required)
     Placeholder: "e.g., Holiday Collection 2025"
   - Creative Prompt (keep, required)
   - Video Style Selector (keep, 3 perfume styles)
   - Duration Slider (keep, 15-60s)
   - Variations Selector (keep, 1-3)
   
   ❌ REMOVE (from current):
   - Brand Name (auto-filled from brand table)
   - Brand Description (auto-filled from brand table)
   - Target Audience (removed entirely)
   - Reference Image Upload (removed entirely)
   - Perfume Name (auto-filled from selected perfume)
   - Perfume Gender (auto-filled from selected perfume)
   - Product Image Upload (auto-filled from perfume images)
   
   Auto-Populated (Show as read-only badges):
   - Brand: "Noir Élégance" (from brand table)
   - Perfume: "Midnight Rose" (from selected perfume)
   - Gender: "Feminine" (from perfume)
   - Images: "4 images available" (from perfume)
   
   Bottom:
   - "Cancel" button
   - "Generate Campaign" button (gold, shows cost estimate: "~$1.05")
   
3. Submit
   - Validate all required fields
   - Create campaign record (status: pending)
   - Enqueue generation job
   - Redirect to Generation Progress page

4. Generation Progress Page
   - Same as current system
   - Real-time progress (0-100%)
   - 8 steps shown
   - If num_variations > 1:
     Navigate to VideoSelection page after completion
   - If num_variations = 1:
     Navigate to Campaign Results page after completion
```

---

### Flow 5: View Campaign Results

```
1. Campaign Dashboard → Click completed campaign card

2. Campaign Results Page (Similar to current VideoResults)
   
   Header:
   - Breadcrumb: "Your Perfumes > Midnight Rose > Holiday Campaign"
   - Campaign name
   - Back button to Campaign Dashboard
   
   Campaign Details Card:
   - Perfume: "Midnight Rose"
   - Style: "Dark Elegance"
   - Duration: "30s"
   - Created: "2 days ago"
   - Cost: "$1.05"
   - Status: ✓ Completed
   
   Video Player Section:
   - Large video player
   - Play/pause controls
   - If multiple variations:
     Variation tabs: "Variation 1" | "Variation 2" | "Variation 3"
     Selected variation = user's choice from VideoSelection
   
   Download Section:
   - "Download Video" button (downloads final_video.mp4)
   - Show file size: "~15MB"
   
   Actions:
   - "Create Similar" button (clones campaign with same settings)
   - "Delete Campaign" button (confirmation modal)
```

---

## UI/UX Changes

### Page Structure (Before vs After)

**BEFORE (Current):**
```
/                 → Landing
/login            → Login
/signup           → Signup
/dashboard        → Project List (ALL projects from ALL users)
/projects/create  → Create Project
/projects/:id     → Video Results
```

**AFTER (New):**
```
/                        → Landing
/login                   → Login
/signup                  → Signup
/onboarding              → Brand Onboarding (NEW, mandatory)
/dashboard               → Perfume List (NEW, brand-specific)
/perfumes/add            → Add Perfume Form (NEW)
/perfumes/:perfumeId     → Campaign Dashboard (NEW, per perfume)
/perfumes/:perfumeId/campaigns/create  → Create Campaign (UPDATED)
/campaigns/:campaignId/progress        → Generation Progress (same)
/campaigns/:campaignId/select          → Variation Selection (same)
/campaigns/:campaignId/results         → Campaign Results (UPDATED)
```

### Main Dashboard (NEW)

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Header                                             │
│  [Logo]  Your Perfumes                 [User Menu] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌────────────────────────────────────────────┐   │
│  │  Perfumes                   [+ Add Perfume]│   │
│  └────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ [Image] │  │ [Image] │  │ [Image] │           │
│  │ Perfume │  │ Perfume │  │ Perfume │           │
│  │ Name 1  │  │ Name 2  │  │ Name 3  │           │
│  │ Gender  │  │ Gender  │  │ Gender  │           │
│  │ 5 camps │  │ 3 camps │  │ 8 camps │           │
│  └─────────┘  └─────────┘  └─────────┘           │
│                                                     │
│  Empty State (if no perfumes):                     │
│  "No perfumes yet. Add your first perfume to       │
│   start creating campaigns!"                       │
│  [+ Add Perfume]                                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Campaign Dashboard (NEW)

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  [< Back]  Your Perfumes > Midnight Rose           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │  Perfume Details                             │ │
│  │  [Large Image]  Midnight Rose                │ │
│  │                 Feminine                      │ │
│  │                 4 images uploaded             │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │  Ad Campaigns              [+ Create Campaign]│ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │[Thumb]  │  │[Thumb]  │  │[Thumb]  │           │
│  │Holiday  │  │Summer   │  │Spring   │           │
│  │Campaign │  │Campaign │  │Campaign │           │
│  │✓ Done   │  │⏳ Process│  │✓ Done   │           │
│  │30s, $1.05│  │45s, $1.20│  │15s, $0.60│         │
│  └─────────┘  └─────────┘  └─────────┘           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## API Endpoints (New Structure)

### Brand Endpoints

```
POST   /api/brands/onboard
  - Create brand during onboarding
  - Upload logo + guidelines to S3
  - Body: { brand_name, logo_file, guidelines_file }
  - Response: { brand_id, onboarding_completed: true }

GET    /api/brands/me
  - Get current user's brand
  - Response: { brand_id, brand_name, logo_url, guidelines_url, onboarding_completed }

GET    /api/brands/me/stats
  - Get brand statistics
  - Response: { total_perfumes, total_campaigns, total_cost }
```

### Perfume Endpoints

```
POST   /api/perfumes
  - Create new perfume
  - Upload images to S3
  - Body: { perfume_name, gender, front_image, back_image?, top_image?, left_image?, right_image? }
  - Response: { perfume_id, ... }

GET    /api/perfumes
  - List all perfumes for current brand
  - Query: ?page=1&limit=20
  - Response: { perfumes: [...], total, page, limit }

GET    /api/perfumes/:perfumeId
  - Get perfume details
  - Response: { perfume_id, perfume_name, gender, image_urls, campaign_count }

PUT    /api/perfumes/:perfumeId
  - Update perfume (future - not MVP)

DELETE /api/perfumes/:perfumeId
  - Delete perfume (only if no campaigns)
```

### Campaign Endpoints (Updated)

```
POST   /api/campaigns
  - Create new campaign
  - Body: { perfume_id, campaign_name, creative_prompt, selected_style, target_duration, num_variations }
  - Note: brand_id inferred from auth user
  - Response: { campaign_id, status: 'pending' }

GET    /api/campaigns?perfume_id={id}
  - List campaigns for a perfume
  - Query: ?perfume_id=xxx&page=1&limit=20
  - Response: { campaigns: [...], total, page, limit }

GET    /api/campaigns/:campaignId
  - Get campaign details
  - Response: { campaign_id, perfume_id, brand_id, campaign_name, status, progress, cost, ... }

DELETE /api/campaigns/:campaignId
  - Delete campaign (only if not processing)
```

### Generation Endpoints (Same as Current)

```
POST   /api/generation/campaigns/:campaignId/generate
  - Trigger generation job

GET    /api/generation/campaigns/:campaignId/progress
  - Poll generation progress

POST   /api/generation/campaigns/:campaignId/select-variation
  - Select variation
```

---

## Database Schema Changes

### New Tables

#### 1. `brands` Table (NEW)

```sql
CREATE TABLE brands (
  brand_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_name VARCHAR(100) NOT NULL UNIQUE,
  brand_logo_url VARCHAR(500) NOT NULL,
  brand_guidelines_url VARCHAR(500) NOT NULL,
  onboarding_completed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_brands_user_id ON brands(user_id);
CREATE INDEX idx_brands_onboarding ON brands(onboarding_completed);
```

#### 2. `perfumes` Table (NEW)

```sql
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
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(brand_id, perfume_name)  -- Perfume name unique within brand
);

CREATE INDEX idx_perfumes_brand_id ON perfumes(brand_id);
CREATE INDEX idx_perfumes_gender ON perfumes(perfume_gender);
```

#### 3. `campaigns` Table (REPLACES `projects`)

```sql
CREATE TABLE campaigns (
  campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  perfume_id UUID NOT NULL REFERENCES perfumes(perfume_id) ON DELETE CASCADE,
  brand_id UUID NOT NULL REFERENCES brands(brand_id) ON DELETE CASCADE,  -- Denormalized for quick queries
  
  campaign_name VARCHAR(200) NOT NULL,
  creative_prompt TEXT NOT NULL,
  selected_style VARCHAR(50) NOT NULL CHECK (selected_style IN ('gold_luxe', 'dark_elegance', 'romantic_floral')),
  target_duration INTEGER NOT NULL CHECK (target_duration BETWEEN 15 AND 60),
  num_variations INTEGER DEFAULT 1 CHECK (num_variations BETWEEN 1 AND 3),
  selected_variation_index INTEGER CHECK (selected_variation_index BETWEEN 0 AND 2),
  
  status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  progress INTEGER DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  cost DECIMAL(10,2) DEFAULT 0,
  error_message TEXT,
  
  campaign_json JSONB NOT NULL,  -- Scene data, style spec, etc.
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(perfume_id, campaign_name)  -- Campaign name unique within perfume
);

CREATE INDEX idx_campaigns_perfume_id ON campaigns(perfume_id);
CREATE INDEX idx_campaigns_brand_id ON campaigns(brand_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_created_at ON campaigns(created_at DESC);
```

### Table Relationships

```
auth.users (Supabase Auth)
    ↓ 1:1
brands
    ↓ 1:N
perfumes
    ↓ 1:N
campaigns
```

**Cascade Behavior:**
- Delete user → Delete brand → Delete all perfumes → Delete all campaigns
- Delete brand → Delete all perfumes → Delete all campaigns
- Delete perfume → Delete all campaigns for that perfume
- Cannot delete perfume if campaigns exist (business logic)

---

## S3 Storage Structure (Updated)

### New Hierarchy

```
s3://genads-videos/
  brands/
    {brand_id}/                              # One folder per brand
      brand_logo.png                         # Brand logo
      brand_guidelines.pdf                   # Brand guidelines document
      
      perfumes/
        {perfume_id}/                        # One folder per perfume
          front.png                          # REQUIRED
          back.png                           # optional
          top.png                            # optional
          left.png                           # optional
          right.png                          # optional
          
          campaigns/
            {campaign_id}/                   # One folder per campaign
              variations/
                variation_0/
                  draft/
                    scene_1_bg.mp4           # Generated background videos
                    scene_2_bg.mp4
                    scene_3_bg.mp4
                    scene_4_bg.mp4
                    music.mp3                # Generated music
                  final_video.mp4            # Final composited video
                
                variation_1/
                  draft/
                    scene_1_bg.mp4
                    scene_2_bg.mp4
                    scene_3_bg.mp4
                    scene_4_bg.mp4
                    music.mp3
                  final_video.mp4
                
                variation_2/
                  draft/
                    scene_1_bg.mp4
                    scene_2_bg.mp4
                    scene_3_bg.mp4
                    scene_4_bg.mp4
                    music.mp3
                  final_video.mp4
```

### Storage Rules

1. **Brand Level:**
   - Logo: PNG/JPG/WebP, max 5MB
   - Guidelines: PDF/DOCX, max 10MB
   - Lifecycle: Keep forever (no auto-delete)

2. **Perfume Level:**
   - Images: PNG/JPG/WebP, max 5MB each
   - Lifecycle: Keep forever (no auto-delete)

3. **Campaign Level:**
   - Draft videos: Keep for 30 days (lifecycle policy)
   - Final videos: Keep for 90 days (lifecycle policy)
   - Music: Keep for 30 days
   - User can download within 90 days

### S3 Lifecycle Policy (Updated)

```json
{
  "Rules": [
    {
      "Id": "DeleteDraftVideosAfter30Days",
      "Prefix": "brands/",
      "Filter": {
        "And": {
          "Tags": [{"Key": "type", "Value": "draft"}]
        }
      },
      "Status": "Enabled",
      "Expiration": {"Days": 30}
    },
    {
      "Id": "DeleteFinalVideosAfter90Days",
      "Prefix": "brands/",
      "Filter": {
        "And": {
          "Tags": [{"Key": "type", "Value": "final"}]
        }
      },
      "Status": "Enabled",
      "Expiration": {"Days": 90}
    }
  ]
}
```

---

## Success Metrics

### MVP Success Criteria

**Functional:**
- ✅ User can complete onboarding
- ✅ User can add perfumes with images
- ✅ User can create campaigns under perfumes
- ✅ All campaigns auto-use brand guidelines
- ✅ Campaigns organized by perfume
- ✅ Full brand isolation (no data leaks)

**Performance:**
- ✅ Onboarding completes in <30 seconds
- ✅ Perfume creation in <15 seconds
- ✅ Campaign generation same as current (~5-7 min)

**Data Integrity:**
- ✅ No cross-brand data access
- ✅ Cascade deletes work correctly
- ✅ S3 storage reflects database hierarchy

### Post-MVP Enhancements

**Phase 1 (Settings):**
- Update brand name/logo/guidelines
- Edit perfume details
- Duplicate campaigns

**Phase 2 (Teams):**
- Multi-user support per brand
- Role-based access (Admin, Editor, Viewer)
- Invite team members

**Phase 3 (Analytics):**
- Campaign performance tracking
- Cost analytics per perfume
- Usage insights

---

## Migration Strategy

### Data Migration (NOT NEEDED)

**User confirmed:** "I will be deleting my current database and creating a new one"

**Action:** Fresh database with new schema
- No data migration required
- Clean slate
- Existing users will need to re-signup

### Code Migration (Backend)

**Keep (No Changes):**
- ✅ Scene planner with perfume shot grammar
- ✅ Multi-variation generation logic
- ✅ Style selection (3 perfume styles)
- ✅ Video generator (Wān model)
- ✅ Compositor
- ✅ Audio engine
- ✅ Renderer
- ✅ Text overlay

**Update (Data Models Only):**
- ✅ Database models (brands, perfumes, campaigns)
- ✅ API endpoints (new routes, updated responses)
- ✅ S3 storage paths (new hierarchy)
- ✅ Brand guidelines extraction (use brand table)

**Remove:**
- ❌ Reference image extractor (feature removed)
- ❌ Target audience logic (feature removed)
- ❌ Brand description in campaign (moved to brand table)

---

## Timeline Estimate

### Phase-by-Phase Breakdown

**Total:** 120-160 hours (3-4 weeks)

1. **Database & Models** (2-3 days, 16-24 hours)
   - Create new tables (brands, perfumes, campaigns)
   - Alembic migrations
   - ORM model updates
   - Pydantic schema updates

2. **S3 Storage Refactor** (2 days, 16 hours)
   - Update storage utility functions
   - New upload paths
   - Lifecycle policies
   - Test upload/download

3. **Backend API** (5-7 days, 40-56 hours)
   - Brand onboarding endpoint
   - Perfume CRUD endpoints
   - Campaign CRUD endpoints (updated)
   - Generation pipeline updates (use brand guidelines)
   - Remove reference image logic
   - Testing

4. **Frontend Pages** (5-7 days, 40-56 hours)
   - Onboarding page (brand setup)
   - Main dashboard (perfume list)
   - Add perfume form
   - Campaign dashboard (per perfume)
   - Create campaign page (updated)
   - Campaign results page (updated)
   - Navigation updates
   - Auth guards (onboarding check)

5. **Integration & Testing** (3-4 days, 24-32 hours)
   - End-to-end testing
   - S3 storage verification
   - Brand isolation testing
   - Bug fixes
   - Performance optimization

6. **Documentation & Deployment** (1 day, 8 hours)
   - Update README
   - API documentation
   - Deployment to production
   - Smoke testing

---

## Risk Assessment

### High Risk

1. **S3 Storage Migration**
   - Risk: Complex path restructuring
   - Mitigation: Test thoroughly with multiple scenarios
   - Rollback: Keep old storage logic in separate branch

2. **Data Model Complexity**
   - Risk: 3-tier relationship might cause query complexity
   - Mitigation: Proper indexing, denormalize brand_id in campaigns
   - Rollback: Can flatten structure if needed

3. **Onboarding UX**
   - Risk: Users might drop off during mandatory onboarding
   - Mitigation: Make it fast (<30s), clear progress indicators
   - Rollback: Allow skip (set onboarding_completed = false)

### Medium Risk

4. **Brand Guidelines Extraction**
   - Risk: PDF/DOCX parsing might fail
   - Mitigation: Graceful fallback, allow manual color input
   - Rollback: Skip brand guidelines, use creative prompt only

5. **Perfume Image Fallback**
   - Risk: Fallback logic might look repetitive
   - Mitigation: Show warning when only front image provided
   - Rollback: Require all 5 images (too strict)

### Low Risk

6. **API Endpoint Changes**
   - Risk: Frontend-backend mismatch
   - Mitigation: Update both simultaneously, comprehensive testing
   - Rollback: Keep old endpoints in parallel during transition

---

## Open Questions (Resolved)

1. ✅ **Multi-user teams?** NO - 1 user = 1 brand for MVP
2. ✅ **Onboarding skippable?** NO - Mandatory with database flag
3. ✅ **Optional perfume images?** YES - Only front required
4. ✅ **Style cascading inputs?** Brand guidelines + creative prompt + style + gender
5. ✅ **Dashboard shows what?** Only perfumes (not campaigns)
6. ✅ **Keep generation logic?** YES - Option A, only restructure data models
7. ✅ **S3 draft videos?** YES - Store in variation_N/draft/ subfolder

---

**Status:** Ready for Implementation  
**Next:** Review Architecture Document  
**Last Updated:** November 18, 2025

