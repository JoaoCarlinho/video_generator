# Product Context — AI Ad Video Generator

**Why this exists, what problems it solves, how it should work**

---

## The Problem Space

### Current State of AI Video Generation

**Existing tools fail at product advertising because:**

1. **Product Inconsistency**
   - AI models warp logos and distort products
   - Colors change between scenes
   - Brand elements become unrecognizable
   - Result: Unusable for professional advertising

2. **Visual Incoherence**
   - Each scene has different lighting
   - Art styles vary wildly
   - No unified aesthetic
   - Result: Looks amateur, not brand-consistent

3. **No Editing Capability**
   - Generate once, can't modify
   - Must regenerate entire video for small changes
   - Expensive and time-consuming iteration
   - Result: Locked into first generation

4. **Platform Fragmentation**
   - Need 9:16 for TikTok
   - Need 16:9 for YouTube  
   - Need 1:1 for Instagram
   - Result: Manual resizing or multiple tools

### Market Opportunity

- Digital ad market: $786B by 2026
- Video ads: Fastest-growing segment
- Brands need hundreds of variations for A/B testing
- Current solution: $5K-50K per ad, weeks of turnaround

**Gap:** No tool maintains product consistency while generating professional ads at scale.

---

## Our Solution

### Core Innovation: Compositing, Not Generation

**The Insight:** Treat product as sacred, background as variable.

**Traditional Approach (BAD):**
```
User Prompt → AI generates everything → Inconsistent product ❌
```

**Our Approach (GOOD):**
```
1. Extract product from uploaded image (pixel-perfect)
2. Generate background only (no product in prompt)
3. Composite product onto background with OpenCV
   → Product stays exactly the same ✓
```

### How It Works (User Journey)

#### 1. Input Stage
User provides:
- Product brief (2-3 sentences)
- Brand colors
- Target audience
- Video duration (15-60s)
- Mood (uplifting, dramatic, energetic, calm)
- Product image (PNG/JPG)

#### 2. Planning Stage (Automatic)
**Scene Planner (LLM):**
- Breaks brief into 3-5 scenes:
  - Hook (2-3s) - Attention grabber
  - Product Showcase (3-5s) - Hero shot
  - Benefit Demo (4-6s) - Value prop
  - Lifestyle Context (3-5s) - Product in use
  - Call-to-Action (3-4s) - Purchase prompt

**Style Spec Generator:**
- Analyzes brief and brand
- Creates global style rules:
  - Lighting: "soft studio lighting, warm tones"
  - Camera: "smooth panning, cinematic"
  - Mood: "fresh, uplifting"
  - Colors: [brand palette]
  - Grade: "warm shadows, teal highlights"

#### 3. Generation Stage (Automatic)
**Parallel Processing:**
- All scenes generate simultaneously (4x faster)
- Each scene uses same Style Spec
- Product never mentioned in prompts

**Product Extraction:**
- Background removed with rembg
- Saves masked PNG with transparency
- Creates clean mask for compositing

**Background Videos:**
- Wān model generates each scene
- Prompts: Scene description + Style Spec
- Negative prompt: "product, logo, text, watermark"
- Output: Clean backgrounds, 3-4s each

#### 4. Compositing Stage (Automatic)
**For each scene:**
- If productUsage = "none" → Use background as-is
- If productUsage = "static_insert" → Overlay product (centered)
- If productUsage = "animated_insert" → Overlay with zoom/float
- If productUsage = "dominant_center" → Product as focal point

**Process:**
1. Download background video
2. Scale product to 60% of frame height
3. Position product (center, custom, etc.)
4. Frame-by-frame alpha blending with OpenCV
5. Upload composited video to S3

#### 5. Enhancement Stage (Automatic)
**Text Overlays:**
- FFmpeg drawtext filter
- Position based on scene role:
  - Hook: Top center
  - CTA: Bottom center
  - Benefits: Lower third
- Brand colors applied
- Fade in/out animations

**Background Music:**
- MusicGen creates mood-matched track
- Trim to exact video duration
- Normalize to -6dB
- Sync with scene transitions

#### 6. Rendering Stage (Automatic)
**Master Video (9:16):**
- Concatenate all scenes
- Crossfade transitions (0.5s)
- Mux audio with video
- 1080p, 30fps, H.264

**Other Aspects:**
- 1:1 (Square) → Center crop
- 16:9 (Horizontal) → Letterbox or regenerate
- Upload all to S3

#### 7. Delivery
User receives:
- Master video (9:16) for TikTok/Reels
- Square video (1:1) for Instagram Feed
- Horizontal video (16:9) for YouTube
- Generation cost breakdown
- Download links (expire in 7 days)

---

## User Experience Goals

### MVP Experience
**Simple, fast, reliable:**
- Fill form in 2 minutes
- See progress in real-time
- Get video in 8-10 minutes
- Download all formats instantly

**Key Moments:**
1. Upload product image → See preview
2. Click "Generate" → Watch progress bar
3. "Extracting product..." → Build anticipation
4. "Generating scenes..." → Show scene count
5. "Rendering..." → Final step
6. "Complete!" → Play video immediately

**Quality Indicators:**
- Cost displayed: ~$1.00 per video
- Time displayed: 8-10 minutes
- Product looks perfect in every scene
- Music syncs with visuals
- Text overlays readable

### Post-MVP Experience (Future)
**Editing Layer:**
- See timeline with all scenes
- Click scene to edit
- "Make showcase brighter" → Regenerates only that scene
- Drag to reorder scenes
- Generate 5 A/B variations instantly
- Cost: Only regenerated scenes charged

---

## What Success Looks Like

### Technical Success
- 90%+ generation success rate
- <10 min generation time for 30s video
- <$2.00 cost per video
- Product consistency: 9/10 quality
- No critical bugs in core flow

### User Success
- "Wow, the product looks perfect"
- "This is way faster than my agency"
- "I can afford to test 10 variations now"
- Repeat usage: 60%+ create second video
- NPS: 50+

### Business Success
- 10 users initially (competition)
- Path to 1000+ users without refactor
- Positive unit economics ($2 cost → $5-10 pricing)
- Scalable infrastructure (add workers)

---

## Key Principles

1. **Product is Sacred** - Never let AI touch it
2. **Quality Over Speed** - 10 min with great output > 2 min with bad output
3. **Transparency** - Show cost, show progress, show what's happening
4. **Editing Later** - Get generation right first, add editing after
5. **Platform Native** - Each aspect ratio optimized for its platform

---

## What This Enables

### For Small Businesses
- Professional ads without $5K agency fees
- Test multiple creative approaches
- Launch campaigns same day

### For E-commerce
- Generate ads for entire product catalog
- Seasonal variations (summer/winter themes)
- A/B test until you find winners

### For Startups
- In-house video production capability
- Rapid iteration on messaging
- Scale ad spend without hiring

---

## What This Is NOT

- ❌ Not a general-purpose video editor
- ❌ Not for long-form content (>3 min)
- ❌ Not for non-product videos (vlogs, tutorials)
- ❌ Not for frame-accurate editing (for now)

**Focus:** Product advertising, done exceptionally well.

---

**Last Updated:** November 14, 2025

