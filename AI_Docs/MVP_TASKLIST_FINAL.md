# MVP Task List — AI Ad Video Generator
**Focus:** Generation Pipeline Only (No Editing Features)  
**Timeline:** Flexible development pace  
**Goal:** Rock-solid video generation that works reliably

---

## 📋 Phase 0: Infrastructure Setup (Day 0)

### Accounts & Services
- [ ] Create GitHub repository
- [ ] Setup Supabase project
  - [ ] Enable Email/Password auth
  - [ ] Enable Google OAuth
  - [ ] Note project URL and anon key
- [ ] Setup Railway project
  - [ ] Add Redis service
  - [ ] Note Redis URL
- [ ] Setup AWS S3
  - [ ] Create bucket `adgen-videos-{random}`
  - [ ] Enable public read for /outputs/
  - [ ] Note access key and secret
  - [ ] **Configure S3 lifecycle policy for 7-day auto-delete:**
    ```bash
    aws s3api put-bucket-lifecycle-configuration \
      --bucket adgen-videos-xxx \
      --lifecycle-configuration '{
        "Rules": [{
          "Id": "DeleteAfter7Days",
          "Prefix": "projects/",
          "Status": "Enabled",
          "Expiration": {
            "Days": 7
          }
        }]
      }'
    ```
  - [ ] Verify lifecycle policy: `aws s3api get-bucket-lifecycle-configuration --bucket adgen-videos-xxx`
- [ ] Get Replicate API key ($30 credit)
- [ ] Get OpenAI API key ($20 credit)

### Local Environment
- [ ] Verify Python 3.11+: `python3 --version`
- [ ] Verify Node.js 18+: `node --version`
- [ ] Install FFmpeg: `brew install ffmpeg` (macOS)
- [ ] Test FFmpeg: `ffmpeg -version`

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary redis rq replicate openai rembg opencv-python Pillow pydub boto3 python-dotenv pydantic-settings aiohttp
```

- [ ] Create `.env`:
```
DATABASE_URL=postgresql://...  # From Supabase
REDIS_URL=redis://...          # From Railway
REPLICATE_API_TOKEN=r8_...
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=adgen-videos-xxx
SUPABASE_URL=https://...
SUPABASE_KEY=...
```

### Frontend Setup
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install @supabase/supabase-js axios framer-motion react-player react-dropzone react-hook-form
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npx shadcn-ui@latest init
npx shadcn-ui@latest add button input textarea label progress toast card
```

- [ ] Create `.env`:
```
VITE_SUPABASE_URL=https://...
VITE_SUPABASE_ANON_KEY=...
VITE_API_URL=http://localhost:8000
```

---

## 📋 Phase 1: Backend Core (Critical Path)

### 1.1 Project Structure
- [ ] Create backend structure:
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scene_planner.py
│   │   ├── product_extractor.py
│   │   ├── video_generator.py
│   │   ├── compositor.py
│   │   ├── audio_engine.py
│   │   ├── text_overlay.py
│   │   └── renderer.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── projects.py
│   │   └── generation.py
│   └── jobs/
│       ├── __init__.py
│       └── generation_pipeline.py
├── worker.py
└── requirements.txt
```

### 1.2 Database Schema (Supabase)
- [ ] Create `projects` table:
```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  title TEXT NOT NULL,
  ad_project_json JSONB NOT NULL,
  status TEXT DEFAULT 'pending',
  progress INTEGER DEFAULT 0,
  cost DECIMAL(10,2) DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
```

- [ ] Test connection from backend

### 1.3 Pydantic Schemas
- [ ] Implement in `models/schemas.py`:
  - [ ] `Brand` model
  - [ ] `ProductAsset` model
  - [ ] `StyleSpec` model
  - [ ] `Overlay` model
  - [ ] `CompositeConfig` model
  - [ ] `Scene` model
  - [ ] `VideoSettings` model
  - [ ] `AudioSettings` model
  - [ ] `RenderStatus` model
  - [ ] `AdProject` model

### 1.4 FastAPI Application
- [ ] Implement `main.py`:
  - [ ] Create FastAPI app
  - [ ] Add CORS middleware
  - [ ] Health endpoint
  - [ ] Include routers
- [ ] Test: `uvicorn app.main:app --reload`

### 1.5 Early Component Testing (CRITICAL)
**Purpose:** Validate critical dependencies before building full pipeline

#### Test Product Extraction
- [ ] Create `backend/test_extraction.py`:
```python
from rembg import remove
from PIL import Image
import sys

def test_extraction(image_path):
    """Test background removal"""
    img = Image.open(image_path)
    output = remove(img)
    output.save("test_masked.png")
    print(f"✓ Extraction successful: test_masked.png")
    return output.mode == "RGBA"

if __name__ == "__main__":
    success = test_extraction(sys.argv[1])
    sys.exit(0 if success else 1)
```

- [ ] Find or create a test product image
- [ ] Run test: `python test_extraction.py path/to/product.jpg`
- [ ] Review `test_masked.png` - is background removed cleanly?
- [ ] **GO/NO-GO DECISION:**
  - [ ] ✅ GO: Background removed well → Continue with compositing
  - [ ] ❌ NO-GO: Poor extraction → Use original image as fallback (document in code)

#### Test Video Generation
- [ ] Create `backend/test_video_gen.py`:
```python
import replicate
from app.config import settings
import time

def test_generation():
    """Test Wān video model"""
    client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
    
    prompt = "minimal studio background, soft gradient, clean, no objects"
    print(f"Generating video...")
    
    start = time.time()
    output = client.run(
        "minimax/video-01",  # Wān model
        input={
            "prompt": prompt,
            "negative_prompt": "product, text, watermark",
        }
    )
    
    elapsed = time.time() - start
    print(f"✓ Generated in {elapsed:.1f}s")
    print(f"✓ URL: {output}")
    
    # Download
    import requests
    response = requests.get(output[0] if isinstance(output, list) else output)
    with open("test_video.mp4", "wb") as f:
        f.write(response.content)
    print(f"✓ Downloaded: test_video.mp4")

if __name__ == "__main__":
    test_generation()
```

- [ ] Run test: `python test_video_gen.py`
- [ ] Watch `test_video.mp4` - acceptable quality?
- [ ] Note generation time (should be 2-4 minutes)
- [ ] **GO/NO-GO DECISION:**
  - [ ] ✅ GO: Video generated successfully → Continue
  - [ ] ❌ NO-GO: Generation failed → Document issue, may need model change

#### Test FFmpeg Operations
- [ ] Create test videos:
```bash
ffmpeg -f lavfi -i testsrc=duration=3:size=576x1024:rate=30 scene1.mp4
ffmpeg -f lavfi -i testsrc=duration=3:size=576x1024:rate=30 scene2.mp4
```

- [ ] Test concatenation:
```bash
echo "file 'scene1.mp4'" > concat.txt
echo "file 'scene2.mp4'" >> concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c copy output.mp4
```

- [ ] Test text overlay:
```bash
ffmpeg -i scene1.mp4 -vf "drawtext=text='Test':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h-100" test_overlay.mp4
```

- [ ] Verify all outputs play correctly

**🚨 CHECKPOINT 1:**
- [ ] ✅ Product extraction working (or fallback documented)
- [ ] ✅ Video generation produces output
- [ ] ✅ FFmpeg operations work correctly
- **If any CRITICAL failure → Stop and resolve before Phase 2**

### 1.6 Database CRUD Operations
**File:** `app/database/crud.py`

- [ ] Implement `create_project(db, user_id, title, ad_project_json)`:
```python
from supabase import create_client
from app.config import settings
import uuid

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def create_project(user_id: str, title: str, ad_project_json: dict) -> dict:
    """Create new project in Supabase"""
    project = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "ad_project_json": ad_project_json,
        "status": "PENDING",
        "progress": 0,
        "cost": 0.0,
        "error_message": None
    }
    result = supabase.table("projects").insert(project).execute()
    return result.data[0]
```

- [ ] Implement `get_project(project_id)`:
```python
def get_project(project_id: str) -> dict:
    """Get project by ID"""
    result = supabase.table("projects").select("*").eq("id", project_id).execute()
    return result.data[0] if result.data else None
```

- [ ] Implement `get_user_projects(user_id, limit=50)`:
```python
def get_user_projects(user_id: str, limit: int = 50) -> list:
    """Get all projects for user"""
    result = supabase.table("projects") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    return result.data
```

- [ ] Implement `update_project(project_id, **updates)`:
```python
def update_project(project_id: str, **updates) -> dict:
    """Update project fields"""
    updates["updated_at"] = "now()"
    result = supabase.table("projects") \
        .update(updates) \
        .eq("id", project_id) \
        .execute()
    return result.data[0]
```

- [ ] Test all CRUD operations:
```python
# Test in Python REPL
from app.database.crud import *

# Create
project = create_project("test_user", "Test Project", {"version": 1})
print(f"Created: {project['id']}")

# Get
retrieved = get_project(project['id'])
print(f"Retrieved: {retrieved['title']}")

# Update
updated = update_project(project['id'], status="COMPLETED", progress=100)
print(f"Updated: {updated['status']}")

# List
projects = get_user_projects("test_user")
print(f"User has {len(projects)} projects")
```

---

## 📋 Phase 2: Core Services (Heart of Pipeline)

### 2.1 Scene Planner (Critical)
**File:** `services/scene_planner.py`

- [ ] Implement `ScenePlanner` class:
  - [ ] `plan_scenes(brief, brand, duration)` → List[Scene]
    - [ ] Build system prompt with ad structure rules
    - [ ] Call GPT-4o-mini with JSON mode
    - [ ] Parse scenes (3-5 scenes based on duration)
    - [ ] Validate: first scene is hook, last is CTA
    - [ ] Assign productUsage per scene
    - [ ] Generate overlay text
  - [ ] `generate_style_spec(brief, brand)` → StyleSpec
    - [ ] Extract mood, lighting, colors
    - [ ] Incorporate brand colors into palette
  - [ ] Fallback: hardcoded 3-scene plan

**Test:**
```python
# test_scene_planner.py
planner = ScenePlanner()
scenes = await planner.plan_scenes(
    "Premium hydrating serum for radiant skin",
    Brand(name="HydraGlow", primaryColor="#4dbac7"),
    30
)
assert len(scenes) >= 3
assert scenes[0].role == "hook"
```

### 2.2 Product Extractor
**File:** `services/product_extractor.py`

- [ ] Implement `ProductExtractor` class:
  - [ ] `extract_product(image_path, output_dir)` → dict
    - [ ] Load image with PIL
    - [ ] Remove background with rembg
    - [ ] Save masked PNG to S3
    - [ ] Save mask PNG to S3
    - [ ] Extract dimensions
    - [ ] Return asset URLs + metadata
  - [ ] Fallback: if rembg fails, use original image

**Test:**
```python
extractor = ProductExtractor()
result = await extractor.extract_product("test.jpg", "out/")
assert "maskedPngUrl" in result
```

### 2.3 Video Generator
**File:** `services/video_generator.py`

- [ ] Implement `VideoGenerator` class:
  - [ ] `generate_scene_background(scene, style_spec, output_dir)` → str
    - [ ] Build full prompt: scene.backgroundPrompt + style descriptors
    - [ ] Add negative prompt: "product, logo, text, watermark"
    - [ ] Calculate num_frames = duration * 30
    - [ ] Call Replicate Wān model
    - [ ] Download video to local temp
    - [ ] Upload to S3
    - [ ] Return S3 URL
  - [ ] Model: `minimax/video-01` (Wān on Replicate)
  - [ ] Fallback: black video with FFmpeg

**Test:**
```python
generator = VideoGenerator()
video_url = await generator.generate_scene_background(
    scene=test_scene,
    style_spec=test_style,
    output_dir="temp/"
)
assert video_url.startswith("https://")
```

### 2.4 Compositor
**File:** `services/compositor.py`

- [ ] Implement `Compositor` class:
  - [ ] `composite_product(bg_video_url, product_png_url, scene, output_path)` → str
    - [ ] If productUsage == "none": return bg_video_url
    - [ ] Download background video from S3
    - [ ] Download product PNG from S3
    - [ ] Load video with cv2.VideoCapture
    - [ ] Load product with PIL (RGBA)
    - [ ] Scale product to 60% of frame height
    - [ ] Position: center (or custom from scene.composite.position)
    - [ ] Loop through frames:
      - [ ] Paste product with alpha blending
      - [ ] Write frame to output
    - [ ] Upload composited video to S3
    - [ ] Return S3 URL
  - [ ] Fallback: return background if compositing fails

**Test:**
```python
compositor = Compositor()
result = await compositor.composite_product(
    bg_video_url="s3://...",
    product_png_url="s3://...",
    scene=test_scene,
    output_path="temp/comp.mp4"
)
```

### 2.5 Text Overlay Renderer
**File:** `services/text_overlay.py`

- [ ] Implement `TextOverlayRenderer` class:
  - [ ] `add_text_overlay(video_url, overlay, brand, output_path)` → str
    - [ ] Download video from S3
    - [ ] If overlay.text is empty: return video_url
    - [ ] Use FFmpeg drawtext filter:
      - [ ] Position based on overlay.position
      - [ ] Font size based on video resolution
      - [ ] Color from brand.primaryColor
      - [ ] Add subtle shadow/stroke
      - [ ] Fade in/out animation
    - [ ] Upload result to S3
    - [ ] Return S3 URL

**FFmpeg Example:**
```bash
ffmpeg -i input.mp4 -vf "drawtext=text='Shop Now':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h-100:enable='between(t,0,3)'" output.mp4
```

### 2.6 Audio Engine
**File:** `services/audio_engine.py`

- [ ] Implement `AudioEngine` class:
  - [ ] `generate_background_music(mood, duration, output_dir)` → str
    - [ ] Map mood to music prompt
    - [ ] Call Replicate MusicGen model
    - [ ] Download audio
    - [ ] Trim to exact duration with pydub
    - [ ] Normalize volume to -6dB
    - [ ] Upload to S3
    - [ ] Return S3 URL
  - [ ] Fallback: silent audio track

**Test:**
```python
engine = AudioEngine()
audio_url = await engine.generate_background_music("uplifting", 30, "temp/")
```

### 2.7 Final Renderer
**File:** `services/renderer.py`

- [ ] Implement `Renderer` class:
  - [ ] `render_final_video(scene_video_urls, audio_url, output_path, aspect_ratio)` → str
    - [ ] Download all scene videos from S3
    - [ ] Download audio from S3
    - [ ] Create concat file
    - [ ] Add crossfade transitions between scenes (0.5s)
    - [ ] Mux audio with video
    - [ ] Render at 1080p, 30fps, H.264
    - [ ] Upload to S3
    - [ ] Return S3 URL
  - [ ] `render_multi_aspect(master_video_url)` → dict
    - [ ] Download master (9:16)
    - [ ] Generate 1:1 (center crop)
    - [ ] Generate 16:9 (letterbox)
    - [ ] Upload all to S3
    - [ ] Return dict with URLs

**FFmpeg Commands:**
```bash
# Concat with crossfades
ffmpeg -i scene1.mp4 -i scene2.mp4 -filter_complex "[0][1]xfade=transition=fade:duration=0.5:offset=2.5" temp.mp4

# Center crop 9:16 → 1:1
ffmpeg -i input.mp4 -vf "crop=1080:1080" output.mp4

# Letterbox 9:16 → 16:9
ffmpeg -i input.mp4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" output.mp4
```

**🚨 CHECKPOINT 2: Core Services Complete**
- [ ] ✅ ScenePlanner generates valid 3-5 scenes with proper structure
- [ ] ✅ ProductExtractor creates masked PNG (or documents fallback)
- [ ] ✅ VideoGenerator produces quality background video
- [ ] ✅ Compositor overlays product cleanly onto background
- [ ] ✅ TextOverlayRenderer adds text with correct positioning
- [ ] ✅ AudioEngine generates synced music
- [ ] ✅ Renderer produces final video with all 3 aspects
- **If any service fails → Debug before Phase 3**

---

## 📋 Phase 3: Generation Pipeline Job

### 3.1 Background Job Implementation
**File:** `jobs/generation_pipeline.py`

- [ ] Implement async `_generate_full_pipeline(project_id)`:
  ```python
  # Step 1: Load project
  project = get_project(project_id)
  ad_project = AdProject(**project.ad_project_json)
  
  # Step 2: Extract product (10%)
  update_status(project_id, "EXTRACTING_PRODUCT", 10)
  product_data = await extractor.extract_product(...)
  
  # Step 3: Plan scenes (20%)
  update_status(project_id, "PLANNING", 20)
  scenes = await planner.plan_scenes(...)
  style_spec = await planner.generate_style_spec(...)
  
  # Step 4: Generate scene backgrounds (30-60%)
  update_status(project_id, "GENERATING_SCENES", 30)
  tasks = [generator.generate_scene_background(scene, style_spec, ...) for scene in scenes]
  scene_video_urls = await asyncio.gather(*tasks)  # Parallel!
  
  # Step 5: Composite products (65%)
  update_status(project_id, "COMPOSITING", 65)
  composited_urls = []
  for i, scene in enumerate(scenes):
      if scene.productUsage != "none":
          url = await compositor.composite_product(scene_video_urls[i], product_data["maskedPngUrl"], scene, ...)
      else:
          url = scene_video_urls[i]
      composited_urls.append(url)
  
  # Step 6: Add text overlays (75%)
  update_status(project_id, "ADDING_OVERLAYS", 75)
  overlay_urls = []
  for i, scene in enumerate(scenes):
      url = await overlay_renderer.add_text_overlay(composited_urls[i], scene.overlay, brand, ...)
      overlay_urls.append(url)
  
  # Step 7: Generate music (80%)
  update_status(project_id, "GENERATING_AUDIO", 80)
  music_url = await audio_engine.generate_background_music(mood, duration, ...)
  
  # Step 8: Render final video 9:16 (90%)
  update_status(project_id, "RENDERING", 90)
  master_url = await renderer.render_final_video(overlay_urls, music_url, ..., "9:16")
  
  # Step 9: Render other aspects (95%)
  aspect_exports = await renderer.render_multi_aspect(master_url)
  
  # Step 10: Save and complete (100%)
  update_project(project_id, {
      "status": "COMPLETED",
      "progress": 100,
      "ad_project_json": {
          ...ad_project.dict(),
          "renderStatus": {
              "finalVideoUrl": master_url,
              "aspectExports": aspect_exports
          }
      }
  })
  ```

- [ ] Implement sync wrapper: `generate_full_pipeline(project_id)`
- [ ] Add error handling: catch exceptions, set status to FAILED

### 3.1.1 Cost Tracking Implementation
**Purpose:** Track API costs for each generation

- [ ] Add cost tracking throughout pipeline:
```python

async def _generate_full_pipeline(project_id):
    total_cost = 0.0
    
    try:
        # Step 3: Plan scenes
        update_status(project_id, "PLANNING", 20)
        scenes = await planner.plan_scenes(...)
        style_spec = await planner.generate_style_spec(...)
        total_cost += COST_SCENE_PLANNING
        
        # Step 4: Generate videos
        update_status(project_id, "GENERATING_SCENES", 30)
        tasks = [generator.generate_scene_background(...) for scene in scenes]
        scene_video_urls = await asyncio.gather(*tasks)
        total_cost += COST_VIDEO_PER_SCENE * len(scenes)
        
        # Step 7: Generate music
        update_status(project_id, "GENERATING_AUDIO", 80)
        music_url = await audio_engine.generate_background_music(...)
        total_cost += COST_MUSIC_GENERATION
        
        # Update final cost
        update_project(project_id, {
            "status": "COMPLETED",
            "progress": 100,
            "cost": round(total_cost, 2),
            "ad_project_json": {...}
        })
        
    except Exception as e:
        update_project(project_id, {
            "status": "FAILED",
            "error_message": str(e),
            "cost": round(total_cost, 2)  # Save cost even on failure
        })
```

- [ ] Log costs to console for monitoring:
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Project {project_id}: Scene planning cost ${COST_SCENE_PLANNING}")
logger.info(f"Project {project_id}: Video generation cost ${COST_VIDEO_PER_SCENE * len(scenes)}")
logger.info(f"Project {project_id}: Total cost ${total_cost}")
```

### 3.2 RQ Worker
**File:** `worker.py`

```python
from redis import Redis
from rq import Worker
from app.config import settings

redis_conn = Redis.from_url(settings.REDIS_URL)

if __name__ == '__main__':
    worker = Worker(['default'], connection=redis_conn)
    worker.work()
```

- [ ] Test worker runs: `python worker.py`

**🚨 CHECKPOINT 3: Pipeline Integration**
- [ ] ✅ Background job accepts project_id
- [ ] ✅ All 9 pipeline steps execute in order
- [ ] ✅ Status updates correctly at each step
- [ ] ✅ Cost tracking works and saves to database
- [ ] ✅ Error handling catches failures
- [ ] ✅ Worker processes jobs from queue
- **If pipeline fails → Debug job orchestration before Phase 4**

---

## 📋 Phase 4: API Endpoints

### 4.1 Projects API
**File:** `api/projects.py`

- [ ] `POST /api/projects` - Create project
  - [ ] Accept FormData: brief, brandName, primaryColor, duration, productImage
  - [ ] Require Supabase auth
  - [ ] Generate project ID
  - [ ] Upload product image to S3
  - [ ] Create AdProject object
  - [ ] Save to Supabase
  - [ ] Return project ID

- [ ] `GET /api/projects/{project_id}` - Get project
  - [ ] Require auth
  - [ ] Check user owns project
  - [ ] Return full project + status

- [ ] `GET /api/projects/user/all` - List projects
  - [ ] Require auth
  - [ ] Return user's projects

### 4.2 Generation API
**File:** `api/generation.py`

- [ ] `POST /api/generation/projects/{project_id}/generate`
  - [ ] Verify project exists
  - [ ] Verify user owns project
  - [ ] Enqueue job with RQ
  - [ ] Return job ID

---

## 📋 Phase 5: Frontend

### 5.1 Auth & API Setup
- [ ] Create `lib/supabase.ts` - Supabase client
- [ ] Create `lib/api.ts` - Axios client with auth interceptor
- [ ] Create `contexts/AuthContext.tsx` - Auth provider

### 5.2 Pages

**Landing Page** (`pages/Landing.tsx`)
- [ ] Hero section with cool animation (Framer Motion)
- [ ] Feature highlights (3 cards)
- [ ] Demo video showcase
- [ ] CTA buttons → /login, /create
- [ ] Use 21st.dev MCP for modern components

**Login Page** (`pages/Login.tsx`)
- [ ] Email/password form
- [ ] Google OAuth button
- [ ] Sign up / sign in toggle
- [ ] Use shadcn Button, Input

**Create Page** (`pages/Create.tsx`)
- [ ] Project creation form:
  - [ ] Product name (input)
  - [ ] Brief description (textarea)
  - [ ] Brand name (input)
  - [ ] Primary color (color picker)
  - [ ] Duration selector (15/30/60)
  - [ ] Mood selector (dropdown)
  - [ ] Product image upload (dropzone)
- [ ] Form validation with react-hook-form
- [ ] Submit → create project → start generation → redirect to /project/{id}

**Project Page** (`pages/Project.tsx`)
- [ ] Poll project status every 2 seconds
- [ ] Show progress bar + current step
- [ ] When COMPLETED:
  - [ ] Display master video (React Player)
  - [ ] Show generation stats (time, cost)
  - [ ] Download buttons for all 3 aspect ratios
  - [ ] Copy link button
- [ ] When FAILED: show error message

**Dashboard Page** (`pages/Dashboard.tsx`)
- [ ] List all user projects
- [ ] Filter: All / Completed / In Progress / Failed
- [ ] Project cards with thumbnail
- [ ] Quick actions: View, Download, Delete

### 5.3 Components
- [ ] `ProjectForm.tsx` - Creation form
- [ ] `ProgressTracker.tsx` - Generation progress display
- [ ] `VideoPlayer.tsx` - Video preview with controls
- [ ] `ProjectCard.tsx` - Project list item
- [ ] `AspectSelector.tsx` - Download aspect ratio picker

---

## 📋 Phase 6: Integration & Testing

### 6.1 Comprehensive Pipeline Test
**Purpose:** Validate entire generation pipeline end-to-end

- [ ] Create `backend/test_full_pipeline.py`:
```python
"""
End-to-end pipeline test
Tests all services together from scene planning to final render
"""
from app.services.scene_planner import ScenePlanner
from app.services.product_extractor import ProductExtractor
from app.services.video_generator import VideoGenerator
from app.services.compositor import Compositor
from app.services.text_overlay import TextOverlayRenderer
from app.services.audio_engine import AudioEngine
from app.services.renderer import Renderer
from app.models.schemas import Brand
import asyncio
import os
import time

async def test_full_pipeline():
    """Test complete generation pipeline"""
    print("\n" + "="*60)
    print("FULL PIPELINE TEST")
    print("="*60 + "\n")
    
    start_time = time.time()
    output_dir = "/tmp/pipeline_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test configuration
    brand = Brand(
        name="TestBrand",
        primaryColor="#4dbac7",
        secondaryColor="#ffffff"
    )
    brief = "Premium hydrating serum for radiant, glowing skin"
    duration = 12  # 4 scenes × 3s each
    
    try:
        # Step 1: Scene Planning
        print("[1/8] Scene Planning...")
        planner = ScenePlanner()
        scenes = await planner.plan_scenes(brief, brand, duration)
        style_spec = await planner.generate_style_spec(brief, brand)
        assert len(scenes) >= 3, "Need at least 3 scenes"
        print(f"✓ Generated {len(scenes)} scenes")
        for scene in scenes:
            print(f"  - {scene.id}: {scene.role} ({scene.duration}s)")
        
        # Step 2: Product Extraction
        print("\n[2/8] Product Extraction...")
        extractor = ProductExtractor()
        product_data = await extractor.extract_product(
            "test_product.jpg",  # You need to provide this
            output_dir
        )
        assert "maskedPngUrl" in product_data
        print(f"✓ Product extracted")
        print(f"  - Masked PNG: {product_data['maskedPngUrl']}")
        print(f"  - Size: {product_data['width']}x{product_data['height']}")
        
        # Step 3: Generate Scene Backgrounds
        print("\n[3/8] Generating Scene Backgrounds (this will take 5-10 min)...")
        generator = VideoGenerator()
        scene_urls = []
        for i, scene in enumerate(scenes):
            print(f"  [{i+1}/{len(scenes)}] Generating {scene.id}...")
            video_url = await generator.generate_scene_background(
                scene, style_spec, output_dir
            )
            scene_urls.append(video_url)
        print(f"✓ All {len(scene_urls)} backgrounds generated")
        
        # Step 4: Composite Products
        print("\n[4/8] Compositing Products...")
        compositor = Compositor()
        composited_urls = []
        for i, scene in enumerate(scenes):
            if scene.productUsage != "none":
                print(f"  Compositing {scene.id}...")
                url = await compositor.composite_product(
                    scene_urls[i],
                    product_data["maskedPngUrl"],
                    scene,
                    f"{output_dir}/{scene.id}_comp.mp4"
                )
                composited_urls.append(url)
            else:
                composited_urls.append(scene_urls[i])
        print(f"✓ Compositing complete")
        
        # Step 5: Add Text Overlays
        print("\n[5/8] Adding Text Overlays...")
        overlay_renderer = TextOverlayRenderer()
        overlay_urls = []
        for i, scene in enumerate(scenes):
            if scene.overlay and scene.overlay.text:
                print(f"  Adding text to {scene.id}: '{scene.overlay.text}'")
                url = await overlay_renderer.add_text_overlay(
                    composited_urls[i],
                    scene.overlay,
                    brand,
                    f"{output_dir}/{scene.id}_overlay.mp4"
                )
                overlay_urls.append(url)
            else:
                overlay_urls.append(composited_urls[i])
        print(f"✓ Text overlays added")
        
        # Step 6: Generate Music
        print("\n[6/8] Generating Music...")
        audio_engine = AudioEngine()
        music_url = await audio_engine.generate_background_music(
            "uplifting", duration, output_dir
        )
        print(f"✓ Music generated: {music_url}")
        
        # Step 7: Render Final Video
        print("\n[7/8] Rendering Final Video...")
        renderer = Renderer()
        final_url = await renderer.render_final_video(
            overlay_urls,
            music_url,
            f"{output_dir}/final.mp4",
            "9:16"
        )
        print(f"✓ Master video (9:16): {final_url}")
        
        # Step 8: Render Other Aspects
        print("\n[8/8] Rendering Other Aspects...")
        aspects = await renderer.render_multi_aspect(final_url)
        print(f"✓ Exported aspects:")
        for aspect, url in aspects.items():
            print(f"  - {aspect}: {url}")
        
        # Summary
        elapsed = time.time() - start_time
        print("\n" + "="*60)
        print("✅ FULL PIPELINE TEST PASSED")
        print("="*60)
        print(f"Total time: {elapsed/60:.1f} minutes")
        print(f"\nWatch the video:")
        print(f"  {final_url}")
        
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        print("\n" + "="*60)
        print(f"❌ PIPELINE TEST FAILED after {elapsed/60:.1f} minutes")
        print("="*60)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_pipeline())
    sys.exit(0 if success else 1)
```

- [ ] Prepare test product image (`test_product.jpg`)
- [ ] Run test: `python test_full_pipeline.py`
- [ ] Wait for completion (10-15 minutes)
- [ ] Verify output video plays correctly
- [ ] Check all 3 aspect ratios generated

### 6.2 UI Integration Test
- [ ] Start backend: `uvicorn app.main:app --reload`
- [ ] Start worker: `python worker.py`
- [ ] Start frontend: `npm run dev`
- [ ] Create test project through UI
- [ ] Monitor worker logs
- [ ] Wait for completion (~8-10 minutes)
- [ ] Verify final video plays
- [ ] Download all 3 aspect ratios
- [ ] Check videos are correct

**🚨 CHECKPOINT 4: End-to-End Integration**
- [ ] ✅ Can create project through UI
- [ ] ✅ Product extraction works
- [ ] ✅ Scene planning generates valid plans
- [ ] ✅ Video generation produces quality scenes
- [ ] ✅ Product compositing looks professional
- [ ] ✅ Text overlays render correctly
- [ ] ✅ Background music syncs with video
- [ ] ✅ Final render completes successfully
- [ ] ✅ All 3 aspect ratios export correctly
- [ ] ✅ Cost tracking displays in UI
- **If major issues → Fix before deployment**

### 6.3 Test Multiple Products
- [ ] Test with bottle shape
- [ ] Test with flat product (card)
- [ ] Test with complex shape
- [ ] Verify product consistency across scenes

### 6.4 Bug Fixes
- [ ] Fix any extraction issues
- [ ] Fix any compositing artifacts
- [ ] Fix any audio sync issues
- [ ] Fix any rendering errors

---

## 📋 Phase 7: Deployment

### 7.1 Backend Deployment (Railway)
- [ ] Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

- [ ] Push to GitHub
- [ ] Connect Railway to repo
- [ ] Set environment variables
- [ ] Deploy web service
- [ ] Deploy worker service (separate)
- [ ] Verify health endpoint

### 7.2 Frontend Deployment (Vercel)
- [ ] Push to GitHub
- [ ] Connect Vercel to repo
- [ ] Set environment variables
- [ ] Deploy
- [ ] Update CORS in backend

### 7.3 Generate Demo Videos
- [ ] Demo 1: Skincare product (30s)
- [ ] Demo 2: Tech gadget (30s)
- [ ] Save to `/demos` folder

---

## 📋 Phase 8: Documentation

- [ ] Create README.md with setup instructions
- [ ] Create ARCHITECTURE.md (focused on MVP)
- [ ] Capture screenshots (landing, form, progress, result)
- [ ] Record demo walkthrough video (5 minutes)
- [ ] Document environment variables
- [ ] Add comments to complex code

---

## ✅ MVP Complete Checklist

- [ ] Can create project through UI ✓
- [ ] Product extraction works ✓
- [ ] Scene planning generates valid plans ✓
- [ ] Video generation produces quality scenes ✓
- [ ] Product compositing looks professional ✓
- [ ] Text overlays render correctly ✓
- [ ] Background music syncs with video ✓
- [ ] Final render completes successfully ✓
- [ ] All 3 aspect ratios export ✓
- [ ] Videos auto-delete after 7 days ✓
- [ ] Modern UI with animations ✓
- [ ] 2 demo videos generated ✓
- [ ] Documentation complete ✓
- [ ] Deployed and accessible ✓

---

**End of MVP Task List**

