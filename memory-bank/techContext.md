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
S3_BUCKET_NAME=adgen-videos-xxx
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

### Supabase Table: `projects`
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
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
```

**Why JSONB:**
- Store entire AdProject without schema migrations
- Query nested fields: `ad_project_json->'scenes'->0`
- Update specific fields: `jsonb_set()`
- Perfect for evolving schema (post-MVP editing)

---

## Storage Structure (S3)

```
s3://adgen-videos-xxx/
├── projects/{project_id}/
│   ├── product/
│   │   ├── original.jpg          # User upload
│   │   ├── masked.png             # Background removed
│   │   └── mask.png               # Alpha mask
│   ├── scenes/
│   │   ├── scene_1_bg.mp4         # Generated background
│   │   ├── scene_1_comp.mp4       # With product
│   │   ├── scene_1_overlay.mp4    # With text
│   │   └── ...
│   ├── audio/
│   │   └── background_music.mp3
│   └── outputs/
│       ├── final_9x16.mp4         # Master (vertical)
│       ├── final_1x1.mp4          # Square
│       └── final_16x9.mp4         # Horizontal
```

**Lifecycle Policy:**
```json
{
  "Rules": [{
    "Id": "DeleteAfter7Days",
    "Prefix": "projects/",
    "Status": "Enabled",
    "Expiration": { "Days": 7 }
  }]
}
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
    "prompt": f"{mood} background music, instrumental",
    "duration": video_duration
}
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

### Generation Time (30s video)
```
Scene Planning:       10-20 seconds
Product Extraction:   5-10 seconds
Background Generation: 8-12 minutes (4 scenes × 2-3 min, parallel)
Compositing:          30-60 seconds per scene
Text Overlays:        10-20 seconds total
Music Generation:     60-90 seconds
Final Rendering:      60-90 seconds
Multi-Aspect Export:  30-60 seconds

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
1 RQ Worker:    10-20 concurrent generations
5 RQ Workers:   50-100 concurrent generations
10 RQ Workers:  100-200 concurrent generations

Bottleneck: AI API rate limits (not our infrastructure)
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
- Sufficient for 10-100 users
- Simpler to manage
- Easy to add more later (just deploy more instances)
- Cost-effective

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

**Last Updated:** November 14, 2025

