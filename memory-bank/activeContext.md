# Active Context

## Current Focus
Phase 3: AI Scene Editing Feature - Backend implementation complete, ready for frontend integration.

## Recent Implementation Session (January 20, 2025)

### Phase 3: AI Scene Editing Feature - Backend Complete ✅

**Status:** Backend implementation complete, tested, and deployed to Docker

**Implementation Summary:**
- ✅ **EditService** created - LLM-based prompt modification service
- ✅ **SceneEditPipeline** created - 8-step edit pipeline (modify prompt → regenerate → replace → re-render)
- ✅ **S3 helper functions** added - Scene and final video URL construction
- ✅ **Worker updated** - Supports edit job execution via RQ
- ✅ **Database migration** applied - Revision 009 adds `edit_history` JSONB column
- ✅ **API endpoints** registered - 3 endpoints for scenes, editing, and history
- ✅ **Docker tested** - Containers restarted, migration applied, API healthy

**Key Features:**
1. **Prompt Modification** - LLM modifies scene prompts based on user instructions
2. **Scene Regeneration** - Only edited scene regenerated (cost-efficient)
3. **Final Video Re-render** - All scenes downloaded, re-composited, uploaded
4. **Edit History Tracking** - Lightweight audit trail in `campaign_json.edit_history`
5. **Cost Tracking** - ~$0.21 per edit ($0.01 LLM + $0.20 video)

**Architecture:**
- S3-first storage (scenes stored in S3, downloaded for re-rendering)
- Background job processing (RQ worker handles edit jobs)
- Edit history in JSONB (no separate versioning table)
- Single scene edits only (MVP scope)

**API Endpoints:**
- `GET /api/campaigns/{id}/scenes` - Get all scenes with video URLs
- `POST /api/campaigns/{id}/scenes/{idx}/edit` - Edit a scene (enqueues job)
- `GET /api/campaigns/{id}/edit-history` - Get edit history

**Files Created:**
- `backend/app/services/edit_service.py` (160 lines)
- `backend/app/jobs/edit_pipeline.py` (330 lines)
- `backend/app/api/editing.py` (200 lines)
- `backend/alembic/versions/009_add_edit_history.py` (49 lines)

**Files Modified:**
- `backend/app/utils/s3_utils.py` (+2 helper functions)
- `backend/app/jobs/worker.py` (+enqueue_edit_job method)
- `backend/app/database/models.py` (+edit_history column)
- `backend/app/main.py` (+editing router)

**Testing Status:**
- ✅ Database migration applied successfully
- ✅ API endpoints registered in Swagger
- ✅ Docker containers healthy
- ✅ Worker listening on generation queue
- ⏳ End-to-end testing pending (requires frontend)

**Next Steps:**
1. Frontend implementation (Tasks 8-12):
   - useSceneEditing hook
   - SceneCard component
   - EditScenePopup component
   - SceneSidebar component
   - VideoResults page update
2. End-to-end testing with real campaigns
3. User acceptance testing

## Recent Changes (Pre-Planning)
- Fixed video streaming 404 error by constructing S3 keys directly from campaign hierarchy
- Modified `backend/app/api/generation.py` to bypass recursive proxy URL issues
- Validated S3 key construction against bucket structure

## Context
The Veo S3 migration is a strategic upgrade to leverage Google's advanced image-to-video model. Current pipeline uses manual OpenCV compositing and FFmpeg text overlays, which produce artificial-looking results. Veo S3 can generate videos with products and text naturally integrated using image references.

**Architecture Decisions:**
- Keep `use_product` and `use_logo` flags in scene schema (tells Veo which scenes need images)
- Remove manual positioning logic (Veo handles placement intelligently)
- Repurpose `TextOverlay` schema for Veo instruction generation (not manual rendering)
- Update scene planner master prompt with cinematic vocabulary (dolly shots, rack focus, volumetric lighting, etc.)

**CRITICAL PHILOSOPHY UPDATE (Nov 20, 2025):**
- **Priority Hierarchy:** User prompt = PRIMARY (what to show), Grammar = SECONDARY (how to show it)
- **Grammar Role:** Visual language library for cinematography techniques, NOT strict rulebook
- **Golden Rule:** If user says "underwater scene", create underwater scene with perfume cinematography (NOT force "silk fabric" template)
- **Formula:** User's concept (WHAT) + Perfume cinematography (HOW) = Perfect scene
- **Result:** Infinite creative possibilities while maintaining luxury perfume execution quality

## Previous Context (Veo S3 Migration - Complete)

**Veo S3 Migration:** ✅ COMPLETE (November 20, 2025)
- Removed manual compositor and text overlay services
- Simplified pipeline from 7 steps to 5 steps
- Updated scene planner with user-first philosophy
- Enhanced prompts with advanced cinematography vocabulary
- Ready for Veo S3 API integration (future phase)

## Next Steps
1. **Immediate:** Frontend implementation for editing feature (Tasks 8-12)
2. **Phase 1:** Create useSceneEditing hook (2 hours)
3. **Phase 2:** Create SceneCard, EditScenePopup, SceneSidebar components (6-8 hours)
4. **Phase 3:** Update VideoResults page with editing UI (3-4 hours)
5. **Testing:** End-to-end testing with real campaigns
6. **Future:** Multi-scene editing, undo/redo, edit templates
