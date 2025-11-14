# AI Ad Video Generator — Product Requirements Document

**Version:** 2.0 (Finalized)  
**Last Updated:** November 14, 2025  
**Project Status:** MVP in Development  
**Target Users:** Small businesses, e-commerce brands, marketing teams

---

## Executive Summary

The AI Ad Video Generator is an end-to-end automated system that transforms a simple product brief into professional, brand-consistent promotional videos. The system's core innovation is **product visual consistency** — ensuring that user-uploaded product images remain pixel-perfect across all generated scenes through advanced compositing techniques rather than unreliable AI generation.

**Key Differentiator:** Unlike traditional video generation tools that produce inconsistent product representations, our system treats the uploaded product image as a locked visual anchor, generating clean backgrounds separately and compositing the product with professional precision.

### Product Vision

"Empower brands to create studio-quality product advertisements in minutes, not days, while maintaining perfect brand consistency."

---

## 1. Problem Statement

### Current Market Challenges

1. **Product Inconsistency in AI Generation**  
   Existing AI video tools generate products directly, leading to warped logos, incorrect colors, and brand inconsistencies that make them unusable for professional advertising.

2. **Lack of Visual Coherence**  
   Most AI video generators produce disconnected clips with varying art styles, lighting, and color palettes, resulting in unprofessional final outputs.

3. **Complex Production Workflows**  
   Creating professional ads requires coordinating videographers, editors, motion designers, and sound engineers — expensive and time-consuming.

4. **Platform Fragmentation**  
   Advertisers need videos in multiple aspect ratios (TikTok 9:16, YouTube 16:9, Instagram 1:1) but creating these manually is inefficient.

### Market Opportunity

The global digital advertising market is projected to reach $786 billion by 2026, with video ads representing the fastest-growing segment. Brands need hundreds of ad variations for A/B testing across platforms.

---

## 2. Target Audience

### Primary Users

**Small Business Owners & Entrepreneurs**
- Need: Affordable professional ads for social media
- Pain Point: Can't afford production teams or agencies
- Value: Generate dozens of ad variations for testing

**E-commerce Brands**
- Need: Product showcase videos for online stores
- Pain Point: Static product images don't convert
- Value: Automated video creation for entire product catalog

**Marketing Teams at Startups**
- Need: Rapid ad iteration for campaigns
- Pain Point: Slow turnaround from creative agencies
- Value: In-house video production capability

---

## 3. Product Features

### 3.1 MVP Features (Generation Pipeline)

#### Scene Planning System
**Purpose:** Intelligently structure video narrative for maximum advertising impact.

**Functionality:**
- AI-powered brief analysis to extract key product benefits
- Automatic scene breakdown into proven ad structures:
  - **Hook:** Attention-grabbing opening (2-3 seconds)
  - **Product Showcase:** Hero shot of product (3-5 seconds)
  - **Benefit Demonstration:** Show value proposition (4-6 seconds)
  - **Lifestyle Context:** Product in use (3-5 seconds)
  - **Call-to-Action:** Purchase prompt with product (3-4 seconds)
- Duration optimization based on target platforms
- Scene-level prompt generation for visual coherence

**User Input:**
- Product description and key benefits
- Target audience and tone
- Desired video duration (15-60 seconds)
- Brand identity (colors, name)

**Output:**
- Structured scene plan with timing, roles, and visual descriptions
- Overlay text recommendations (hooks, CTAs, benefit statements)
- Product integration strategy for each scene

---

#### Product Consistency Engine
**Purpose:** Guarantee pixel-perfect product representation across all scenes.

**Core Innovation:**  
Never let AI models generate the product directly.

**Process:**

1. **Product Extraction**
   - Remove background from uploaded product image
   - Generate clean, transparent PNG with refined edges
   - Create high-quality mask for compositing

2. **Background-Only Generation**
   - Generate scene backgrounds WITHOUT the product
   - Focus AI on environments, lighting, and atmosphere
   - Eliminate product warping/distortion issues

3. **Professional Compositing**
   - Composite extracted product into generated backgrounds
   - Apply scene-appropriate positioning and scaling
   - Add realistic shadows and depth effects
   - Support animation (zoom, pan) while maintaining quality

**Product Usage Modes:**
- **None:** Pure background scene (hooks, transitions)
- **Static Insert:** Product placed in scene, no movement
- **Animated Insert:** Product with subtle motion (zoom, float)
- **Dominant Center:** Product as focal point (showcase, CTA)

**Quality Guarantees:**
- Product pixels never regenerated by AI
- Logo clarity maintained
- Color accuracy preserved
- Brand consistency enforced

---

#### Style Specification System
**Purpose:** Maintain visual coherence across all scenes through a unified aesthetic framework.

**Style Spec Components:**

1. **Lighting Direction**
   - Soft studio lighting, warm tones
   - Dramatic side lighting, high contrast
   - Natural outdoor lighting, diffused

2. **Camera Style**
   - Smooth panning and cinematic zooms
   - Static framing with depth of field
   - Dynamic tracking shots

3. **Texture & Material**
   - Glossy, reflective surfaces
   - Matte, minimal aesthetic
   - Organic, textured backgrounds

4. **Mood & Atmosphere**
   - Fresh and uplifting
   - Luxurious and elegant
   - Energetic and bold

5. **Color Palette**
   - Extracted from brand colors
   - Harmonized across all scenes
   - Applied as LUT in post-processing

6. **Grade & Post-Processing**
   - Warm shadows, teal highlights
   - High contrast, crushed blacks
   - Soft, pastel color science

**How It Works:**
- Generated once at project start from brand guidelines and product image
- Applied to ALL scene generations via prompt engineering
- Ensures every scene feels part of the same ad campaign

**User Control:**
- Select music mood (uplifting, dramatic, energetic, calm)
- Customize brand colors
- Upload product reference image

---

#### Video Generation Pipeline
**Purpose:** Transform scene plans into high-quality video clips.

**Pipeline Stages:**

1. **Prompt Construction**
   - Combine: Scene Description + Style Spec + Technical Parameters
   - Inject negative prompts to avoid unwanted elements
   - Optimize for Wān video model

2. **Background Video Generation**
   - Generate each scene background independently
   - Parallel processing for speed
   - Automatic retry with fallback if quality is poor

3. **Product Compositing**
   - Load scene background and product asset
   - Apply positioning, scaling, and animation
   - Render shadows and lighting integration
   - Export composited scene video

4. **Text Overlay Application**
   - Add text overlays (hooks, CTAs, benefits)
   - Apply brand colors and fonts
   - Animate text entrance/exit
   - Position overlays strategically

5. **Transition Creation**
   - Smooth crossfades between scenes
   - Professional dissolves
   - Beat-synced cuts (if music present)

**Technical Specifications:**
- Minimum 1080p resolution
- 30 FPS for smooth playback
- H.264 encoding for broad compatibility
- Optimized file sizes for web delivery

---

#### Audio System
**Purpose:** Create immersive soundscapes that enhance visual storytelling.

**MVP Audio (Background Music Only):**
- AI-generated music matching mood specification
- Genre options: Uplifting, dramatic, chill, energetic
- Automatic volume normalization
- Loop or trim to exact video duration

**Audio Mixing:**
- Music normalized to proper levels
- No audio-video drift or sync issues
- Professional mastering

**User Controls:**
- Select music mood
- Adjust volume level (optional)

---

#### Multi-Aspect Export System
**Purpose:** Deliver platform-optimized videos from a single generation.

**Supported Aspect Ratios:**

1. **9:16 (Vertical)**
   - Platform: TikTok, Instagram Reels, YouTube Shorts
   - Strategy: Master generation format
   - Optimization: Full vertical canvas utilization

2. **1:1 (Square)**
   - Platform: Instagram Feed, Facebook
   - Strategy: Center crop from 9:16 master
   - Optimization: Intelligent framing to preserve product and text

3. **16:9 (Horizontal)**
   - Platform: YouTube, website embeds
   - Strategy: Letterbox or regenerate scenes
   - Optimization: Option to generate in native 16:9 for premium quality

**Smart Cropping:**
- Automatically detect product and text regions
- Preserve critical elements in all crops
- Maintain composition balance

---

### 3.2 Post-MVP Features (Editing Layer)

#### Timeline Editor
Visual interface for precise control:
- Scene reordering (drag-and-drop)
- Duration adjustment (trim scenes)
- Text editing (direct overlay editing)
- Product control (toggle on/off per scene)
- Selective regeneration (regenerate individual scenes)
- Transition editing (change types and timing)

#### Prompt-Based Editing
Natural language modifications:
- "Make the showcase scene brighter and add more motion"
- "Change the CTA to 'Shop Now'"
- Translates to operations → Regenerates only affected scenes

**Edit Operations Supported:**
- Update overlay text
- Adjust scene duration
- Reorder scenes
- Regenerate with prompt modifications
- Change product positioning
- Update brand colors
- Modify global style

**Isolation Principle:**  
Scene changes never cascade. Each scene is independent, so edits only regenerate what's necessary.

---

#### A/B Variation Generator
**Purpose:** Enable rapid testing of ad creative elements.

**Variation Types:**

1. **Hook Variations**
   - Test different opening lines
   - Alternative attention-grabbers
   - Maintain identical scenes 2-5

2. **CTA Variations**
   - Test different calls-to-action
   - "Shop Now" vs "Learn More" vs "Get Yours"
   - Different urgency levels

3. **Tone Variations**
   - Playful vs Professional
   - Urgent vs Calm
   - Luxury vs Accessible

**Consistency Rules:**
- All variations share identical Style Spec
- Product remains exactly the same
- Only text and tone vary
- Background scenes may subtly adjust mood

---

#### Advanced Audio Features
**Voiceover Narration:**
- Text-to-speech from scene-level scripts
- Multiple voice profiles (professional, friendly, authoritative)
- Sync narration timing to scene transitions

**Background Ad Voice (Optional):**
- Subtle whisper/motivational voice layer
- Mixed at low volume for atmosphere

**Audio Mixing:**
- Three-layer mix: Music + Narration + Background Voice
- Dynamic volume balancing (narration ducks music)
- Professional mastering with limiter

---

## 4. User Journey

### First-Time User Flow (MVP)

1. **Sign Up / Login**
   - Supabase authentication
   - Google/Email sign-in options
   - No credit card required

2. **Project Creation**
   - Click "Create New Ad"
   - Fill out simple form:
     - Product name
     - Brief description (2-3 sentences)
     - Key benefits
     - Target audience
     - Upload product image (PNG/JPG)
   - Select brand colors (color picker)
   - Choose video duration (15s / 30s / 60s)
   - Select mood (Uplifting / Dramatic / Energetic / Calm)

3. **Generation Progress**
   - Real-time progress tracker showing:
     - "Planning scenes..."
     - "Extracting product..."
     - "Generating scenes... (Scene 2 of 5)"
     - "Creating soundtrack..."
     - "Compositing product..."
     - "Rendering final video..."
   - Estimated time remaining
   - Live preview of completed scenes (optional)

4. **Preview & Download**
   - Video player with completed ad
   - Generation summary:
     - Total duration
     - Scene count
     - Generation cost
     - Processing time
   - Download options:
     - Download master video (9:16)
     - Export additional formats (1:1, 16:9)
     - Copy shareable link

---

## 5. Technical Requirements

### 5.1 Generation Quality

**Visual Coherence:**
- Consistent art style across all clips
- Smooth transitions between scenes
- No jarring style shifts or artifacts
- Professional color grading throughout

**Audio-Visual Sync:**
- Music transitions aligned to scene changes
- No audio-video drift
- Beat-matched cuts for music videos

**Output Quality:**
- Minimum 1080p resolution (1920x1080 or 1080x1920)
- 30 FPS frame rate
- Clean audio (no distortion, clipping, or background noise)
- Optimized compression (reasonable file size without quality loss)

---

### 5.2 Pipeline Performance

**Speed Targets:**
- 30-second video: Generate in under 8 minutes
- 60-second video: Generate in under 15 minutes
- Scene regeneration: Under 2 minutes per scene

**Cost Efficiency:**
- Target: Under $2.00 per minute of final video
- Track generation cost per video
- Cache repeated elements (style specs, product assets)

**Reliability:**
- 90%+ successful generation rate
- Graceful failure handling with informative error messages
- Automatic retry logic for transient API failures
- Detailed logging for debugging

---

### 5.3 Scalability

**Initial Scale (10-100 Users):**
- Single RQ worker sufficient
- Supabase free tier
- S3 standard storage
- Fair resource allocation via queue

**Future Scale (1000+ Users):**
- Multiple workers (horizontal scaling)
- Supabase paid tier or migrate to Postgres
- S3 with lifecycle policies
- CDN for video delivery
- Priority queue for paid users

**Storage Management:**
- Auto-delete projects after 7 days
- User option to save favorites permanently
- Efficient video compression
- Temporary file cleanup

---

## 6. Technology Stack

### Frontend
- **Framework:** React + Vite + TypeScript
- **Styling:** Tailwind CSS + shadcn/ui
- **UI Enhancement:** 21st.dev MCP components
- **Animation:** Framer Motion
- **Authentication:** Supabase Auth
- **API Client:** Axios

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** Supabase (Postgres)
- **Queue:** Redis + RQ
- **Storage:** AWS S3
- **ORM:** SQLAlchemy

### AI Services
- **Video Generation:** Replicate API (Wān model)
- **Scene Planning:** OpenAI GPT-4o-mini
- **Music Generation:** Replicate API (MusicGen)
- **Product Extraction:** rembg

### Processing
- **Compositing:** OpenCV + PIL
- **Rendering:** FFmpeg
- **Audio Processing:** pydub

### Infrastructure
- **Backend Hosting:** Railway
- **Frontend Hosting:** Vercel
- **Storage:** AWS S3
- **Database & Auth:** Supabase

---

## 7. Success Metrics

### MVP Success Criteria

**Functionality:**
- ✅ Working end-to-end generation pipeline
- ✅ Product consistency maintained across scenes
- ✅ Audio-visual sync achieved
- ✅ Multi-aspect export working
- ✅ Text overlays properly rendered
- ✅ 2+ demo videos showcase capabilities

**Quality:**
- Visual coherence score: 8/10 (subjective review)
- No critical bugs blocking core flow
- Professional output quality
- Generation time < 10 minutes for 30s video

**User Experience:**
- Intuitive form interface
- Clear progress feedback
- Easy download process
- Modern, professional UI

---

## 8. Non-Functional Requirements

### Security
- Secure authentication via Supabase
- API endpoint protection (JWT tokens)
- User data isolation
- Secure file upload handling
- Environment variables for secrets

### Performance
- Page load times < 2 seconds
- Video upload responsive feedback
- Streaming video playback
- No memory leaks

### Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Minimum browser version: Last 2 major versions
- Responsive design (desktop + tablet)

---

## 9. MVP Scope vs. Post-MVP

### ✅ IN MVP (Generation Pipeline)
- Scene planning with LLM
- Style Spec generation
- Product extraction + compositing
- Multi-scene video generation
- Background music generation
- Text overlay rendering
- Multi-aspect export (9:16, 1:1, 16:9)
- Modern UI with cool landing page
- Project dashboard
- Video preview + download

### ❌ POST-MVP (Editing Layer)
- Timeline editor (drag-and-drop)
- Prompt-based editing
- A/B variation generator
- Voiceover narration (TTS)
- Background ad voice
- Scene-level regeneration UI
- Advanced transitions
- Custom fonts/animations
- Team collaboration
- Analytics dashboard

---

## 10. Risks & Mitigation

### Risk 1: Product Compositing Looks Artificial
**Impact:** High — Core differentiator fails  
**Likelihood:** Medium

**Mitigation:**
- Test compositing early with multiple products
- Implement quality scoring for composites
- Fallback: Use product as overlay without full removal
- Add subtle shadows and lighting effects

### Risk 2: Video Generation Quality Inconsistent
**Impact:** High — Unprofessional outputs  
**Likelihood:** Medium

**Mitigation:**
- Test Wān model early with multiple scenes
- Implement automatic quality checks
- Fallback to different model if quality issues persist
- Use shorter scenes (2-3s) to hide quality issues

### Risk 3: Generation Cost Exceeds Budget
**Impact:** Medium — Unsustainable for testing  
**Likelihood:** Medium

**Mitigation:**
- Start with Wān (cost-efficient model)
- Implement aggressive caching
- Monitor per-video costs
- Limit free tier generations

### Risk 4: API Rate Limits or Downtime
**Impact:** High — Pipeline breaks  
**Likelihood:** Low

**Mitigation:**
- Implement retry logic with exponential backoff
- Queue system to manage rate limits
- Fallback to alternative models if needed
- Detailed error logging

---

## 11. Future Enhancements (Beyond Post-MVP)

### Advanced Features
- Voice cloning from user audio samples
- Motion brush for custom product animation
- Advanced depth-based parallax effects
- Custom LoRA model training for brand consistency
- Batch generation (multiple products simultaneously)
- Integration with e-commerce platforms (Shopify, WooCommerce)
- Automatic subtitles/captions
- Multi-language support

### Business Features
- Team collaboration tools
- Brand asset libraries
- Campaign management dashboard
- Analytics and performance tracking
- White-label solutions
- API access for developers
- Subscription tiers

---

## 12. Appendix

### Glossary

**AdProject:** The central JSON data structure representing an entire ad project, including scenes, style, audio, and render status.

**Scene:** A single video segment within an ad, typically 2-5 seconds long, with a specific role (hook, showcase, benefit, CTA).

**Style Spec:** A global specification defining lighting, color, camera style, and mood to ensure visual consistency across all scenes.

**Product Usage:** A scene attribute defining how the product appears (none, static_insert, animated_insert, dominant_center).

**Compositing:** The process of overlaying a transparent product image onto a generated background video.

**Aspect Ratio:** The proportional relationship between video width and height (9:16 vertical, 1:1 square, 16:9 horizontal).

---

## Document Approval

**Version:** 2.0 (Finalized)  
**Date:** November 14, 2025  
**Status:** Approved — Ready for MVP Implementation

**Next Steps:**
1. ✅ PRD Finalized
2. → Create MVP Task List
3. → Create MVP Architecture Document
4. → Begin Implementation

---

**End of Document**

