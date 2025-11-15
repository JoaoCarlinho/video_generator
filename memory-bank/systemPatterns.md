# System Patterns — AI Ad Video Generator

**Architecture, design patterns, component relationships**

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

### Scene Generation Flow

```
1. Planning Phase
   Brief + Brand → GPT-4o-mini → Scenes + Style Spec

2. Asset Preparation
   Product Image → rembg → Masked PNG → S3

3. Parallel Generation (KEY OPTIMIZATION - All within single worker job)
   Scene 1 → Wān API → Video 1 ┐
   Scene 2 → Wān API → Video 2 ├→ All API calls concurrent (4x faster)
   Scene 3 → Wān API → Video 3 │  Using asyncio.gather()
   Scene 4 → Wān API → Video 4 ┘

   Note: This is I/O-bound (waiting for API responses)
         Worker sends all requests → waits → receives all responses
         NOT multi-processing or threading, just async HTTP calls

4. Compositing
   Video 1 + Product PNG → Composited Video 1
   Video 2 + Product PNG → Composited Video 2
   ...

5. Enhancement
   Composited Videos → Add Text Overlays → Final Scenes

6. Rendering
   Final Scenes + Music → Master Video (9:16)
   Master Video → Multi-Aspect → [9:16, 1:1, 16:9]
```

**Why This Parallelism Works:**
- Replicate API calls are I/O-bound (network waiting)
- Worker isn't CPU-processing while waiting for API
- Can issue multiple HTTP requests concurrently
- Each API processes independently on Replicate's servers
- Worker collects all results when ready

---

## Component Relationships

### Backend Services

```
ScenePlanner
  └─> Creates: Scene objects, StyleSpec
  └─> Uses: OpenAI API
  └─> Output: JSON structures

ProductExtractor
  └─> Input: User-uploaded image
  └─> Uses: rembg library
  └─> Output: Masked PNG (S3 URL)

VideoGenerator
  └─> Input: Scene + StyleSpec
  └─> Uses: Replicate Wān model
  └─> Output: Background video (S3 URL)

Compositor
  └─> Input: Background video + Product PNG + Scene config
  └─> Uses: OpenCV + PIL
  └─> Output: Composited video (S3 URL)

TextOverlayRenderer
  └─> Input: Video + Overlay config + Brand
  └─> Uses: FFmpeg drawtext
  └─> Output: Video with text (S3 URL)

AudioEngine
  └─> Input: Mood + Duration
  └─> Uses: Replicate MusicGen
  └─> Output: Music track (S3 URL)

Renderer
  └─> Input: Scene videos + Audio
  └─> Uses: FFmpeg concat + mux
  └─> Output: Final videos [9:16, 1:1, 16:9] (S3 URLs)
```

**Dependency Direction:** Always forward, no cycles.

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

**Last Updated:** November 14, 2025

