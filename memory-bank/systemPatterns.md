# System Patterns — AI Ad Video Generator

**Architecture, design patterns, component relationships**

---

## Database Schema (Phase 2 B2B Transformation)

### New B2B Schema (Phase 2)

**3-Tier Hierarchy:**
```
auth.users (Supabase Auth)
  └── brands (1:1 relationship - one user = one brand)
       ├── perfumes (1:many - many perfumes per brand)
       │    └── campaigns (1:many - many campaigns per perfume)
       └── campaigns (1:many - campaigns also reference brand_id)
```

**Tables:**

**brands:**
- `brand_id` (UUID, PK)
- `user_id` (UUID, FK → auth.users, UNIQUE, CASCADE DELETE)
- `brand_name` (VARCHAR(100), UNIQUE)
- `brand_logo_url` (VARCHAR(500))
- `brand_guidelines_url` (VARCHAR(500))
- `onboarding_completed` (BOOLEAN, default false)
- Indexes: user_id, onboarding_completed, brand_name (unique)

**perfumes:**
- `perfume_id` (UUID, PK)
- `brand_id` (UUID, FK → brands, CASCADE DELETE)
- `perfume_name` (VARCHAR(200))
- `perfume_gender` (VARCHAR(20), CHECK: masculine/feminine/unisex)
- `front_image_url` (VARCHAR(500), REQUIRED)
- `back_image_url`, `top_image_url`, `left_image_url`, `right_image_url` (optional)
- Unique constraint: (brand_id, perfume_name)
- Indexes: brand_id, perfume_gender

**campaigns:**
- `campaign_id` (UUID, PK)
- `perfume_id` (UUID, FK → perfumes, CASCADE DELETE)
- `brand_id` (UUID, FK → brands, CASCADE DELETE)
- `campaign_name` (VARCHAR(200))
- `creative_prompt` (TEXT)
- `selected_style` (VARCHAR(50), CHECK: gold_luxe/dark_elegance/romantic_floral)
- `target_duration` (INTEGER, CHECK: 15-60)
- `num_variations` (INTEGER, CHECK: 1-3, default 1)
- `status` (VARCHAR(50))
- `campaign_json` (JSONB) - All generation data
- Indexes: perfume_id, brand_id, status, created_at

**Key Constraints:**
- 1:1 User-Brand relationship (enforced by UNIQUE on user_id)
- Cascade delete: Brand → Perfumes → Campaigns
- CHECK constraints: gender, style, duration, variations
- UNIQUE constraints: brand_name, (brand_id, perfume_name)

**Migration:** `008_create_b2b_schema.py` (applied Nov 18, 2025)

**Legacy:** `projects` table kept temporarily (DEPRECATED) for backward compatibility. Will be removed in Phase 3-4.

---

## High-Level Architecture

```
┌─────────────┐
│   Browser   │
└─────┬───────┘
      │ HTTPS
      ▼
┌─────────────────────────┐
│   Vercel (Frontend)     │
│   React + TypeScript    │
└─────────┬───────────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌──────────────────┐
│Supabase │ │  Railway Backend │
│Auth+DB  │ │  FastAPI + RQ    │
└─────────┘ └────────┬─────────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
    ┌────────┐ ┌─────────┐ ┌─────┐
    │OpenAI  │ │Replicate│ │ S3  │
    │GPT-4o  │ │Wān+Music│ │Store│
    └────────┘ └─────────┘ └─────┘
```

---

## Core Design Patterns

### 1. Single Source of Truth: AdProject JSON

**Pattern:** All video state lives in one JSON object.

```json
{
  "projectId": "uuid",
  "brand": {...},
  "productAsset": {...},
  "style": {...},
  "scenes": [...],
  "renderStatus": {...}
}
```

**Benefits:**
- Easy to serialize/deserialize
- Simple to version control
- Enables deterministic regeneration
- Perfect for editing (modify JSON, re-render)
- JSONB in Supabase = no migrations needed

**Used by:**
- Scene planner (creates initial JSON)
- Generator services (read scenes to generate)
- Editor (modifies JSON, triggers regen)
- API (stores/retrieves from database)

---

### 2. Service Layer Isolation

**Pattern:** Each service is completely independent.

```python
# Each service has ONE job
class ScenePlanner:
    async def plan_scenes(brief, brand, duration) -> List[Scene]
    
class VideoGenerator:
    async def generate_scene_background(scene, style) -> str
    
class Compositor:
    async def composite_product(bg_url, product_url, scene) -> str
```

**Benefits:**
- Test each service independently
- Reuse services for editing (regenerate single scene)
- Easy to swap implementations (try different AI models)
- Clear separation of concerns

**Communication:**
- Services don't call each other
- Pipeline orchestrates all services
- Pass URLs (S3) not file objects

---

### 3. Background Job Pipeline

**Pattern:** Long-running tasks in worker process.

```
User Request → API enqueues job → Returns immediately
                     ↓
              RQ Worker picks up
                     ↓
              Runs async pipeline
                     ↓
              Updates database
                     ↓
              User polls for status
```

**Benefits:**
- API stays responsive
- User sees real-time progress
- Can retry failed jobs
- Easy to scale (add more workers)

**Implementation:**
- Redis Queue (RQ) for job management
- Single worker initially (sufficient for 10-100 users)
- Async/await for parallel scene generation

**Important: Worker vs Parallelism**

Many people confuse these two concepts:

**Single Worker = One Job at a Time (User-level Parallelism)**
```python
# Worker processes ONE user's video
# If User B submits while User A generating → User B waits in queue
```

**But Within Each Job = Parallel Scene Generation (Scene-level Parallelism)**
```python
# Inside one job, generate all scenes concurrently
tasks = [generate_scene(s) for s in scenes]  # 4 API calls
videos = await asyncio.gather(*tasks)        # All at once

# Sequential: 3min × 4 = 12 minutes total
# Parallel:   max(3min, 3min, 3min, 3min) = 3 minutes total
# 4x faster!
```

**When to Add More Workers:**
- Single worker: 6 videos/hour (10-20 users)
- Queue depth >5: Add worker 2
- Queue depth >10: Add worker 3
- Each worker costs ~$10/month

---

### 4. Progressive Enhancement

**Pattern:** Build core features first, add enhancements later.

**MVP (Core):**
```
Brief → Scenes → Videos → Composite → Render
```

**Post-MVP (Enhancements):**
```
Brief → Scenes → Videos → Composite → Render
          ↓
       [EDIT] ← User changes scene
          ↓
    Regenerate only that scene
          ↓
       Re-render final
```

**Why This Works:**
- Services already isolated (no changes needed)
- JSON already supports editing history
- Database schema flexible (JSONB)
- Frontend components reusable

---

## Data Flow Patterns

### Scene Generation Flow (Updated for Veo S3 Migration)

**CURRENT PIPELINE (7 Steps - Pre-Veo):**
```
1. Planning Phase
   Brief + Brand → GPT-4o-mini → Scenes + Style Spec

2. Asset Preparation
   Product Image → rembg → Masked PNG → S3

3. Parallel Generation (KEY OPTIMIZATION - All within single worker job)
   Scene 1 → ByteDance API → Video 1 ┐
   Scene 2 → ByteDance API → Video 2 ├→ All API calls concurrent (4x faster)
   Scene 3 → ByteDance API → Video 3 │  Using asyncio.gather()
   Scene 4 → ByteDance API → Video 4 ┘

4. Compositing (TO BE REMOVED)
   Video 1 + Product PNG → OpenCV frame-by-frame overlay
   Video 2 + Product PNG → OpenCV frame-by-frame overlay
   ...

5. Text Overlay (TO BE REMOVED)
   Videos → FFmpeg drawtext → Text overlaid

6. Audio Generation
   MusicGen → Luxury ambient music

7. Final Rendering
   Scenes + Music → TikTok vertical (9:16)
```

**NEW PIPELINE (5 Steps - Post-Veo Migration):**
```
1. Planning Phase (Enhanced)
   Brief + Brand → GPT-4o-mini with Veo S3 prompts → Scenes with embedded instructions
   - Cinematic vocabulary (dolly shots, rack focus, volumetric lighting)
   - Text instructions embedded in prompts
   - Product/logo flags per scene

2. Asset Preparation (Optional)
   Product Image → Optional preprocessing for Veo

3. Parallel Generation (Veo S3 Image-to-Video)
   Scene 1 + Product Ref + Text Instructions → Veo S3 → Video 1 ┐
   Scene 2 + Logo Ref + Text Instructions → Veo S3 → Video 2 ├→ Concurrent (4x faster)
   Scene 3 + Instructions → Veo S3 → Video 3                  │  asyncio.gather()
   Scene 4 + Product + Logo → Veo S3 → Video 4                ┘
   
   Note: Veo S3 handles product, text, and cinematography natively
         No manual compositing or text overlay needed
         Each scene can have different image references

4. Audio Generation
   MusicGen → Luxury ambient music

5. Final Rendering
   Scenes + Music → TikTok vertical (9:16)
```

**Key Changes:**
- ❌ Removed Steps 4 & 5 (Compositing + Text Overlay)
- ✅ Enhanced Step 1 (Scene Planning with Veo prompts)
- ✅ Updated Step 3 (Veo S3 image-to-video with references)
- ⚡ 30% faster generation (fewer steps)
- 🎨 Better quality (natural integration vs manual overlay)

**Why This Parallelism Still Works:**
- Veo API calls are I/O-bound (network waiting)
- Worker sends all scene requests concurrently
- Each scene can have different image references (product/logo)
- asyncio.gather() handles parallel async calls
- Worker collects all results when ready

---

## Component Relationships

### Backend Services (Updated for Veo S3 Migration)

```
ScenePlanner (Enhanced for Veo S3)
  └─> Creates: Scene objects with Veo-enhanced prompts, StyleSpec
  └─> Uses: OpenAI API (GPT-4o-mini with Veo S3 system prompt)
  └─> Output: Scenes with cinematic vocabulary + text/product instructions
  └─> NEW: Embeds text overlay instructions in prompts (not rendered separately)
  └─> NEW: Includes cinematography details (dolly shots, rack focus, volumetric lighting)

ProductExtractor
  └─> Input: Perfume front image URL (from database)
  └─> Uses: rembg library
  └─> Output: Masked PNG (S3 URL) - Optional preprocessing for Veo
  └─> Status: May be simplified/removed in future (Veo can handle raw images)

VideoGenerator (Updated for Veo S3)
  └─> Input: Scene + StyleSpec + Product/Logo Images (optional)
  └─> Uses: Google Veo S3 model (image-to-video)
  └─> NEW: Accepts image references per scene (product, logo)
  └─> NEW: Text embedded by Veo (not overlaid)
  └─> Output: Complete scene video with product + text integrated (S3 URL)

Compositor (DEPRECATED - TO BE REMOVED)
  └─> Status: No longer used after Veo S3 migration
  └─> Reason: Veo S3 handles product integration naturally
  └─> Code: Kept in codebase for reference, not called in pipeline

TextOverlayRenderer (DEPRECATED - TO BE REMOVED)
  └─> Status: No longer used after Veo S3 migration
  └─> Reason: Veo S3 generates text in scene (not overlaid)
  └─> Schema: TextOverlay repurposed for Veo instruction generation

AudioEngine
  └─> Input: Duration + Gender (masculine/feminine/unisex)
  └─> Uses: Replicate MusicGen
  └─> Method: generate_perfume_background_music() (perfume-specific)
  └─> Prompt: Luxury ambient cinematic with gender-aware descriptors
  └─> Output: Music track (local path)
  └─> Status: Unchanged

Renderer
  └─> Input: Scene videos (from Veo) + Audio
  └─> Uses: FFmpeg concat + mux
  └─> Output: Final TikTok vertical video (9:16 only) (local path as string)
  └─> Status: Unchanged
```

**Service Evolution:**
- ✅ ScenePlanner: Enhanced with Veo prompting
- ✅ VideoGenerator: Updated to support Veo S3 API
- ❌ Compositor: Deprecated (Veo handles product integration)
- ❌ TextOverlayRenderer: Deprecated (Veo generates text in scene)
- ✅ AudioEngine: Unchanged
- ✅ Renderer: Unchanged

**Dependency Direction:** Always forward, no cycles. Simplified with fewer services.

---

### Frontend Components

```
Pages (React Router)
├─ Landing.tsx → Hero, features, CTAs
├─ Login.tsx → Auth (Supabase)
├─ Create.tsx → ProjectForm
├─ Project.tsx → ProgressTracker + VideoPlayer
└─ Dashboard.tsx → ProjectCard list

Components (Reusable)
├─ ProjectForm.tsx → Create new project
├─ ProgressTracker.tsx → Show generation status
├─ VideoPlayer.tsx → Display result
└─ ProjectCard.tsx → Project list item

Contexts (State)
└─ AuthContext.tsx → Supabase auth state
```

**State Management:**
- Auth: Supabase context
- Projects: API calls via axios
- No global state manager (not needed for MVP)

---

## Key Patterns for Post-MVP

### 1. Scene Regeneration Pattern

```python
# MVP: Generate all scenes
await generate_all_scenes(scenes, style_spec)

# Post-MVP: Regenerate single scene
scene = find_scene(project, scene_id)
scene.backgroundPrompt += ", brighter lighting"
new_video = await generator.generate_scene_background(scene, style_spec)
update_scene(project_id, scene_id, {"sceneVideoUrl": new_video})
```

**Why it works:** Services already isolated, just call one service.

### 2. Edit Operation Pattern

```python
# User says: "Make the showcase scene brighter"
# LLM converts to operation:
{
  "operation": "regenerate_scene",
  "sceneId": "scene_2",
  "promptAdditions": "brighter lighting, more contrast"
}

# Backend applies:
scene = get_scene(project_id, "scene_2")
scene.backgroundPrompt += ", brighter lighting, more contrast"
await regenerate_scene(project_id, scene)
```

**Why it works:** JSON structure already supports modifications.

### 3. A/B Variation Pattern

```python
# Clone project
variation = clone_project(base_project)
variation.variation = {"isVariation": True, "parentProjectId": base_id}

# Modify specific elements
variation.scenes[0].overlay.text = "Alternative Hook"
variation.scenes[-1].overlay.text = "Shop Now"  # Different CTA

# Regenerate ONLY scenes with changes
await regenerate_scenes(variation, [scenes[0], scenes[-1]])
```

**Why it works:** Style Spec and product stay same, only text changes.

---

## Cost Optimization Patterns

### 1. Parallel Generation
```
Sequential: Scene1 (3min) + Scene2 (3min) + Scene3 (3min) = 9 min
Parallel: max(3min, 3min, 3min) = 3 min total (3x faster)
```

### 2. Aggressive Caching
```python
# Cache Style Spec (reuse for variations)
cache_key = f"style:{hash(brief + brand)}"
style_spec = cache.get(cache_key) or generate_style_spec(...)

# Cache Product Extraction (reuse across edits)
cache_key = f"product:{image_checksum}"
masked_png = cache.get(cache_key) or extract_product(...)
```

### 3. Smart Regeneration
```
Edit text overlay → No regeneration needed (FFmpeg only)
Edit scene prompt → Regenerate only that scene
Edit product → Regenerate ALL scenes (but rare)
```

---

## Scalability Patterns

### Current (10-100 Users)
- Single RQ worker
- Supabase free tier
- S3 standard storage
- Sequential processing per user

### Future (1000+ Users)
- Multiple RQ workers (horizontal scaling)
- Supabase paid tier or dedicated Postgres
- S3 with CloudFront CDN
- Priority queue (paid users first)

**Key:** Architecture supports both without refactor.

---

## Error Handling Patterns

### Graceful Degradation
```python
try:
    masked_png = rembg.remove(image)
except:
    masked_png = image  # Use original if extraction fails
    
try:
    video = await waan_model.generate(prompt)
except:
    video = create_black_placeholder()  # Fallback video
```

### Progressive Failure
```python
# If Scene 2 fails, continue with Scene 1, 3, 4
results = await asyncio.gather(*tasks, return_exceptions=True)
successful = [r for r in results if not isinstance(r, Exception)]
```

### Cost Tracking Even on Failure
```python
try:
    total_cost += run_pipeline()
except Exception as e:
    update_project(id, {"status": "FAILED", "cost": total_cost})
```

---

## Testing Patterns

### Service-Level Tests
```python
# Test each service independently
async def test_scene_planner():
    scenes = await planner.plan_scenes("test brief", brand, 30)
    assert len(scenes) >= 3
    assert scenes[0].role == "hook"
```

### Integration Tests
```python
# Test full pipeline
async def test_full_pipeline():
    result = await generate_full_pipeline(test_project_id)
    assert result.status == "COMPLETED"
    assert len(result.aspectExports) == 3
```

### Checkpoints
- After early testing (GO/NO-GO on extraction)
- After core services (all services work)
- After pipeline integration (end-to-end works)
- After UI integration (user can generate)

---

## Perfume-Specific Patterns (Phase 8)

### Grammar Validation Pattern
```python
# After scene planning, validate against perfume shot grammar
from app.services.perfume_grammar_loader import PerfumeGrammarLoader
grammar_loader = PerfumeGrammarLoader()
is_valid, violations = grammar_loader.validate_scene_plan(plan_scenes_list)

if not is_valid:
    logger.warning(f"⚠️ Grammar violations detected: {violations}")
else:
    logger.info("✅ Scene plan validated against perfume shot grammar")
```

**Why:** Ensures all scenes follow perfume shot grammar rules. Scene planner already has 3-retry system with fallback templates, so violations are rare. This validation is for observability.

### Perfume Name Extraction Pattern
```python
# Extract perfume_name from ad_project_json or fallback to brand name
perfume_name = None
if project.ad_project_json and isinstance(project.ad_project_json, dict):
    perfume_name = project.ad_project_json.get("perfume_name")
if not perfume_name:
    perfume_name = ad_project.brand.get('name', 'Perfume')
    
# Store for future use
project.ad_project_json['perfume_name'] = perfume_name
```

**Why:** Perfume name is required for perfume-specific scene planning. Stored in JSON for future use (Phase 9 will add database field).

### TikTok Vertical Hardcoding Pattern
```python
# All rendering returns single string path (not dict)
final_video_path = await renderer.render_final_video(...)  # Returns str

# Pipeline stores as dict for backward compatibility
local_video_paths = {"9:16": final_video_path}
```

**Why:** Maintains backward compatibility with existing data structures while simplifying code (no multi-aspect logic).

---

## Multi-Variation Generation Pattern (Nov 18, 2025)

### Parallel Variation Processing

```python
# Key insight: Generate all variations concurrently, not sequentially
import asyncio

async def run():
    # Plan N different scene variations upfront
    scene_variations = await self._plan_scenes_variations(num_variations=3)
    # [[scene1_v1, scene2_v1], [scene1_v2, scene2_v2], [scene1_v3, scene2_v3]]
    
    # Process all variations IN PARALLEL
    tasks = [
        self._process_variation(scenes, var_idx, num_variations)
        for var_idx, scenes in enumerate(scene_variations)
    ]
    final_videos = await asyncio.gather(*tasks)
    # All 3 variations complete ~simultaneously = 5-7 min (not 15-21!)
```

**Why This Works:**
- Each variation is independent
- No shared state conflicts
- asyncio coordinates the waiting
- API requests happen concurrently (Replicate handles parallel requests)
- Worker isn't blocked (just awaiting)

### Variation Uniqueness Pattern

```python
# Each variation gets different "approach"
def _build_variation_prompt(variation_index):
    approaches = [
        "Cinematic: dramatic lighting, wide shots",
        "Minimal: clean aesthetic, macro shots",
        "Lifestyle: real-world moments, atmospheric"
    ]
    
    # Also use different seed for video generation
    seed = 1000 + variation_index  # 1000, 1001, 1002
    
    # Combine: different scenes + different seeds = visibly different videos
    return {
        "prompt": base_prompt + approaches[variation_index],
        "seed": seed
    }
```

**Why This Works:**
- Scene prompt variation creates different storylines
- Video seed variation creates different visual treatments
- Together = meaningful choice for user
- Not "completely different" (same brand/requirements maintained)

### Storage & Selection Pattern

```python
# Multi-variation storage pattern
if num_variations > 1:
    # Store as array
    local_video_paths["9:16"] = [
        "/path/to/variation_0.mp4",
        "/path/to/variation_1.mp4",
        "/path/to/variation_2.mp4"
    ]
else:
    # Store as string (backward compat)
    local_video_paths["9:16"] = "/path/to/video.mp4"

# After user selection
selected_index = 1  # User picked Option 2
selected_video = local_video_paths["9:16"][selected_index]

# After finalization (keep only selected)
# Delete unselected videos
# Upload selected to S3
# Keep only in final project
```

**Why This Works:**
- Flexible data structure (array or string)
- No database schema changes needed (JSONB)
- Selection preserved for audit trail
- Easy cleanup (delete unselected)

### Routing Pattern

```typescript
// Conditional routing based on variation count
if (project.num_variations === 1) {
    // Skip selection page entirely
    navigate(`/project/${projectId}`);  // → VideoResults
} else {
    // Show selection page
    navigate(`/project/${projectId}/select`);  // → VideoSelection
    // After selection:
    navigate(`/project/${projectId}`);  // → VideoResults
}
```

**Why This Works:**
- Better UX (no unnecessary pages)
- Single variation same as current flow
- Multi-variation adds selection page
- No breaking changes

### Preview Endpoint Pattern (Nov 18, 2025)

```python
# Preview endpoint supports variation selection
GET /api/local-generation/projects/{id}/preview?variation={0|1|2}

# Backend handles array vs string
if isinstance(video_paths, list):
    return video_paths[variation_index]  # Multi-variation
else:
    return video_paths  # Single video (ignores variation param)
```

**Why This Works:**
- Single endpoint serves all variations
- Query parameter selects which variation
- Backward compatible (single video still works)
- Frontend constructs URLs with variation index

---

## S3 Storage Patterns (Phase 2)

### Hierarchical Path Generation

**Pattern:** Path functions build hierarchical S3 structure
```python
# Brand level
brand_path = get_brand_s3_path(brand_id)  
# → "brands/{brand_id}/"

# Perfume level
perfume_path = get_perfume_s3_path(brand_id, perfume_id)
# → "brands/{brand_id}/perfumes/{perfume_id}/"

# Campaign level
campaign_path = get_campaign_s3_path(brand_id, perfume_id, campaign_id)
# → "brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"
```

**Benefits:**
- Clear hierarchy matches database structure
- Easy to navigate in S3 console
- Supports lifecycle policies via prefix filtering
- Enables brand-level operations (delete all brand data)

### S3 Tagging Pattern

**Pattern:** All uploads apply tags for lifecycle management
```python
# Brand assets (permanent)
tags = {
    "type": "brand_asset",
    "brand_id": brand_id,
    "lifecycle": "permanent"
}

# Draft videos (30-day lifecycle)
tags = {
    "type": "campaign_video",
    "subtype": "draft",
    "brand_id": brand_id,
    "perfume_id": perfume_id,
    "campaign_id": campaign_id,
    "variation_index": str(variation_index),
    "lifecycle": "30days"
}

# Final videos (90-day lifecycle)
tags = {
    "type": "campaign_video",
    "subtype": "final",
    "brand_id": brand_id,
    "perfume_id": perfume_id,
    "campaign_id": campaign_id,
    "variation_index": str(variation_index),
    "lifecycle": "90days"
}
```

**Tag Format:**
- URL-encoded string: `key1=value1&key2=value2`
- Applied via `Tagging` parameter in `put_object()`
- Used by lifecycle policy for automatic deletion

**Lifecycle Rules:**
- Draft videos: Delete after 30 days (tagged `subtype=draft`)
- Final videos: Delete after 90 days (tagged `subtype=final`)
- Brand assets: No lifecycle (permanent)
- Perfume images: No lifecycle (permanent)

### Upload Function Pattern

**Pattern:** Consistent function signatures across all upload types
```python
# Brand assets (file_content: bytes)
async def upload_brand_logo(brand_id, file_content, filename) -> dict

# Perfume images (file_content: bytes)
async def upload_perfume_image(brand_id, perfume_id, angle, file_content, filename) -> dict

# Campaign videos (file_path: str - local file)
async def upload_draft_video(brand_id, perfume_id, campaign_id, variation_index, scene_index, file_path) -> dict
async def upload_final_video(brand_id, perfume_id, campaign_id, variation_index, file_path) -> dict
```

**Return Format:**
```python
{
    "url": "https://bucket.s3.region.amazonaws.com/path",
    "s3_key": "brands/.../path",
    "size_bytes": 12345,
    "filename": "file.ext"
}
```

**Error Handling:**
- All functions raise `RuntimeError` on failure
- Comprehensive logging at each step
- Validation before upload (file types, sizes, indexes)

### Modern S3 Bucket Pattern

**Pattern:** No ACL support (modern buckets)
- Removed `ACL="public-read"` from all `put_object()` calls
- Bucket uses bucket policies for access control
- Files accessible via presigned URLs if needed

**Bucket Configuration:**
- **Name:** `genads-gauntlet`
- **Region:** `us-east-1`
- **ACL:** Disabled (modern bucket)
- **Lifecycle:** Applied via JSON policy file

---

**Last Updated:** November 18, 2025 (Phase 2 B2B SaaS - Phase 2 S3 Storage Refactor Complete)

