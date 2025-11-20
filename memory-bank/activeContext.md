# Active Context

## Current Focus
Planning Veo S3 migration to remove manual compositing and text overlay from the generation pipeline.

## Recent Planning Session (November 20, 2025)

### Veo S3 Migration Plan Created
Created comprehensive documentation for migrating from manual post-processing to Veo S3 image-to-video model:

**Key Changes:**
1. **Remove Manual Compositor** (OpenCV frame-by-frame product overlay)
2. **Remove Manual Text Overlay** (FFmpeg drawtext rendering)
3. **Update Scene Planner Prompts** (leverage Veo S3's advanced cinematography capabilities)
4. **Simplify Pipeline** (7 steps → 5 steps, ~30% faster)

**Benefits:**
- Natural product integration (Veo embeds product vs manual overlay)
- Better text quality (AI-generated text in scene vs FFmpeg overlay)
- Cinematic capabilities (dolly shots, rack focus, volumetric lighting, motion physics)
- Simpler codebase (~500 lines removed)
- Faster generation (~30% time reduction)

**Documentation Created:**
- `AI_Docs/VEO_S3_MIGRATION_PLAN.md` - Complete 500+ line implementation guide with:
  - 3 implementation phases (Remove compositor, Remove text overlay, Update prompts)
  - Schema changes (keep `use_product` and `use_logo` flags)
  - Veo S3 system prompt with advanced cinematography vocabulary
  - Testing plan, rollback strategy, risk assessment
  - Timeline: 3-4 hours implementation

**Status:** Planning complete, awaiting authorization to implement

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

## Next Steps
1. **Immediate:** Await user authorization for Veo S3 migration implementation
2. **Phase 1:** Remove compositor service from pipeline (~1 hour)
3. **Phase 2:** Remove text overlay service from pipeline (~1 hour)
4. **Phase 3:** Update scene planner prompts for Veo S3 (~1-2 hours)
5. **Testing:** Verify pipeline runs with 5 steps, test prompt generation quality
6. **Future:** Integrate actual Veo S3 API (separate phase, requires API access)
