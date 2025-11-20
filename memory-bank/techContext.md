# Tech Context — AI Ad Video Generator

**Technologies, setup, constraints, dependencies**

---

## Technology Stack

### Frontend
- **Framework:** React 18 + Vite + TypeScript
- **Styling:** Tailwind CSS + shadcn/ui
- **UI Enhancement:** 21st.dev MCP for modern components
- **Animation:** Framer Motion
- **Auth:** Supabase Auth (@supabase/supabase-js)
- **HTTP:** Axios (with auth interceptor)
- **Video:** react-player
- **Upload:** react-dropzone
- **Forms:** react-hook-form
- **Routing:** react-router-dom

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** Supabase (Postgres with JSONB)
- **Queue:** Redis + RQ (Python-RQ)
- **ORM:** SQLAlchemy
- **Storage:** AWS S3 (boto3)
- **Config:** pydantic-settings
- **Async:** asyncio + aiohttp

### AI Services
- **Video Generation:** Replicate API (Wān model: `minimax/video-01`)
- **Music Generation:** Replicate API (MusicGen)
- **Scene Planning:** OpenAI GPT-4o-mini
- **Product Extraction:** rembg (local processing)

### Processing Libraries
- **Compositing:** OpenCV + PIL (Pillow)
- **Rendering:** FFmpeg (subprocess)
- **Audio:** pydub

### Infrastructure
- **Frontend Hosting:** Vercel
- **Backend Hosting:** Railway (Web + Worker)
- **Database & Auth:** Supabase
- **Storage:** AWS S3
- **Queue:** Railway Redis

---

## Development Environment

### Required Software
```bash
# Core
Python 3.11+
Node.js 18+
FFmpeg (for video processing)

# Package Managers
pip (Python)
npm (Node.js)

# Optional (for local testing)
PostgreSQL (or use Supabase)
Redis (or use Railway)
```

### Backend Dependencies
```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1

# Queue
redis==5.0.1
rq==1.15.1

# AI APIs
replicate==0.22.0
openai==1.3.7

# Image/Video Processing
rembg==2.0.50
opencv-python==4.8.1.78
Pillow==10.1.0
numpy==1.26.2
pydub==0.25.1

# Storage
boto3==1.33.6

# Utilities
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
aiohttp==3.9.1
```

### Frontend Dependencies
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@supabase/supabase-js": "^2.38.0",
    "axios": "^1.6.0",
    "framer-motion": "^10.16.0",
    "react-player": "^2.13.0",
    "react-dropzone": "^14.2.0",
    "react-hook-form": "^7.48.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "typescript": "^5.2.0",
    "tailwindcss": "^3.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

---

## Environment Configuration

### Backend `.env`
```bash
# Database (Supabase)
DATABASE_URL=postgresql://user:pass@db.xxx.supabase.co:5432/postgres

# Redis (Railway)
REDIS_URL=redis://default:xxx@redis.railway.internal:6379

# AI APIs
REPLICATE_API_TOKEN=r8_xxx
OPENAI_API_KEY=sk-xxx

# Storage (AWS S3)
AWS_ACCESS_KEY_ID=AKIAxxx
AWS_SECRET_ACCESS_KEY=xxx
S3_BUCKET_NAME=genads-gauntlet  # Phase 2 bucket
AWS_REGION=us-east-1

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx

# App Config
ENVIRONMENT=development
DEBUG=True
```

### Frontend `.env`
```bash
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJxxx
VITE_API_URL=http://localhost:8000
```

---

## Database Schema

### Phase 2 B2B Schema (Current)

**Tables:** `brands`, `perfumes`, `campaigns`

See `systemPatterns.md` for complete schema details.

**Migration:** `008_create_b2b_schema.py` (applied Nov 18, 2025)

**Key Changes:**
- Dropped `projects` table
- Created 3-tier hierarchy: brands → perfumes → campaigns
- 1:1 User-Brand relationship
- Cascade delete enforced
- CHECK constraints for validation

### Legacy Schema (Temporary - DEPRECATED)

### Supabase Table: `projects` (DEPRECATED - will be removed in Phase 3-4)
```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  title TEXT NOT NULL,
  ad_project_json JSONB NOT NULL,
  status TEXT DEFAULT 'PENDING',
  progress INTEGER DEFAULT 0,
  cost DECIMAL(10,2) DEFAULT 0,
  error_message TEXT,
  
  -- S3 paths (Phase 1)
  s3_project_folder TEXT,
  s3_project_folder_url TEXT,
  
  -- Video settings (Phase 3)
  aspect_ratio TEXT DEFAULT '9:16',  -- TikTok vertical (hardcoded)
  
  -- Perfume-specific fields (Phase 9)
  perfume_name VARCHAR(200),
  perfume_gender VARCHAR(20),  -- 'masculine', 'feminine', 'unisex'
  
  -- Local storage paths
  local_project_path VARCHAR(500),
  local_video_paths JSONB,  -- Backward compat (deprecated)
  local_video_path VARCHAR(500),  -- Single TikTok vertical video (Phase 9)
  local_input_files JSONB,
  local_draft_files JSONB,
  
  -- Style selection (Phase 7, updated Phase 4)
  selected_style VARCHAR(50),  -- 'gold_luxe', 'dark_elegance', 'romantic_floral'
  
  -- Multi-variation generation (Phase 1, Nov 18, 2025)
  num_variations INTEGER DEFAULT 1 NOT NULL,  -- Number of variations (1-3)
  selected_variation_index INTEGER,  -- Selected variation index (0-2), NULL if not selected
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_selected_style ON projects(selected_style);
CREATE INDEX idx_projects_perfume_name ON projects(perfume_name);  -- Phase 9
CREATE INDEX idx_projects_perfume_gender ON projects(perfume_gender);  -- Phase 9
CREATE INDEX idx_projects_num_variations ON projects(num_variations);  -- Multi-Variation Phase 1
CREATE INDEX idx_projects_selected_variation ON projects(selected_variation_index);  -- Multi-Variation Phase 1
```

**Why JSONB:**
- Store entire AdProject without schema migrations
- Query nested fields: `ad_project_json->'scenes'->0`
- Update specific fields: `jsonb_set()`
- Perfect for evolving schema (post-MVP editing)

---

## Storage Structure (S3) - Phase 2 B2B Hierarchy

### Current Structure (Phase 2)
```
s3://genads-gauntlet/
├── brands/{brand_id}/
│   ├── brand_logo.png              # Permanent (no lifecycle)
│   ├── brand_guidelines.pdf        # Permanent (no lifecycle)
│   └── perfumes/{perfume_id}/
│       ├── front.png               # Permanent (required)
│       ├── back.png                # Permanent (optional)
│       ├── top.png                 # Permanent (optional)
│       ├── left.png                # Permanent (optional)
│       ├── right.png               # Permanent (optional)
│       └── campaigns/{campaign_id}/
│           └── variations/variation_{0|1|2}/
│               ├── draft/          # Delete after 30 days
│               │   ├── scene_1_bg.mp4
│               │   ├── scene_2_bg.mp4
│               │   ├── scene_3_bg.mp4
│               │   ├── scene_4_bg.mp4
│               │   └── music.mp3
│               └── final_video.mp4  # Delete after 90 days
```

**S3 Bucket:** `genads-gauntlet`  
**Region:** `us-east-1`  
**ACL:** Disabled (modern bucket, no ACL support)

**Lifecycle Policy (Applied):**
```json
{
  "Rules": [
    {
      "ID": "DeleteDraftVideosAfter30Days",
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
      "ID": "DeleteFinalVideosAfter90Days",
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

**S3 Tagging Format:**
- Tags formatted as URL-encoded string: `key1=value1&key2=value2`
- Applied via `Tagging` parameter in `put_object()` calls
- Tags used for lifecycle policy filtering

**Legacy Structure (DEPRECATED):**
```
s3://adgen-videos-xxx/projects/{project_id}/...
```

---

## AI Model Configuration

### Video Generation (Wān)
```python
model = "minimax/video-01"
input = {
    "prompt": scene_prompt + style_spec,
    "negative_prompt": "product, logo, text, watermark",
    # Duration calculated as: scene.duration * 30 frames
}
cost_per_scene = ~$0.20
```

**Why Wān:**
- Cost-efficient (~$0.20/scene vs $1+/scene for premium)
- Good quality for ad use case
- Fast generation (2-4 minutes per scene)
- Easy to swap for better model later (isolated service)

### Music Generation (MusicGen)
```python
model = "meta/musicgen"
input = {
    "prompt": f"Luxury ambient cinematic background music for perfume commercial. Mood: {gender_descriptor}. Style: elegant, sophisticated, premium, ambient.",
    "duration": video_duration
}
# Gender descriptors: masculine (deep/confident), feminine (elegant/delicate), unisex (sophisticated/modern)
# Method: generate_perfume_background_music() (perfume-specific)
cost = ~$0.20
```

### Scene Planning (GPT-4o-mini)
```python
model = "gpt-4o-mini"
system_prompt = "You are an expert ad creative director..."
response_format = {"type": "json_object"}
cost = ~$0.01 per request
```

---

## Performance Characteristics

### Generation Time (30s TikTok vertical video)
```
Scene Planning:       10-20 seconds
Product Extraction:   5-10 seconds
Background Generation: 8-12 minutes (4 scenes × 2-3 min, parallel)
Compositing:          30-60 seconds per scene
Text Overlays:        10-20 seconds total
Music Generation:     60-90 seconds
Final Rendering:      60-90 seconds (TikTok vertical 9:16 only)

Total: ~8-10 minutes
```

### Cost Breakdown (30s video)
```
Scene Planning:       $0.01
4 Background Videos:  $0.80 (4 × $0.20)
Music Generation:     $0.20
Local Processing:     $0.00 (compositing, rendering)

Total: ~$1.01 per video
```

### Scalability
```
1 RQ Worker:    
  - Processes 1 video at a time (sequential users)
  - Each video: 4 scenes generated in parallel (asyncio)
  - Throughput: ~6 videos/hour
  - Suitable for: 10-20 users with normal usage

5 RQ Workers:   
  - Process 5 videos simultaneously
  - Throughput: ~30 videos/hour
  - Suitable for: 50-100 users

10 RQ Workers:  
  - Process 10 videos simultaneously
  - Throughput: ~60 videos/hour
  - Suitable for: 100-200 users

Bottleneck: AI API rate limits (not our infrastructure)
Note: Replicate allows concurrent requests, so parallel scene generation works
```

---

## Technical Constraints

### Known Limitations

1. **Video Generation Quality**
   - Dependent on Wān model quality
   - Can't guarantee perfect results every time
   - Mitigation: Regenerate button, automatic retries

2. **Generation Time**
   - Minimum 8 minutes for 30s video
   - Mostly AI API wait time (can't optimize much)
   - Mitigation: Real-time progress updates, clear expectations

3. **Storage Costs**
   - Videos are large (~50-100MB per project)
   - 7-day lifecycle reduces costs
   - Mitigation: Compress aggressively, cleanup old files

4. **S3 Limitations**
   - Not suitable for real-time streaming
   - Mitigation: Pre-generate all formats, use presigned URLs

5. **FFmpeg Complexity**
   - Text overlay positioning tricky
   - Crossfade transitions can fail with different codecs
   - Mitigation: Standardize all videos to same format first

---

## Development Workflow

### Local Development
```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Worker
cd backend
source venv/bin/activate
python worker.py

# Terminal 3: Frontend
cd frontend
npm run dev
```

### Testing Strategy
```bash
# Unit tests (services)
pytest app/services/test_*.py

# Integration test (full pipeline)
python test_full_pipeline.py

# End-to-end (UI)
# Manual testing through browser
```

### Deployment
```bash
# Backend (Railway)
git push origin main  # Auto-deploys

# Frontend (Vercel)
git push origin main  # Auto-deploys

# Environment variables managed in platform UIs
```

---

## Key Technical Decisions

### Why Supabase over Firebase?
- Postgres (easier migration to standalone later)
- Better querying (JSONB support)
- Includes auth + database in one
- Free tier more generous for database

### Why S3 over Railway Volumes?
- Scalable (no 10GB limit)
- Lifecycle policies built-in
- Industry standard
- Easy CDN integration later

### Why Single Worker Initially?
- **One worker = one video generation at a time** (sequential user processing)
- **BUT: Scenes generate in parallel within each job** (4 scenes in 3 min via asyncio)
- Throughput: ~6 videos/hour (sufficient for 10-100 users with normal usage patterns)
- Simpler to manage (no worker coordination needed)
- Easy to add more later (just deploy more instances, they share Redis queue)
- Cost-effective ($10/month per worker on Railway)

**Clarification:**
```
Single Worker Processing:
  User A's video → [Scene1, Scene2, Scene3, Scene4] all in parallel → 3 min
  User B waits → [Scene1, Scene2, Scene3, Scene4] all in parallel → 3 min
  Total: 6 min for 2 users

Multiple Workers (when needed):
  Worker 1: User A's video → 3 min
  Worker 2: User B's video → 3 min  (simultaneous)
  Total: 3 min for 2 users
```

### Why FFmpeg over MoviePy?
- More control over encoding
- Better performance
- Industry standard
- More community support

### Why No WebSockets?
- Polling every 2s is sufficient
- Simpler to implement
- Easier to scale
- Can add WebSockets later if needed

---

## Future Technical Considerations

### When to Add CDN (CloudFlare/CloudFront)
- When serving 100+ users
- When download speeds become issue
- Cost: Minimal ($1-5/month)

### When to Migrate from Supabase
- When need >1TB storage
- When need custom Postgres extensions
- Migration path: Railway Postgres or AWS RDS

### When to Add Multiple Workers
- When queue depth consistently >10
- When users wait >5 min to start
- Cost: $10/worker/month on Railway

---

**Last Updated:** November 18, 2025 (Phase 2 B2B SaaS - Phase 2 S3 Storage Refactor Complete)

