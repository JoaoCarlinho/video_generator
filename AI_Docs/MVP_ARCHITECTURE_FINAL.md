# MVP Architecture — AI Ad Video Generator
**Focus:** Generation Pipeline Only  
**Version:** 1.0 (MVP)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Landing Page │  │ Create Form  │  │ Progress View│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VERCEL (Frontend CDN)                         │
│                   React + Vite + TypeScript                      │
│              Tailwind CSS + shadcn/ui + Framer Motion           │
└─────────────────────────────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│   SUPABASE (Auth + DB)   │   │  RAILWAY (Backend API)   │
│  • User Authentication   │   │  • FastAPI (Python)      │
│  • Postgres Database     │   │  • RQ Worker (Jobs)      │
│  • Project Storage       │   │  • Redis Queue           │
└──────────────────────────┘   └──────────────────────────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        │                  │                  │
                        ▼                  ▼                  ▼
              ┌────────────────┐  ┌────────────────┐  ┌────────────┐
              │   OpenAI API   │  │ Replicate API  │  │  AWS S3    │
              │  • GPT-4o-mini │  │  • Wān (Video) │  │ • Videos   │
              │  • Planning    │  │  • MusicGen    │  │ • Images   │
              └────────────────┘  └────────────────┘  └────────────┘
```

---

## Data Flow (Complete User Journey)

```
[1] USER CREATES PROJECT
    ↓
    User fills form → Upload product image → Submit
    ↓
    POST /api/projects
    ↓
    • Save product image to S3
    • Create project in Supabase (status: PENDING)
    • Return project_id
    ↓
    POST /api/generation/projects/{project_id}/generate
    ↓
    • Enqueue job in Redis Queue
    • Return job_id
    ↓
    Frontend redirects to /project/{project_id}
    Frontend polls GET /api/projects/{project_id} every 2s

[2] RQ WORKER PICKS UP JOB
    ↓
    generate_full_pipeline(project_id) starts
    ↓
    
    STEP 1: EXTRACT PRODUCT (10%)
    ├─ Download product image from S3
    ├─ Remove background with rembg
    ├─ Upload masked PNG to S3
    └─ Update project: status="EXTRACTING_PRODUCT", progress=10
    
    STEP 2: PLAN SCENES (20%)
    ├─ Call OpenAI GPT-4o-mini
    ├─ Generate 3-5 scenes based on duration
    ├─ Generate Style Spec (lighting, mood, colors)
    └─ Update project: status="PLANNING", progress=20
    
    STEP 3: GENERATE SCENE BACKGROUNDS (30-60%)
    ├─ For each scene in parallel:
    │   ├─ Build prompt: scene.backgroundPrompt + style descriptors
    │   ├─ Call Replicate Wān model
    │   ├─ Download video
    │   └─ Upload to S3
    └─ Update progress: 30 → 40 → 50 → 60 (per scene)
    
    STEP 4: COMPOSITE PRODUCTS (65%)
    ├─ For each scene:
    │   ├─ If productUsage != "none":
    │   │   ├─ Download background video
    │   │   ├─ Download product PNG
    │   │   ├─ Use OpenCV + PIL to overlay product
    │   │   └─ Upload composited video to S3
    │   └─ Else: keep background video
    └─ Update project: status="COMPOSITING", progress=65
    
    STEP 5: ADD TEXT OVERLAYS (75%)
    ├─ For each scene:
    │   ├─ If overlay.text exists:
    │   │   ├─ Use FFmpeg drawtext filter
    │   │   ├─ Apply brand colors
    │   │   └─ Upload to S3
    │   └─ Else: keep video
    └─ Update project: status="ADDING_OVERLAYS", progress=75
    
    STEP 6: GENERATE MUSIC (80%)
    ├─ Call Replicate MusicGen
    ├─ Download and normalize audio
    ├─ Trim to exact duration
    └─ Upload to S3
    
    STEP 7: RENDER FINAL VIDEO (90%)
    ├─ Download all scene videos
    ├─ Concatenate with crossfade transitions
    ├─ Mux audio with video
    ├─ Render at 1080p 30fps
    └─ Upload master (9:16) to S3
    
    STEP 8: RENDER OTHER ASPECTS (95%)
    ├─ Generate 1:1 (center crop)
    ├─ Generate 16:9 (letterbox)
    └─ Upload all to S3
    
    STEP 9: COMPLETE (100%)
    ├─ Update project:
    │   ├─ status="COMPLETED"
    │   ├─ progress=100
    │   ├─ finalVideoUrl
    │   └─ aspectExports: [9:16, 1:1, 16:9]
    └─ Schedule deletion after 7 days

[3] USER VIEWS RESULT
    ↓
    Frontend receives status="COMPLETED"
    ↓
    Display video player with master video
    Show download buttons for all 3 aspects
```

---

## Core Architecture Decisions

### 1. Product Consistency Strategy

**Problem:** AI models generate inconsistent products (warped logos, wrong colors)

**Solution:** Background-Only Generation + Compositing

```
Traditional Approach (BAD):
  User Prompt: "Show hydrating serum bottle on gradient background"
  ↓
  AI Video Model generates everything
  ↓
  Result: Product looks different in every scene ❌

Our Approach (GOOD):
  1. Extract product from uploaded image (rembg)
  2. Generate background: "gradient background" (no product mention)
  3. Composite real product PNG onto background with OpenCV
  ↓
  Result: Product is pixel-perfect across all scenes ✓
```

### 2. Style Consistency System

**Problem:** AI generates scenes with varying aesthetics

**Solution:** Global Style Spec

```
Style Spec Generated Once:
{
  "lighting": "soft studio lighting, warm tones",
  "cameraStyle": "smooth panning, cinematic",
  "texture": "glossy, minimal",
  "mood": "fresh, uplifting",
  "colorPalette": ["#4dbac7", "#ffffff"],
  "grade": "warm shadows, teal highlights"
}

Applied to Every Scene:
  scene.backgroundPrompt + style.lighting + style.cameraStyle + style.mood
  ↓
  Result: All scenes feel cohesive ✓
```

### 3. Parallel Scene Generation

**Problem:** Sequential generation is slow (12+ minutes for 4 scenes)

**Solution:** Async parallel processing

```python
# Sequential (SLOW): 3 min × 4 scenes = 12 min total
for scene in scenes:
    video = await generate_scene(scene)

# Parallel (FAST): max(3 min) = 3 min total
tasks = [generate_scene(scene) for scene in scenes]
videos = await asyncio.gather(*tasks)
```

### 4. Queue-Based Job Processing

**Problem:** Video generation takes 8-10 minutes (too long for HTTP request)

**Solution:** Background jobs with Redis Queue

```
User Request → API enqueues job → Returns immediately
                     ↓
              RQ Worker picks up job
                     ↓
              Processes in background
                     ↓
              User polls for status
```

---

## Technology Stack

### Frontend
- **Framework:** React 18 + Vite + TypeScript
- **Styling:** Tailwind CSS + shadcn/ui
- **Animation:** Framer Motion
- **Auth:** Supabase Auth (@supabase/supabase-js)
- **API:** Axios
- **Video:** react-player
- **Upload:** react-dropzone
- **Forms:** react-hook-form

### Backend
- **Framework:** FastAPI (Python 3.11)
- **Database:** Supabase (Postgres)
- **Queue:** Redis + RQ
- **ORM:** SQLAlchemy
- **Storage:** AWS S3 (boto3)

### AI Services
- **Video:** Replicate API (Wān model: `minimax/video-01`)
- **Music:** Replicate API (MusicGen)
- **Planning:** OpenAI GPT-4o-mini
- **Extraction:** rembg (local)

### Processing
- **Compositing:** OpenCV + PIL
- **Rendering:** FFmpeg
- **Audio:** pydub

### Infrastructure
- **Frontend:** Vercel
- **Backend:** Railway (Web + Worker)
- **Database:** Supabase
- **Storage:** AWS S3
- **Queue:** Railway Redis

---

## Database Schema (Supabase)

### `projects` table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to auth.users |
| title | TEXT | Project name |
| ad_project_json | JSONB | Complete AdProject data |
| status | TEXT | PENDING / EXTRACTING_PRODUCT / PLANNING / GENERATING_SCENES / COMPOSITING / ADDING_OVERLAYS / GENERATING_AUDIO / RENDERING / COMPLETED / FAILED |
| progress | INTEGER | 0-100 |
| cost | DECIMAL | Total generation cost |
| error_message | TEXT | Error if failed |
| created_at | TIMESTAMPTZ | Creation time |
| updated_at | TIMESTAMPTZ | Last update |

**Indexes:**
- `idx_projects_user_id` on `user_id`
- `idx_projects_status` on `status`

---

## S3 Storage Structure

```
s3://adgen-videos-xxx/
├── projects/{project_id}/
│   ├── product/
│   │   ├── original.jpg
│   │   ├── masked.png
│   │   └── mask.png
│   ├── scenes/
│   │   ├── scene_1_bg.mp4
│   │   ├── scene_1_composited.mp4
│   │   ├── scene_1_overlay.mp4
│   │   ├── scene_2_bg.mp4
│   │   ├── scene_2_composited.mp4
│   │   └── ...
│   ├── audio/
│   │   └── background_music.mp3
│   └── outputs/
│       ├── final_9x16.mp4
│       ├── final_1x1.mp4
│       └── final_16x9.mp4
```

**Lifecycle Policy:**
- Delete all files in `/projects/{project_id}/` after 7 days

---

## API Endpoints

### Projects

**POST** `/api/projects`
- Create new project
- Body: FormData (brief, brandName, primaryColor, duration, productImage)
- Auth: Required
- Returns: `{ project_id, status }`

**GET** `/api/projects/{project_id}`
- Get project details and status
- Auth: Required
- Returns: Full project object

**GET** `/api/projects/user/all`
- List all user projects
- Auth: Required
- Returns: `[{ id, title, status, created_at, ... }]`

### Generation

**POST** `/api/generation/projects/{project_id}/generate`
- Start video generation
- Auth: Required
- Returns: `{ job_id }`

---

## Job Status Flow

```
PENDING
  ↓
EXTRACTING_PRODUCT (10%)
  ↓
PLANNING (20%)
  ↓
GENERATING_SCENES (30-60%)
  ↓
COMPOSITING (65%)
  ↓
ADDING_OVERLAYS (75%)
  ↓
GENERATING_AUDIO (80%)
  ↓
RENDERING (90%)
  ↓
COMPLETED (100%)

Any error → FAILED
```

---

## Service Responsibilities

### ScenePlanner
- Input: Brief, Brand, Duration
- Output: List[Scene], StyleSpec
- Uses: OpenAI GPT-4o-mini

### ProductExtractor
- Input: Product image path
- Output: Masked PNG, Mask PNG, Metadata
- Uses: rembg

### VideoGenerator
- Input: Scene, StyleSpec
- Output: Background video URL
- Uses: Replicate Wān model

### Compositor
- Input: Background video, Product PNG, Scene
- Output: Composited video URL
- Uses: OpenCV + PIL

### TextOverlayRenderer
- Input: Video, Overlay, Brand
- Output: Video with text overlay
- Uses: FFmpeg drawtext

### AudioEngine
- Input: Mood, Duration
- Output: Music URL
- Uses: Replicate MusicGen

### Renderer
- Input: Scene videos, Audio
- Output: Final videos (9:16, 1:1, 16:9)
- Uses: FFmpeg

---

## Performance Characteristics

### Generation Time
- **30-second video:** ~8 minutes
  - Planning: 10s
  - Product extraction: 20s
  - Scene generation: 4 scenes × 2min = 8min (parallel: ~2min)
  - Compositing: 4 scenes × 30s = 2min
  - Audio: 1min
  - Rendering: 2min
  - **Total: ~8 minutes**

### Cost Per Video (30s)
- Scene planning (GPT-4o-mini): $0.01
- 4 scene videos (Wān): ~$0.80
- Background music (MusicGen): ~$0.20
- Compositing (local): $0.00
- **Total: ~$1.01 per video**

### Scalability
- **10 users:** Single RQ worker sufficient
- **100 users:** 2-3 workers
- **1000+ users:** 10+ workers + CDN for videos

---

## Error Handling & Fallbacks

### Product Extraction Fails
→ Use original image without background removal

### Video Generation Fails
→ Retry once → If fails, use black placeholder video

### Compositing Fails
→ Use background video without product

### Text Overlay Fails
→ Skip text overlay for that scene

### Music Generation Fails
→ Use silent audio track

### Rendering Fails
→ Simplify FFmpeg command (no transitions)

**Goal:** Always produce a video, even if degraded quality

---

## Deployment Architecture

### Vercel (Frontend)
- Serves React SPA
- Global CDN
- Environment variables:
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
  - `VITE_API_URL`

### Railway (Backend)
- **Web Service:** FastAPI app
  - Handles API requests
  - Port 8000
- **Worker Service:** RQ worker
  - Processes background jobs
  - Same codebase, different command

### Supabase
- Postgres database
- User authentication
- Row-level security

### AWS S3
- Video storage
- Public read access for `/outputs/`
- Lifecycle: auto-delete after 7 days

---

## Security

### Authentication
- Supabase Auth with JWT tokens
- Google OAuth + Email/Password
- Token passed in Authorization header

### API Protection
- All endpoints (except health) require auth
- User can only access own projects
- RLS policies on Supabase

### Storage Security
- S3 bucket not publicly listable
- Only `/outputs/` have public read
- Presigned URLs for temporary access

### Environment Variables
- All secrets in environment
- Never committed to git
- Different values for dev/prod

---

## Monitoring & Logging

### Application Logs
- Python logging to stdout
- Railway captures logs
- Filter by service (web/worker)

### Job Tracking
- Project status in database
- Progress percentage
- Error messages if failed

### Cost Tracking
- Track API costs per project
- Store in `projects.cost` column
- Alert if exceeds budget

---

## Future Scalability Paths

### When 100+ Users:
- [ ] Add Redis caching for style specs
- [ ] Implement CDN for video delivery (CloudFlare)
- [ ] Add multiple RQ workers

### When 1000+ Users:
- [ ] Migrate to dedicated Postgres (Railway or AWS RDS)
- [ ] Implement job prioritization (paid users first)
- [ ] Add monitoring (Sentry, DataDog)
- [ ] Implement rate limiting

### When 10,000+ Users:
- [ ] Microservices architecture
- [ ] Kubernetes for worker scaling
- [ ] Separate video processing service
- [ ] CDN for all assets
- [ ] Multi-region deployment

---

## Key Advantages of This Architecture

1. **Clean Separation:** Frontend, API, Worker are independent
2. **Scalable:** Add more workers as needed
3. **Cost-Efficient:** Pay per generation, not idle time
4. **Reliable:** Queue ensures no lost jobs
5. **Debuggable:** Clear status flow, detailed logs
6. **Fast:** Parallel scene generation saves 75% time
7. **Quality:** Product compositing guarantees consistency

---

**End of MVP Architecture Document**

