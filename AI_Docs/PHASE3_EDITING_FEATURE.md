# Phase 3: AI Scene Editing Feature - Complete Implementation Documentation

**Version:** 1.0  
**Created:** January 20, 2025  
**Architecture:** S3-First with Integrated Video Preview UI  
**Estimated Timeline:** 27-35 hours (3.5-4.5 days)  
**Edit Type:** Prompt-based modifications only (MVP)

---

## Table of Contents

1. [Overview](#overview)
2. [User Experience Flow](#user-experience-flow)
3. [Architecture Design](#architecture-design)
4. [Database Schema Changes](#database-schema-changes)
5. [Backend Implementation Tasks](#backend-implementation-tasks)
6. [Frontend Implementation Tasks](#frontend-implementation-tasks)
7. [Implementation Phases](#implementation-phases)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Checklist](#deployment-checklist)
10. [Cost Analysis](#cost-analysis)
11. [Success Metrics](#success-metrics)

---

## Overview

### Feature Goal
Allow users to edit individual scenes in their generated videos via natural language prompts, directly from the video results page, with seamless preview updates.

### Key Principles
- ✅ **Integrated Experience**: Edit from video preview page (no navigation)
- ✅ **Simple Interface**: Small popup, single text input, immediate feedback
- ✅ **S3-First**: All videos stored in S3, temporary local processing only
- ✅ **Lightweight History**: Track operations (not video versions)
- ✅ **Single Scene Edits**: One scene at a time (MVP)
- ✅ **Cost Transparency**: Show edit cost (~$0.21 per scene)

### Technical Constraints
- Scene videos stored in S3 (must download for re-rendering)
- Local storage is temporary staging only
- Existing final video replaced with new version
- Edit history tracked in `campaign_json` (JSONB)
- No video versioning (lightweight audit trail only)

---

## User Experience Flow

### Complete User Journey

```
USER COMPLETES VIDEO GENERATION
→ Redirected to VideoResults page
  ↓
VIDEO RESULTS PAGE LAYOUT
┌─────────────────────────────────────────────────────────┐
│ LEFT SIDE: Main Video Player (70% width)                │
│ ┌─────────────────────────────────────────────────────┐ │
│ │         [Video Player - 9:16 TikTok Vertical]        │ │
│ │              Playing final video                     │ │
│ └─────────────────────────────────────────────────────┘ │
│ [Play] [Pause] [Mute] [Download]                        │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ RIGHT SIDEBAR: Scene Thumbnails (30% width)            │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Scene 1 - Hook (3s)                                 │ │
│ │ ┌─────────────────┐                                 │ │
│ │ │   [Thumbnail]   │  [Edit Scene 🖊️]               │ │
│ │ └─────────────────┘                                 │ │
│ │ "Luxury perfume bottle on silk..."                 │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Scene 2 - Showcase (4s)                             │ │
│ │ ┌─────────────────┐                                 │ │
│ │ │   [Thumbnail]   │  [Edit Scene 🖊️]               │ │
│ │ └─────────────────┘                                 │ │
│ │ "Close-up of perfume with golden..."               │ │
│ │ Edited 1 time                                      │ │
│ └─────────────────────────────────────────────────────┘ │
│ ... (Scene 3, Scene 4)                                 │
└─────────────────────────────────────────────────────────┘
  ↓
USER CLICKS "EDIT SCENE" BUTTON (e.g., Scene 2)
  ↓
SMALL POPUP APPEARS (Centered overlay, 400px width)
┌─────────────────────────────────────────────────────────┐
│ Edit Scene 2 - Showcase                           [×]  │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ What would you like to change on this scene?           │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ e.g., "Make brighter and add golden tones"         │ │
│ │                                                     │ │
│ │ [Text area - 4 rows]                               │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Cost: ~$0.21 | Time: ~3 minutes                        │
│                                                         │
│                           [Cancel] [Edit Scene]        │
└─────────────────────────────────────────────────────────┘
  ↓
USER ENTERS PROMPT: "Make brighter and add golden tones"
USER CLICKS "EDIT SCENE"
  ↓
POPUP CLOSES
VIDEO PLAYER SHOWS LOADING STATE
┌─────────────────────────────────────────────────────────┐
│ LEFT SIDE: Video Player (Loading overlay)              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │            🔄 Editing Scene 2...                    │ │
│ │         Modifying prompt and regenerating           │ │
│ │         This will take ~3 minutes                   │ │
│ │         ▓▓▓▓▓▓▓▓░░░░░░░░░░░░ 40%                    │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
RIGHT SIDEBAR: Scene 2 shows "Editing..." badge
  ↓
BACKEND PROCESSING (3-4 minutes)
1. LLM modifies prompt
2. Regenerate scene 2 video (ByteDance)
3. Replace scene 2 in S3
4. Download all 4 scenes from S3
5. Re-render final video (FFmpeg)
6. Upload new final video to S3 (replaces old)
7. Update campaign_json with edit history
  ↓
EDIT COMPLETE
VIDEO PLAYER AUTOMATICALLY RELOADS WITH NEW VIDEO
┌─────────────────────────────────────────────────────────┐
│ LEFT SIDE: Video Player                                 │
│ ┌─────────────────────────────────────────────────────┐ │
│ │    [NEW Video Playing - Scene 2 is now brighter]    │ │
│ └─────────────────────────────────────────────────────┘ │
│ ✅ Scene 2 edited successfully! (+$0.21)               │
└─────────────────────────────────────────────────────────┘
RIGHT SIDEBAR: Scene 2 now shows "Edited 1 time"
```

---

## Architecture Design

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                    │
├─────────────────────────────────────────────────────────┤
│ VideoResults.tsx (Updated)                             │
│  ├─ VideoPlayer component (Left 70%)                   │
│  └─ SceneSidebar component (Right 30%) ← NEW          │
│      └─ SceneCard component (Per scene) ← NEW         │
│          └─ EditScenePopup component ← NEW             │
└─────────────────────────────────────────────────────────┘
                          ↓ HTTP API
┌─────────────────────────────────────────────────────────┐
│                 BACKEND API (FastAPI)                  │
├─────────────────────────────────────────────────────────┤
│ editing.py (New router) ← NEW                          │
│  ├─ GET /api/campaigns/{id}/scenes                      │
│  ├─ POST /api/campaigns/{id}/scenes/{idx}/edit          │
│  └─ GET /api/campaigns/{id}/edit-history                │
└─────────────────────────────────────────────────────────┘
                          ↓ Enqueue Job
┌─────────────────────────────────────────────────────────┐
│                  RQ WORKER (Background)                │
├─────────────────────────────────────────────────────────┤
│ edit_pipeline.py (New job) ← NEW                       │
│  └─ SceneEditPipeline class                            │
│      ├─ Step 1: Load campaign + scene data            │
│      ├─ Step 2: Modify prompt (EditService) ← NEW     │
│      ├─ Step 3: Regenerate video (VideoGenerator)      │
│      ├─ Step 4: Replace scene in S3                    │
│      ├─ Step 5: Download all scenes from S3            │
│      ├─ Step 6: Re-render final (Renderer)             │
│      ├─ Step 7: Upload new final to S3 (replace)       │
│      └─ Step 8: Update campaign_json + history         │
└─────────────────────────────────────────────────────────┘
                          ↓ Status Updates
┌─────────────────────────────────────────────────────────┐
│                DATABASE (PostgreSQL/Supabase)           │
├─────────────────────────────────────────────────────────┤
│ campaigns table                                         │
│  ├─ edit_history (JSONB) ← NEW COLUMN                  │
│  └─ campaign_json (JSONB) - Updated scenes            │
└─────────────────────────────────────────────────────────┘
                          ↓ Storage
┌─────────────────────────────────────────────────────────┐
│                    AWS S3 (Storage)                     │
├─────────────────────────────────────────────────────────┤
│ brands/{id}/perfumes/{id}/campaigns/{id}/variations/0/│
│  ├─ draft/                                             │
│  │   ├─ scene_1_bg.mp4 (original)                     │
│  │   ├─ scene_2_bg.mp4 (REPLACED after edit) ← UPDATED│
│  │   ├─ scene_3_bg.mp4 (original)                     │
│  │   ├─ scene_4_bg.mp4 (original)                     │
│  │   └─ music.mp3                                     │
│  └─ final_video.mp4 (REPLACED after edit) ← UPDATED  │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
1. USER INTERACTION
   User clicks "Edit Scene 2" → Enters prompt
   ↓
2. API REQUEST
   POST /api/campaigns/{id}/scenes/1/edit
   Body: { edit_prompt: "Make brighter..." }
   ↓
3. JOB ENQUEUED
   RQ Worker: edit_scene_job(campaign_id, 1, prompt)
   Returns: { job_id: "abc123", estimated_cost: 0.21 }
   ↓
4. FRONTEND POLLING
   Poll every 2s: GET /api/generation/jobs/{job_id}/status
   Shows loading spinner on video player
   ↓
5. WORKER PROCESSING (Async)
   ├─ Load scene data from campaign_json
   ├─ EditService.modify_scene_prompt()
   ├─ VideoGenerator.generate_scene_background()
   ├─ Upload to S3 (replaces old scene_2_bg.mp4)
   ├─ Download all 4 scenes from S3
   ├─ Renderer.render_final_video()
   ├─ Upload final_video.mp4 to S3 (replaces old)
   └─ Update campaign_json + edit_history
   ↓
6. JOB COMPLETE
   Status: "completed"
   Response: { new_video_url: "s3://...", cost: 0.21 }
   ↓
7. FRONTEND UPDATES
   ├─ Stop polling
   ├─ Reload video player with new S3 URL
   ├─ Update scene card (show "Edited 1 time")
   └─ Show success toast
```

---

## Database Schema Changes

### Migration: Add Edit History Column

**File:** `backend/alembic/versions/009_add_edit_history.py`

```python
"""Add edit history tracking to campaigns

Revision ID: 009
Revises: 008
Create Date: 2025-01-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009'
down_revision = '008'

def upgrade():
    # Add edit_history column to campaigns table
    op.add_column(
        'campaigns',
        sa.Column('edit_history', postgresql.JSONB, nullable=True)
    )
    
    # Create index for querying edit history
    op.create_index(
        'idx_campaigns_edit_history',
        'campaigns',
        ['edit_history'],
        postgresql_using='gin'
    )

def downgrade():
    op.drop_index('idx_campaigns_edit_history', table_name='campaigns')
    op.drop_column('campaigns', 'edit_history')
```

### Edit History JSON Structure

```json
{
  "edits": [
    {
      "edit_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2025-01-20T10:30:45Z",
      "scene_index": 1,
      "edit_prompt": "Make brighter and add golden tones",
      "original_prompt": "Luxury perfume bottle on silk fabric with soft lighting",
      "modified_prompt": "Luxury perfume bottle on silk fabric with BRIGHT golden hour lighting, warm glowing tones, enhanced luminosity",
      "changes_summary": "Increased lighting brightness and added golden color grading for warmer atmosphere",
      "cost": 0.21,
      "duration_seconds": 187
    }
  ],
  "total_edit_cost": 0.63,
  "edit_count": 3
}
```

### Updated Campaign Model

**File:** `backend/app/database/models.py`

```python
class Campaign(Base):
    __tablename__ = "campaigns"
    
    # ... existing fields ...
    
    # NEW: Edit history tracking
    edit_history = Column(JSONB, nullable=True)
    # Structure: { edits: [...], total_edit_cost: 0.0, edit_count: 0 }
```

---

## Backend Implementation Tasks

### Task 1: Create EditService (2-3 hours)

**File:** `backend/app/services/edit_service.py` (NEW)

**Requirements:**
- [ ] Create `EditService` class
- [ ] Implement `modify_scene_prompt()` method
  - Takes: original_prompt, edit_instruction, style_spec, scene_role, perfume_name
  - Uses: GPT-4o-mini with specialized system prompt
  - Returns: { modified_prompt, changes_summary }
- [ ] Implement `create_edit_record()` helper
  - Generates edit history record with UUID and timestamp
- [ ] Add comprehensive logging
- [ ] Add error handling for LLM failures

**System Prompt:**
```python
system_prompt = """You are an expert video director editing luxury perfume TikTok ads.

Given an original scene prompt and an edit instruction, modify the prompt to incorporate the changes while maintaining:
1. The core scene concept and composition
2. Perfume shot grammar rules (luxury, elegant, cinematic)
3. Overall style consistency with the campaign
4. TikTok vertical (9:16) optimization
5. User-first creative philosophy (honor the user's vision)

IMPORTANT:
- Apply the edit instruction precisely
- Keep the same scene structure (duration, role, transitions)
- Maintain perfume product visibility and placement
- Preserve brand visual identity
- Add specific cinematography details (lighting, camera, movement)

Return a JSON object:
{
  "modified_prompt": "The full modified prompt with changes applied",
  "changes_summary": "Brief 2-3 sentence summary of what changed"
}"""
```

**Acceptance Criteria:**
- ✅ Successfully modifies prompts based on edit instructions
- ✅ Maintains scene structure and brand consistency
- ✅ Returns valid JSON with modified_prompt and changes_summary
- ✅ Handles edge cases (empty prompts, vague instructions)
- ✅ Unit tests cover 5+ scenarios

---

### Task 2: Create SceneEditPipeline (4-5 hours)

**File:** `backend/app/jobs/edit_pipeline.py` (NEW)

**Requirements:**
- [ ] Create `SceneEditPipeline` class
- [ ] Implement `__init__()` - Load campaign, perfume, brand
- [ ] Implement `run()` method with 8 steps:
  - **Step 1:** Load scene data from campaign_json
  - **Step 2:** Modify prompt via EditService
  - **Step 3:** Regenerate scene video via VideoGenerator
  - **Step 4:** Download from Replicate URL, upload to S3 (replace old scene)
  - **Step 5:** Download ALL scene videos from S3 to /tmp
  - **Step 6:** Re-render final video via Renderer
  - **Step 7:** Upload new final video to S3 (replace old)
  - **Step 8:** Update campaign_json + edit_history in database
- [ ] Add progress tracking (update campaign status)
- [ ] Add cost tracking (accumulate costs per step)
- [ ] Implement cleanup (delete /tmp files)
- [ ] Add comprehensive error handling
- [ ] Create async job wrapper: `edit_scene_job(campaign_id, scene_index, edit_instruction)`

**Key Implementation Details:**

```python
# Step 4: Replace scene in S3
from app.utils.s3_utils import upload_draft_video

s3_result = await upload_draft_video(
    brand_id=str(self.campaign.brand_id),
    perfume_id=str(self.campaign.perfume_id),
    campaign_id=str(self.campaign_id),
    variation_index=self.campaign.selected_variation_index or 0,
    scene_index=self.scene_index + 1,  # 1-based index
    file_path=temp_video_path
)
# This OVERWRITES old scene_X_bg.mp4 in S3
```

**Acceptance Criteria:**
- ✅ Successfully edits a scene end-to-end
- ✅ Replaces scene video in S3 correctly
- ✅ Re-renders final video with edited scene
- ✅ Updates database with edit history
- ✅ Tracks cost accurately (~$0.21)
- ✅ Cleans up all temporary files
- ✅ Handles failures gracefully (partial cleanup)

---

### Task 3: Add S3 Helper Functions (30 minutes)

**File:** `backend/app/utils/s3_utils.py` (UPDATE)

**Requirements:**
- [ ] Add `get_scene_s3_url()` helper function
  - Takes: brand_id, perfume_id, campaign_id, variation_index, scene_index
  - Returns: Full S3 URL string
- [ ] Add `get_final_video_s3_url()` helper function
  - Takes: brand_id, perfume_id, campaign_id, variation_index
  - Returns: Full S3 URL string

**Example:**
```python
def get_scene_s3_url(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int,
    scene_index: int  # 0-based
) -> str:
    """Construct S3 URL for a scene video."""
    return (
        f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/"
        f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"
        f"variations/variation_{variation_index}/draft/scene_{scene_index+1}_bg.mp4"
    )
```

---

### Task 4: Create API Endpoints (3-4 hours)

**File:** `backend/app/api/editing.py` (NEW)

**Requirements:**
- [ ] Create FastAPI router with prefix `/api/campaigns`
- [ ] Implement 3 endpoints:

**Endpoint 1: GET /api/campaigns/{campaign_id}/scenes**
- Load campaign from database
- Verify ownership (user owns brand that owns campaign)
- Extract scenes from campaign_json
- Construct S3 URLs for each scene video
- Return list of SceneInfo objects

**Endpoint 2: POST /api/campaigns/{campaign_id}/scenes/{scene_index}/edit**
- Validate campaign exists and user owns it
- Validate scene_index is within range
- Enqueue edit job via RQ
- Return job_id and estimated cost/time

**Endpoint 3: GET /api/campaigns/{campaign_id}/edit-history**
- Load campaign edit_history from database
- Return list of EditHistoryRecord objects

**Pydantic Schemas:**
```python
class EditSceneRequest(BaseModel):
    edit_prompt: str

class EditSceneResponse(BaseModel):
    job_id: str
    estimated_cost: float
    estimated_duration_seconds: int
    message: str

class SceneInfo(BaseModel):
    scene_index: int
    scene_id: int
    role: str
    duration: int
    background_prompt: str
    video_url: str
    thumbnail_url: Optional[str] = None
    edit_count: int = 0
    last_edited_at: Optional[str] = None

class EditHistoryRecord(BaseModel):
    edit_id: str
    timestamp: str
    scene_index: int
    edit_prompt: str
    changes_summary: Optional[str] = None
    cost: float
    duration_seconds: int
```

**Acceptance Criteria:**
- ✅ All 3 endpoints implemented and tested
- ✅ Ownership verification works correctly
- ✅ Edit jobs enqueue successfully
- ✅ Scene data returned with correct S3 URLs
- ✅ Edit history returns all edits chronologically

---

### Task 5: Update Worker to Handle Edit Jobs (1 hour)

**File:** `backend/app/jobs/worker.py` (UPDATE)

**Requirements:**
- [ ] Import `edit_scene_job` from edit_pipeline
- [ ] Add "edit_scene" to job type mapping
- [ ] Ensure RQ worker can execute edit jobs
- [ ] Test job enqueueing and execution

**Example:**
```python
# Add to worker.py
from app.jobs.edit_pipeline import edit_scene_job

JOB_FUNCTIONS = {
    "generate_campaign": generate_campaign_job,
    "edit_scene": edit_scene_job,  # NEW
}
```

---

### Task 6: Update Main App Router (15 minutes)

**File:** `backend/app/main.py` (UPDATE)

**Requirements:**
- [ ] Import editing router
- [ ] Include editing router in app

```python
from app.api import editing

app.include_router(editing.router)
```

---

### Task 7: Run Database Migration (15 minutes)

**Requirements:**
- [ ] Create migration file: `009_add_edit_history.py`
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify column added: `psql` check campaigns table
- [ ] Test JSONB operations (insert/query)

---

## Frontend Implementation Tasks

### Task 8: Create useSceneEditing Hook (2 hours)

**File:** `frontend/src/hooks/useSceneEditing.ts` (NEW)

**Requirements:**
- [ ] Create custom hook for scene editing operations
- [ ] Implement state management:
  - scenes: Scene[]
  - isLoading: boolean
  - editingSceneIndex: number | null
  - error: string | null
- [ ] Implement functions:
  - `loadScenes(campaignId)` - Fetch scenes from API
  - `editScene(campaignId, sceneIndex, editPrompt)` - Submit edit request
  - `pollEditJob(jobId)` - Poll job status until complete
  - `getEditHistory(campaignId)` - Fetch edit history

**Polling Logic:**
```typescript
const pollEditJob = async (jobId: string): Promise<void> => {
  const maxAttempts = 120; // 4 minutes max (2s intervals)
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    const response = await api.get(`/api/generation/jobs/${jobId}/status`);
    
    if (response.data.status === 'completed') {
      return; // Success
    } else if (response.data.status === 'failed') {
      throw new Error(response.data.error || 'Edit failed');
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2s
    attempts++;
  }
  
  throw new Error('Edit timeout - please refresh page');
};
```

**Acceptance Criteria:**
- ✅ Successfully loads scenes from API
- ✅ Enqueues edit jobs and polls for completion
- ✅ Handles errors gracefully
- ✅ Updates state correctly throughout flow
- ✅ TypeScript types are correct

---

### Task 9: Create SceneCard Component (2 hours)

**File:** `frontend/src/components/SceneCard.tsx` (NEW)

**Requirements:**
- [ ] Display scene thumbnail (or placeholder)
- [ ] Show scene metadata (role, duration)
- [ ] Show truncated background prompt
- [ ] Show edit count badge if edited
- [ ] "Edit Scene" button with pencil icon
- [ ] Loading state when scene is being edited
- [ ] Styled with luxury dark theme (charcoal bg, gold accents)

**Component Structure:**
```tsx
interface SceneCardProps {
  scene: Scene;
  isEditing: boolean;
  onEditClick: () => void;
}

export const SceneCard: React.FC<SceneCardProps> = ({
  scene,
  isEditing,
  onEditClick
}) => {
  return (
    <div className="scene-card bg-slate-800 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h4 className="text-sm font-semibold text-white">
            Scene {scene.scene_index + 1} - {scene.role}
          </h4>
          <p className="text-xs text-gray-400">{scene.duration}s</p>
        </div>
        {scene.edit_count > 0 && (
          <span className="text-xs bg-gold-500/20 text-gold-400 px-2 py-1 rounded">
            Edited {scene.edit_count}x
          </span>
        )}
      </div>
      
      {/* Thumbnail */}
      <div className="aspect-[9/16] bg-charcoal-900 rounded overflow-hidden">
        {scene.thumbnail_url ? (
          <img src={scene.thumbnail_url} alt={`Scene ${scene.scene_index + 1}`} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600">
            <VideoIcon className="w-8 h-8" />
          </div>
        )}
      </div>
      
      {/* Prompt Preview */}
      <p className="text-xs text-gray-400 line-clamp-2">
        {scene.background_prompt}
      </p>
      
      {/* Edit Button */}
      <button
        onClick={onEditClick}
        disabled={isEditing}
        className="w-full py-2 px-3 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isEditing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Editing...
          </>
        ) : (
          <>
            <Edit2 className="w-4 h-4" />
            Edit Scene
          </>
        )}
      </button>
    </div>
  );
};
```

**Acceptance Criteria:**
- ✅ Renders scene information correctly
- ✅ Shows edit count badge when edited
- ✅ Displays loading state during editing
- ✅ Matches luxury dark design system
- ✅ Responsive on mobile (full width)

---

### Task 10: Create EditScenePopup Component (2 hours)

**File:** `frontend/src/components/EditScenePopup.tsx` (NEW)

**Requirements:**
- [ ] Small centered overlay popup (400px width)
- [ ] Close button (X) in top-right
- [ ] Scene title display
- [ ] Label: "What would you like to change on this scene?"
- [ ] Textarea input (4 rows)
- [ ] Placeholder: "e.g., 'Make brighter and add golden tones'"
- [ ] Character counter (max 500 chars)
- [ ] Cost and time estimate display
- [ ] Cancel and "Edit Scene" buttons
- [ ] Disable submit if textarea empty
- [ ] Loading state on submit
- [ ] Close on cancel or successful submit

**Acceptance Criteria:**
- ✅ Opens as centered overlay
- ✅ Closes on X button or cancel
- ✅ Validates input (non-empty)
- ✅ Shows loading state on submit
- ✅ Matches luxury dark design
- ✅ Accessible (keyboard nav, focus trap)

---

### Task 11: Create SceneSidebar Component (2-3 hours)

**File:** `frontend/src/components/SceneSidebar.tsx` (NEW)

**Requirements:**
- [ ] Container for scene cards (right sidebar, 30% width)
- [ ] Header: "Scenes" with scene count
- [ ] Scrollable scene list
- [ ] Manage EditScenePopup state (which scene is being edited)
- [ ] Handle edit submission
- [ ] Refresh scenes after successful edit
- [ ] Show "Editing..." state on correct scene card

**Acceptance Criteria:**
- ✅ Renders all scenes in scrollable list
- ✅ Opens popup when edit button clicked
- ✅ Submits edit request correctly
- ✅ Shows loading state during editing
- ✅ Refreshes scenes and video after edit
- ✅ Handles errors gracefully

---

### Task 12: Update VideoResults Page (3-4 hours)

**File:** `frontend/src/pages/VideoResults.tsx` (UPDATE)

**Requirements:**
- [ ] Restructure layout to 70/30 split (video player / scene sidebar)
- [ ] Add SceneSidebar component to right side
- [ ] Add loading overlay on video player during editing
- [ ] Implement video reload after edit completes
- [ ] Show success toast notification after edit
- [ ] Update document title to include "Edit"
- [ ] Maintain existing functionality (download, stats, etc.)

**Updated Layout Structure:**
```tsx
export const VideoResults: React.FC = () => {
  const { campaignId } = useParams();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [isEditingScene, setIsEditingScene] = useState(false);
  const [videoKey, setVideoKey] = useState(0); // Force video reload
  
  const handleVideoUpdate = () => {
    // Called after successful edit
    loadCampaign(); // Reload campaign data
    setVideoKey(prev => prev + 1); // Force video player reload
    setIsEditingScene(false);
    
    // Show success toast
    toast.success('Scene edited successfully!');
  };
  
  return (
    <div className="video-results-page p-6">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* LEFT: Video Player (70%) */}
        <div className="flex-1 lg:w-2/3 space-y-4">
          <div className="relative">
            <VideoPlayer
              key={videoKey} // Force reload
              videoUrl={videoUrl}
              className="w-full"
            />
            
            {/* Loading Overlay During Edit */}
            {isEditingScene && (
              <div className="absolute inset-0 bg-black/80 flex flex-col items-center justify-center rounded-lg">
                <Loader2 className="w-12 h-12 text-gold-500 animate-spin mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">
                  Editing Scene...
                </h3>
                <p className="text-gray-400">
                  Modifying prompt and regenerating
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  This will take ~3 minutes
                </p>
              </div>
            )}
          </div>
        </div>
        
        {/* RIGHT: Scene Sidebar (30%) */}
        <SceneSidebar
          campaignId={campaignId}
          onVideoUpdate={handleVideoUpdate}
        />
      </div>
    </div>
  );
};
```

**Acceptance Criteria:**
- ✅ Layout is 70/30 split on desktop
- ✅ Stacks vertically on mobile
- ✅ Video player shows loading overlay during editing
- ✅ Video reloads automatically after edit
- ✅ Success notification shows after edit
- ✅ All existing functionality preserved
- ✅ Responsive design works on all screen sizes

---

### Task 13: Add API Client Methods (30 minutes)

**File:** `frontend/src/services/api.ts` (UPDATE)

**Requirements:**
- [ ] Add editing endpoints to API client

```typescript
export const editing = {
  getScenes: (campaignId: string, variationIndex: number = 0) =>
    api.get(`/api/campaigns/${campaignId}/scenes`, {
      params: { variation_index: variationIndex }
    }),
  
  editScene: (campaignId: string, sceneIndex: number, editPrompt: string) =>
    api.post(`/api/campaigns/${campaignId}/scenes/${sceneIndex}/edit`, {
      edit_prompt: editPrompt
    }),
  
  getEditHistory: (campaignId: string) =>
    api.get(`/api/campaigns/${campaignId}/edit-history`)
};
```

---

### Task 14: Add TypeScript Types (30 minutes)

**File:** `frontend/src/types/index.ts` (UPDATE)

**Requirements:**
- [ ] Add Scene interface
- [ ] Add EditSceneRequest interface
- [ ] Add EditSceneResponse interface
- [ ] Add EditHistoryRecord interface

```typescript
export interface Scene {
  scene_index: number;
  scene_id: number;
  role: string;
  duration: number;
  background_prompt: string;
  video_url: string;
  thumbnail_url?: string;
  edit_count: number;
  last_edited_at?: string;
}

export interface EditSceneRequest {
  edit_prompt: string;
}

export interface EditSceneResponse {
  job_id: string;
  estimated_cost: number;
  estimated_duration_seconds: number;
  message: string;
}

export interface EditHistoryRecord {
  edit_id: string;
  timestamp: string;
  scene_index: number;
  edit_prompt: string;
  changes_summary?: string;
  cost: number;
  duration_seconds: number;
}
```

---

## Implementation Phases

### Phase 1: Backend Foundation (8-10 hours)

**Goal:** Complete backend infrastructure for editing

**Tasks:**
- [x] Task 1: Create EditService (2-3 hours)
- [x] Task 2: Create SceneEditPipeline (4-5 hours)
- [x] Task 3: Add S3 Helper Functions (30 minutes)
- [x] Task 5: Update Worker (1 hour)
- [x] Task 7: Run Database Migration (15 minutes)

**Testing:**
- [ ] Unit test EditService prompt modification
- [ ] Integration test SceneEditPipeline end-to-end
- [ ] Verify S3 URL construction
- [ ] Test job enqueueing and execution

**Acceptance Criteria:**
- ✅ EditService successfully modifies prompts
- ✅ SceneEditPipeline completes full edit flow
- ✅ Scene video replaced in S3 correctly
- ✅ Final video re-rendered and uploaded
- ✅ Database updated with edit history
- ✅ All temporary files cleaned up

---

### Phase 2: API Layer (3-4 hours)

**Goal:** Complete REST API endpoints for editing

**Tasks:**
- [x] Task 4: Create API Endpoints (3-4 hours)
- [x] Task 6: Update Main App Router (15 minutes)

**Testing:**
- [ ] Test GET /api/campaigns/{id}/scenes endpoint
- [ ] Test POST /api/campaigns/{id}/scenes/{idx}/edit endpoint
- [ ] Test GET /api/campaigns/{id}/edit-history endpoint
- [ ] Verify ownership checks work
- [ ] Test error cases (invalid scene index, unauthorized, etc.)

**Acceptance Criteria:**
- ✅ All 3 endpoints return correct responses
- ✅ Ownership verification works
- ✅ Job enqueueing successful
- ✅ Proper error handling and status codes
- ✅ Swagger docs updated

---

### Phase 3: Frontend Components (8-10 hours)

**Goal:** Complete UI components for editing

**Tasks:**
- [x] Task 8: Create useSceneEditing Hook (2 hours)
- [x] Task 9: Create SceneCard Component (2 hours)
- [x] Task 10: Create EditScenePopup Component (2 hours)
- [x] Task 11: Create SceneSidebar Component (2-3 hours)
- [x] Task 13: Add API Client Methods (30 minutes)
- [x] Task 14: Add TypeScript Types (30 minutes)

**Testing:**
- [ ] Test useSceneEditing hook state management
- [ ] Test SceneCard rendering and interactions
- [ ] Test EditScenePopup form validation
- [ ] Test SceneSidebar scene list and editing flow
- [ ] Test API integration (mock responses)

**Acceptance Criteria:**
- ✅ All components render correctly
- ✅ Edit popup opens and closes properly
- ✅ Form validation works
- ✅ Loading states display correctly
- ✅ Error handling works
- ✅ TypeScript compiles without errors

---

### Phase 4: VideoResults Integration (3-4 hours)

**Goal:** Integrate editing into video results page

**Tasks:**
- [x] Task 12: Update VideoResults Page (3-4 hours)

**Testing:**
- [ ] Test layout on desktop (70/30 split)
- [ ] Test layout on mobile (stacked)
- [ ] Test video reload after edit
- [ ] Test loading overlay display
- [ ] Test success notifications
- [ ] Test error scenarios

**Acceptance Criteria:**
- ✅ Layout looks good on all screen sizes
- ✅ Editing flow works end-to-end
- ✅ Video updates automatically
- ✅ Loading states work correctly
- ✅ All existing functionality preserved
- ✅ No console errors or warnings

---

### Phase 5: End-to-End Testing (3-4 hours)

**Goal:** Full integration testing and bug fixes

**Test Scenarios:**
1. **Happy Path:**
   - Load campaign → See scenes → Click edit → Enter prompt → Submit → Wait → Video updates

2. **Error Cases:**
   - Invalid scene index
   - Empty edit prompt
   - Network failure during edit
   - Job timeout
   - Unauthorized access

3. **Edge Cases:**
   - Very long edit prompts (500+ chars)
   - Special characters in prompts
   - Multiple rapid edits
   - Editing while another edit in progress

**Testing Checklist:**
- [ ] Complete edit flow (3+ successful edits)
- [ ] Test all error scenarios
- [ ] Test on different screen sizes
- [ ] Test with slow network (throttling)
- [ ] Test with multiple concurrent users
- [ ] Verify S3 storage structure correct
- [ ] Verify database updates correct
- [ ] Check for memory leaks
- [ ] Verify no console errors/warnings
- [ ] Test accessibility (keyboard navigation)

---

### Phase 6: Polish & Documentation (2-3 hours)

**Goal:** Final polish and documentation

**Tasks:**
- [ ] Code review and cleanup
- [ ] Add inline code comments
- [ ] Update API documentation
- [ ] Create user-facing documentation
- [ ] Add logging for debugging
- [ ] Optimize performance (if needed)

**Deliverables:**
- [ ] Code quality: ESLint/Prettier passing
- [ ] TypeScript: No type errors
- [ ] Documentation: API endpoints documented
- [ ] User guide: How to edit scenes
- [ ] Deployment notes: Environment variables, migration steps

---

## Testing Strategy

### Unit Tests

**Backend:**
```python
# tests/test_edit_service.py
def test_modify_scene_prompt_brightening():
    """Test prompt modification for brightening request."""
    service = EditService(api_key="test")
    result = await service.modify_scene_prompt(
        original_prompt="Dark moody perfume scene",
        edit_instruction="Make brighter",
        style_spec={},
        scene_role="showcase",
        perfume_name="Test"
    )
    assert "bright" in result['modified_prompt'].lower()
    assert result['changes_summary'] is not None
```

**Frontend:**
```typescript
// tests/useSceneEditing.test.ts
describe('useSceneEditing', () => {
  it('loads scenes successfully', async () => {
    const { result } = renderHook(() => useSceneEditing());
    
    await act(async () => {
      await result.current.loadScenes('campaign-123');
    });
    
    expect(result.current.scenes).toHaveLength(4);
    expect(result.current.isLoading).toBe(false);
  });
});
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All Phase 1-6 tasks completed
- [ ] All tests passing (unit + integration + E2E)
- [ ] Code reviewed and approved
- [ ] TypeScript compiles without errors
- [ ] ESLint/Prettier checks pass
- [ ] No console errors or warnings
- [ ] Performance tested (edit completes <5 min)

### Database Migration

- [ ] Create backup of production database
- [ ] Run migration on staging: `alembic upgrade head`
- [ ] Verify migration successful (check campaigns table)
- [ ] Test JSONB operations on staging
- [ ] Document rollback steps

### Backend Deployment

- [ ] Deploy backend to Railway
- [ ] Verify environment variables set
- [ ] Restart API containers
- [ ] Restart worker containers
- [ ] Verify health endpoints

### Frontend Deployment

- [ ] Build frontend: `npm run build`
- [ ] Deploy to Vercel
- [ ] Verify API URL environment variable correct
- [ ] Test production build locally first
- [ ] Clear CDN cache if needed

### Post-Deployment Verification

- [ ] Test edit flow on production
- [ ] Verify S3 uploads working
- [ ] Check RQ worker logs for errors
- [ ] Monitor database performance
- [ ] Verify costs tracking correctly
- [ ] Test on multiple devices/browsers

---

## Cost Analysis

### Per Edit Operation

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SERVICE                    COST      TIME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM Prompt Modification    $0.01     2s
Video Regeneration         $0.20     180s
S3 Download (4 scenes)     $0.001    10s
FFmpeg Re-rendering        $0.00     45s
S3 Upload (final video)    $0.001    10s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                      ~$0.21    ~4min
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Monthly Estimates

**Scenario 1: 100 users, 2 edits/campaign**
- 100 users × 2 campaigns/month = 200 campaigns
- 200 campaigns × 2 edits = 400 edits
- 400 edits × $0.21 = **$84/month**

**Scenario 2: 500 users, 3 edits/campaign**
- 500 users × 2 campaigns/month = 1000 campaigns
- 1000 campaigns × 3 edits = 3000 edits
- 3000 edits × $0.21 = **$630/month**

---

## Success Metrics

### Technical Metrics

- **Edit Success Rate:** >95% of edits complete successfully
- **Edit Time:** <5 minutes per scene edit
- **Cost Accuracy:** Within ±5% of estimate ($0.21)
- **Error Rate:** <5% of edit requests fail

### User Experience Metrics

- **Time to Edit:** User completes edit in <30 seconds (input prompt)
- **Satisfaction:** Edited scene matches user's expectation >80% of time
- **Retention:** Users who edit are 2× more likely to return
- **Usage:** 30%+ of campaigns receive at least 1 edit

### Business Metrics

- **Engagement:** Average edits per campaign: 2-3
- **Revenue:** Edit feature increases user LTV by 40%
- **Cost Control:** Edit costs stay under $0.25 per operation

---

## Timeline Summary

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1: Backend Foundation | 8-10 hours | EditService, Pipeline, S3 utils, Worker, Migration |
| Phase 2: API Layer | 3-4 hours | 3 API endpoints, Router setup |
| Phase 3: Frontend Components | 8-10 hours | Hook, SceneCard, Popup, Sidebar, Types |
| Phase 4: VideoResults Integration | 3-4 hours | Layout update, Video reload, Loading states |
| Phase 5: E2E Testing | 3-4 hours | Integration testing, Bug fixes |
| Phase 6: Polish & Docs | 2-3 hours | Code review, Documentation, Final polish |
| **TOTAL** | **27-35 hours** | **~3.5-4.5 days** |

---

**This comprehensive documentation provides everything needed to implement the AI scene editing feature. Each task has clear requirements, acceptance criteria, and implementation details. Ready to start implementation!** 🚀

