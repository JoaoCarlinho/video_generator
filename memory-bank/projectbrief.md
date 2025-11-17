# Project Brief — AI Ad Video Generator (Luxury Perfume Specialist)

**Version:** 2.0 - LUXURY PERFUME REFACTOR  
**Created:** November 14, 2025  
**Refactor Started:** November 17, 2025  
**Status:** Refactor Planning Complete → Ready for Phase 1 Implementation  
**Timeline:** 10 phases, 50-70 hours over 2-3 weeks

---

## Overview

**NEW FOCUS:** GenAds is pivoting from a generic ad generator to a **specialized luxury perfume TikTok ad creator**. The system generates 15-60 second vertical videos (9:16) using constrained-creative AI that follows strict perfume shot grammar while maintaining brand elegance.

---

## Core Problem (REFINED FOR PERFUME NICHE)

Luxury perfume brands need **TikTok-native ads** (9:16 vertical) that:
1. **Maintain Brand Elegance** - Cinematic, high-end, sophisticated aesthetic
2. **Follow Perfume Visual Language** - Macro shots, atmospheric scenes, luxury materials
3. **Stay On-Brand** - Respect brand guidelines (colors, tone, dos/donts)
4. **Generate Fast** - Create variations in minutes, not weeks
5. **Cost-Effective** - < $2 per 30s video vs $5K-50K agency fees

**Current Solutions Fail:**
- Generic AI tools don't understand perfume shot grammar
- Freeform generation produces inconsistent, non-luxury results
- Can't maintain brand identity across scenes
- No TikTok vertical optimization

---

## Core Innovation (REFACTORED)

### 1. Constrained-Creative AI System
**LLM generates scenes BUT must follow strict perfume shot grammar:**
- 5 Allowed Categories: Macro Bottle, Luxury B-roll, Atmospheric, Minimal Human (optional), Brand Moment
- 30+ variations within categories (spray mist, silk fabric, light rays, etc.)
- Duration-based limits (15s→3 scenes, 60s→8 scenes)
- 3-retry validation with fallback to predefined templates
- **Result:** Creative scenes that always look "perfume-like"

### 2. Style Cascading System (NEW)
**Merge style inputs with clear priority:**
1. **Brand Guidelines** (Highest) - Colors, tone, fonts from PDF/DOCX
2. **User Style Selection** (More Weight) - Choose from GOLD_LUXE, DARK_ELEGANCE, ROMANTIC_FLORAL
3. **Reference Image** (Some Weight) - Extract visual inspiration

**Apply unified style to ALL scenes → Theme consistency guaranteed**

### 3. Product Consistency Strategy (KEPT)
**Never let AI generate the product:**
1. Extract perfume bottle from uploaded image
2. Generate luxury backgrounds WITHOUT bottle
3. Composite bottle onto backgrounds (OpenCV)
- **Result:** Pixel-perfect bottle across all scenes

---

## Refactor Scope (Luxury Perfume Specialization)

**What's CHANGING:**
- 🔄 **Scene Planning:** LLM constrained by perfume shot grammar (5 categories)
- 🔄 **Style System:** 3 perfume styles + cascading priority (Brand > User > Reference)
- 🔄 **Video Output:** Hardcoded TikTok vertical (9:16, 1080x1920) ONLY
- 🔄 **Text Overlays:** Luxury fonts (Playfair Display, Montserrant), 3-4 blocks max
- 🔄 **Audio:** Single luxury ambient prompt, simplified pipeline
- 🔄 **Compositing:** Perfume-specific positioning, TikTok safe zones

**What's REMOVED:**
- ❌ Multi-aspect rendering (16:9, 1:1)
- ❌ Generic ad categories and templates
- ❌ Multi-product support
- ❌ Adaptive dynamic positioning
- ❌ Multi-industry flexibility

**What's ADDED:**
- ✅ Perfume shot grammar JSON (30+ variations)
- ✅ PerfumeGrammarLoader service
- ✅ StyleCascadingManager (400+ lines)
- ✅ Fallback templates (3 styles × 4 durations)
- ✅ TikTok-optimized everything

**Timeline:** 10 phases, 50-70 hours, 2-3 weeks

**Rationale:** Focus on ONE niche done exceptionally well. Perfume brands need consistent, elegant TikTok ads. Generic = mediocre. Specialized = exceptional.

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

**Last Updated:** November 17, 2025 (Phase 10 Complete)

