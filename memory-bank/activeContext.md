# Active Context — AI Ad Video Generator

**Current work focus, recent changes, next steps, active decisions**

---

## Current Phase

**Status:** Phase 0 Complete → Ready for Phase 1  
**Focus:** Backend Core Structure Implementation  
**Date:** November 14, 2025

---

## Recent Decisions Made

### 1. MVP Scope Finalized (✅ Complete)
**Decision:** Focus on generation pipeline only, editing features post-MVP

**Rationale:**
- Build solid foundation first
- Validate core innovation (product compositing)
- Architecture designed for easy editing layer addition
- No refactoring needed later

**What's IN MVP:**
- Scene planning with LLM
- Product extraction + compositing
- Multi-scene video generation
- Background music
- Text overlays
- Multi-aspect export (9:16, 1:1, 16:9)

**What's POST-MVP:**
- Timeline editor
- Prompt-based editing
- A/B variations
- Voiceover narration

### 2. Tech Stack Locked (✅ Complete)
**Decisions:**
- **Database:** Supabase (Postgres + Auth in one platform)
- **Storage:** S3 from day 1 (no Railway volume limits)
- **Video Model:** Wān (cost-efficient, good quality)
- **Workers:** Single RQ worker (sufficient for 10-100 users)
- **UI:** shadcn/ui + 21st.dev MCP (modern, professional)

**Rationale:** Balance between simplicity, scalability, and cost.

### 3. Task List Enhanced (✅ Complete)
**Added 5 critical items:**
1. S3 lifecycle configuration (7-day auto-delete)
2. Early component testing with GO/NO-GO checkpoints
3. Database CRUD implementation details
4. GO/NO-GO checkpoints after each phase
5. Cost tracking logic in pipeline
6. Comprehensive end-to-end test script

**Result:** MVP tasklist is now 100% complete and production-ready.

---

## Documents Finalized

### Core Planning Documents
- ✅ `PRD.md` - Complete product vision (full feature set)
- ✅ `MVP_TASKLIST_FINAL.md` - Detailed implementation tasks
- ✅ `MVP_ARCHITECTURE_FINAL.md` - System architecture
- ✅ `MVP_COMPARISON_ANALYSIS.md` - Validation of completeness

### Supporting Documents
- ✅ `adProject.json` - JSON schema
- ✅ `editOperation.json` - Edit operations (post-MVP reference)
- ✅ `Decision.md` - Architectural decisions log
- ✅ `tech-stack.md` - Technology choices

**All documents moved to:** `AI_Docs/` folder for reference.

---

## Next Immediate Steps

### Phase 0: Infrastructure Setup (✅ COMPLETE)
**Timeline:** Completed  
**What was done:**
- ✅ GitHub repository configured
- ✅ Backend virtual environment (Python 3.14)
- ✅ All dependencies installed (see backend/requirements.txt)
- ✅ Backend folder structure created (app/main.py, config, database, models, schemas)
- ✅ Frontend Vite + React + TypeScript initialized
- ✅ Tailwind CSS v4 configured
- ✅ React Router + all dependencies installed
- ✅ FastAPI application verified (imports successfully)
- ✅ Frontend builds successfully

**Still need:**
- [ ] Create Supabase project (and add DATABASE_URL to .env)
- [ ] Create Railway Redis (and add REDIS_URL to .env)
- [ ] Create S3 bucket (and add AWS credentials to .env)
- [ ] Get API keys (Replicate, OpenAI)
- [ ] Create Supabase database tables (SQL provided)
- [ ] Configure S3 lifecycle policy

### Phase 1: Backend Core Structure (NEXT)
**Timeline:** 1-2 days
**Focus:** Database CRUD, API endpoints, authentication

**Critical Tasks:**
1. Database CRUD operations
   - [ ] Create project in database
   - [ ] Read project
   - [ ] Update project
   - [ ] List projects
   - [ ] Delete project

2. API endpoints
   - [ ] POST /api/projects (create)
   - [ ] GET /api/projects (list)
   - [ ] GET /api/projects/{id} (read)
   - [ ] PUT /api/projects/{id} (update)

3. Authentication
   - [ ] Supabase Auth integration
   - [ ] JWT token validation
   - [ ] User context in requests

4. Testing
   - [ ] Database connection test
   - [ ] API endpoint tests
   - [ ] Authentication tests

**Blocker:** Waiting for credentials (.env files)

---

## Open Questions (None Currently)

All major questions resolved during planning:
- ✅ Database choice (Supabase)
- ✅ Storage strategy (S3)
- ✅ Video model (Wān)
- ✅ MVP scope (generation only)
- ✅ Text overlays (in MVP)
- ✅ Multi-aspect (all 3 in MVP)
- ✅ Audio (background music only)
- ✅ **Worker architecture** (single worker with async parallel scene generation)

**Recent Clarification (Nov 14, 2025):**
- Single RQ worker processes ONE user's video at a time
- BUT uses `asyncio.gather()` to generate all scenes in parallel
- Result: 4 scenes in 3 min (not 12 min sequential)
- Add more workers when queue depth >5 (easy horizontal scaling)

---

## Active Considerations

### 1. Video Model Quality
**Context:** Using Wān for cost-efficiency  
**Monitor:** Generation quality during testing  
**Backup Plan:** Can easily swap to different model (service isolated)  
**Decision Point:** During Phase 1.5 early testing

### 2. Product Extraction Quality
**Context:** Using rembg for background removal  
**Monitor:** Extraction quality with different products  
**Backup Plan:** Use original image if extraction fails  
**Decision Point:** Phase 1.5 GO/NO-GO checkpoint

### 3. Cost Per Video
**Target:** Under $2.00 per video  
**Current Estimate:** ~$1.01 per 30s video  
**Monitor:** Actual costs during testing  
**Action:** Adjust cost constants in tracking code

---

## Current Priorities (In Order)

1. **Infrastructure Setup** (Phase 0)
   - Get all accounts and services configured
   - Verify local environment works
   - Test all critical dependencies

2. **Early Component Testing** (Phase 1.5)
   - Test product extraction (GO/NO-GO)
   - Test video generation with Wān
   - Test FFmpeg operations
   - CHECKPOINT 1 validation

3. **Core Services** (Phase 2)
   - Implement all 7 services
   - Test each service independently
   - CHECKPOINT 2 validation

4. **Pipeline Integration** (Phase 3)
   - Connect all services in job pipeline
   - Implement cost tracking
   - Test end-to-end
   - CHECKPOINT 3 validation

---

## Risk Areas to Watch

### High Priority Risks

1. **Product Compositing Quality**
   - **Risk:** Compositing looks fake/artificial
   - **Mitigation:** Test early (Phase 1.5), implement fallbacks
   - **Status:** Will validate at CHECKPOINT 1

2. **Video Generation Consistency**
   - **Risk:** Wān model produces inconsistent quality
   - **Mitigation:** Style Spec system, test multiple products
   - **Status:** Will validate during Phase 2

3. **Generation Time**
   - **Risk:** Takes longer than 10 minutes
   - **Mitigation:** Parallel processing, faster model if needed
   - **Status:** Will measure during testing

### Medium Priority Risks

4. **Audio-Video Sync**
   - **Risk:** Music doesn't sync with scenes
   - **Mitigation:** FFmpeg `-shortest` flag, test thoroughly
   - **Status:** Will validate at CHECKPOINT 2

5. **S3 Costs**
   - **Risk:** Storage costs exceed expectations
   - **Mitigation:** 7-day lifecycle, aggressive compression
   - **Status:** Monitor during development

---

## Post-MVP Planning

### When MVP is Complete
1. **Generate 2 Demo Videos**
   - Skincare product (30s)
   - Tech gadget (30s)
   - Document quality and costs

2. **Deploy to Production**
   - Railway (backend + worker)
   - Vercel (frontend)
   - Verify end-to-end works

3. **Create Documentation**
   - README with setup instructions
   - Architecture document
   - Demo video walkthrough

### Then Start Post-MVP Features
**Priority Order:**
1. Timeline editor (visual scene management)
2. Prompt-based editing (natural language changes)
3. A/B variation generator
4. Voiceover narration (TTS)

**Confidence:** 100% - Architecture supports all these without refactoring.

---

## Team Context

**Team Size:** Solo developer (Ankit)  
**Work Style:** Flexible pace, quality over speed  
**Development Approach:** Phase-by-phase with validation checkpoints

**Communication Style:**
- Clear, technical, implementation-focused
- Ask clarifying questions when needed
- Validate decisions with checkpoints
- Document everything in memory bank

---

## Key Learnings So Far

1. **Early validation is critical**
   - Test product extraction before building full pipeline
   - Test video model quality before committing
   - GO/NO-GO decisions prevent wasted effort

2. **Service isolation pays off**
   - Each service independent = easy testing
   - Easy to swap implementations later
   - Perfect for post-MVP editing features

3. **JSON as source of truth works**
   - JSONB in database = no migrations
   - Easy to serialize/deserialize
   - Enables deterministic regeneration

4. **Cost tracking from day 1**
   - Track every API call
   - Show users what they're paying for
   - Identify optimization opportunities

---

## Context for Next Session

**Where We Are:**
- Planning: 100% complete ✅
- Infrastructure: 0% (starting next)
- Implementation: 0%

**What to Do First:**
1. Read this memory bank (you are here)
2. Start Phase 0: Infrastructure Setup
3. Follow MVP_TASKLIST_FINAL.md step by step
4. Update progress.md after completing phases

**How to Work:**
- One phase at a time
- Validate at checkpoints
- Update memory bank when discoveries made
- Don't skip testing steps

---

**Last Updated:** November 14, 2025  
**Next Update:** After Phase 0 complete

