# Product Context — AI Ad Video Generator (Luxury Perfume Specialist)

**Version 2.0 - Refactored for Luxury Perfume TikTok Ads**

---

## The Problem Space (REFINED FOR PERFUME NICHE)

### Why Luxury Perfume Brands Need Specialized Tools

**Existing generic AI tools fail for perfume advertising because:**

1. **No Understanding of Perfume Visual Language**
   - Generic AI doesn't know perfume shot grammar
   - Produces random scenes (product demos, people talking, generic b-roll)
   - Missing: Macro bottle shots, atmospheric lighting, luxury materials
   - Result: Videos don't "feel like" perfume ads

2. **Can't Maintain Luxury Aesthetic**
   - Freeform LLM generation = inconsistent style
   - One scene dark/moody, next scene bright/colorful
   - No theme consistency across video
   - Result: Looks amateurish, not high-end

3. **Ignores Brand Identity**
   - Can't respect brand guidelines (colors, tone, dos/donts)
   - User style preferences get ignored
   - Reference image inspiration not applied consistently
   - Result: Off-brand, can't use professionally

4. **Wrong Platform Optimization**
   - Tools default to horizontal (16:9)
   - TikTok vertical (9:16) is afterthought
   - Text positioning wrong for mobile UI
   - Result: Crops badly, UI elements covered

### Market Opportunity (PERFUME NICHE)

- **Perfume market:** $65B globally, growing 5-7% yearly
- **TikTok dominance:** #1 platform for perfume discovery (Gen Z/Millennial)
- **Ad volume need:** Brands test 10-50 variations per campaign
- **Current cost:** $5K-50K per 30s ad, 2-4 weeks turnaround
- **Agency bottleneck:** Can't iterate fast enough for TikTok's pace

**Gap:** No AI tool specializes in luxury perfume TikTok ads with consistent brand elegance and proper shot grammar.

### Next-Generation Feature: Multi-Variation Generation (Nov 18, 2025)

Users can now generate 1-3 variations per request:
- **Purpose:** Let users compare different creative approaches on the fly
- **UX:** Select variation count upfront (1, 2, or 3)
- **Experience:** Side-by-side preview of variations, pick favorite
- **Performance:** Parallel generation = 3 variations in same time as 1!
- **Variation types:** Cinematic (dramatic), Minimal (clean), Lifestyle (atmospheric)
- **Result:** Users get options, not forced into single creative direction

This is a pure user experience enhancement - leverages existing infrastructure, adds intelligent variation at scene-planning level.

---

## Our Solution (PERFUME-SPECIALIZED)

### 1. Constrained-Creative AI (NEW)

**The Insight:** LLM creativity WITHIN perfume shot grammar constraints.

**Traditional Approach (BAD):**
```
User Brief → LLM generates any scenes → Random, non-perfume results ❌
```

**Our Approach (GOOD):**
```
1. Load Perfume Shot Grammar (5 categories, 30+ variations)
2. LLM generates scenes BUT MUST use allowed shot types
3. Validate: All scenes follow grammar? Style consistent?
4. If fails → Retry 3x → Use predefined template
   → Creative scenes that always look "perfume-like" ✓
```

**5 Allowed Shot Categories:**
- **Macro Bottle Shots:** Extreme close-up, slow pan, spray mist
- **Luxury B-roll:** Silk fabric, roses/petals, jewelry, candle flame
- **Atmospheric Scenes:** Light rays, shadows, reflections, dust motes
- **Minimal Human Silhouettes:** Hand picking bottle, neck/shoulder, shadowed movement (optional)
- **Final Brand Moment:** Product centered, tagline, black/gold theme

### 2. Style Cascading System (NEW)

**The Insight:** Merge style inputs with clear priority hierarchy.

**Priority:**
1. **Brand Guidelines** (Highest) - Colors, tone, fonts from PDF/DOCX
2. **User Style/Prompt** (More Weight) - GOLD_LUXE, DARK_ELEGANCE, or ROMANTIC_FLORAL
3. **Reference Image** (Some Weight) - Visual inspiration

**Apply unified style to ALL scenes → Theme consistency guaranteed ✓**

### 3. Product Compositing (KEPT)

**The Insight:** Treat perfume bottle as sacred, background as variable.

```
1. Extract bottle from uploaded image (pixel-perfect)
2. Generate luxury backgrounds WITHOUT bottle
3. Composite bottle onto backgrounds with OpenCV
   → Bottle stays exactly the same ✓
```

### How It Works (User Journey)

#### 1. Input Stage
User provides:
- Creative prompt (2-3 sentences describing perfume ad vision)
- Brand name and description
- Perfume name (required, e.g., "Noir Élégance")
- Perfume gender (required: 'masculine', 'feminine', or 'unisex')
- Target audience (optional)
- Video duration (15-60s for TikTok)
- Selected style (optional: 'gold_luxe', 'dark_elegance', or 'romantic_floral')
- Product image (perfume bottle PNG/JPG)
- Brand guidelines (optional PDF/DOCX)
- Reference image (optional mood board)

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

#### 4. Compositing Stage (Automatic) - PERFUME-OPTIMIZED
**For each scene:**
- If use_product = False → Use background as-is
- If use_product = True → Overlay perfume bottle with TikTok-safe positioning

**Process (Perfume-Specific):**
1. Download background video (TikTok vertical 1080x1920)
2. Determine scale based on scene role:
   - Hook scenes: 50% of frame height
   - Showcase scenes: 60% of frame height (larger for product focus)
   - CTA scenes: 50% of frame height
3. Position in TikTok safe zone (15-75% vertical space):
   - center: Centered horizontally, centered in safe zone
   - center_upper: Centered horizontally, upper third of safe zone
   - center_lower: Centered horizontally, lower third of safe zone
4. Frame-by-frame alpha blending with OpenCV
5. Save composited video locally (not S3 until final render)

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
- MusicGen creates luxury ambient cinematic track
- Gender-aware prompts (masculine: deep/confident, feminine: elegant/delicate, unisex: sophisticated/modern)
- Automatic gender inference from style selection or creative prompt
- Trim to exact video duration
- Normalize to -6dB
- Sync with scene transitions

#### 6. Rendering Stage (Automatic)
**TikTok Vertical Video (9:16, 1080x1920):**
- Concatenate all scenes
- Crossfade transitions (0.5s)
- Mux audio with video
- 1080x1920 resolution, 30fps, H.264
- Upload to S3

#### 7. Delivery
User receives:
- TikTok vertical video (9:16, 1080x1920) - ONLY format
- Generation cost breakdown
- Download link (expires in 7 days)

---

## User Experience Goals

### MVP Experience
**Simple, fast, reliable:**
- Fill form in 2 minutes (includes perfume name, gender, style)
- See progress in real-time
- Get TikTok vertical video in 8-10 minutes
- Download video instantly

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

**Last Updated:** November 18, 2025 (Multi-Variation Phase 5 Complete)

