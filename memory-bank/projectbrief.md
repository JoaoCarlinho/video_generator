# Project Brief — AI Ad Video Generator

**Version:** 1.0  
**Created:** November 14, 2025  
**Status:** Planning Complete → Ready for Implementation  
**Timeline:** Flexible (MVP-focused development)

---

## Overview

AI Ad Video Generator is an end-to-end automated system that transforms a simple product brief into professional, brand-consistent promotional videos. The system's core innovation is **product visual consistency** through compositing rather than unreliable AI generation.

---

## Core Problem

Current AI video generators produce inconsistent product representations with:
- Warped logos and incorrect colors
- Disconnected clips with varying art styles
- No ability to edit after generation
- Single aspect ratio outputs

**Market Need:** Brands need hundreds of ad variations for A/B testing across platforms (TikTok 9:16, YouTube 16:9, Instagram 1:1). Creating these manually is expensive ($5K-50K per ad) and slow (weeks).

---

## Core Innovation

### Product Consistency Strategy
**Never let AI generate the product.** Instead:
1. Extract product from uploaded image (remove background)
2. Generate clean backgrounds WITHOUT product
3. Composite real product onto backgrounds with OpenCV

**Result:** Pixel-perfect product across all scenes.

### Style Consistency System
Generate a global **Style Spec** once:
- Lighting direction
- Camera style
- Texture & materials
- Mood & atmosphere
- Color palette (from brand colors)
- Grade & post-processing

Apply to ALL scenes → Visual coherence guaranteed.

---

## MVP Scope (Generation Pipeline)

**What's IN MVP:**
- ✅ Scene planning with LLM (GPT-4o-mini)
- ✅ Product extraction + compositing
- ✅ Multi-scene video generation (Wān model)
- ✅ Background music generation
- ✅ Text overlay rendering
- ✅ Multi-aspect export (9:16, 1:1, 16:9)
- ✅ Modern UI with cool landing page
- ✅ 7-day auto-cleanup

**What's POST-MVP:**
- ❌ Timeline editor (drag-and-drop)
- ❌ Prompt-based editing
- ❌ A/B variation generator
- ❌ Voiceover narration (TTS)

**Rationale:** Build solid generation pipeline first, then add editing layer. Clean separation ensures MVP code won't need refactoring.

---

## Target Users

**Primary:** Small business owners, e-commerce brands, startup marketing teams

**Scale Strategy:**
- Initial: 10 users (competition submission)
- Near-term: 100-1000 users
- Architecture designed for easy horizontal scaling

---

## Success Criteria

### MVP Success
- ✅ Generate 30s video in under 10 minutes
- ✅ Product consistency across all scenes (8/10 quality)
- ✅ Audio-visual sync achieved
- ✅ All 3 aspect ratios export correctly
- ✅ Cost < $2.00 per video
- ✅ 2 demo videos showcasing capabilities

### Post-MVP Success
- Add editing features without refactoring core pipeline
- Support 1000+ concurrent users
- Achieve 90%+ generation success rate

---

## Key Architectural Decisions

1. **Supabase for Database & Auth** - Single platform, easy migration to Postgres later
2. **S3 from Day 1** - Proper scalability (no 10GB Railway volume limits)
3. **Wān Model for Video** - Cost-efficient, good quality
4. **Single RQ Worker** - Sufficient for 10-100 users
5. **AdProject JSON as Source of Truth** - JSONB in database, enables easy editing later
6. **Service Layer Isolation** - Each service independent, reusable for post-MVP

---

## Non-Negotiables

- **Quality:** Product consistency is #1 priority
- **Scalability:** Must support 10 users now, 1000+ later without major refactor
- **Modern UI:** Professional, cool animations, shadcn/ui + 21st.dev MCP
- **Clean Code:** Small components, well-structured for post-MVP features
- **Cost Tracking:** Track every API call, display to user

---

## Documents

**Core Planning:**
- `PRD.md` - Complete product requirements (full vision)
- `MVP_TASKLIST_FINAL.md` - Detailed implementation tasks (generation only)
- `MVP_ARCHITECTURE_FINAL.md` - System architecture and data flow

**Supporting:**
- `adProject.json` - JSON schema for AdProject structure
- `editOperation.json` - Edit operation schemas (post-MVP)
- `Decision.md` - Architectural decision log
- `tech-stack.md` - Technology choices and rationale

---

## Current Status

**Phase:** Ready to implement  
**Next Action:** Start Phase 0 (Infrastructure Setup)

**Completed:**
- ✅ PRD finalized
- ✅ MVP tasklist complete with all critical items
- ✅ Architecture designed and validated
- ✅ Post-MVP readiness confirmed (100%)

**Ready to Build:** YES ✓

---

**Last Updated:** November 14, 2025

