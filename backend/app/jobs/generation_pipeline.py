"""RQ Background job for end-to-end video generation pipeline.

This module contains the main generation pipeline that orchestrates all services:
1. Product Extraction (remove background)
2. Scene Planning (LLM-based)
3. Video Generation (parallel for all scenes)
4. Compositing (product overlay)
5. Text Overlay Rendering
6. Audio Generation (MusicGen)
7. Horizontal Rendering (16:9)

Each step tracks costs and updates progress in database.

LOCAL-FIRST ARCHITECTURE:
- All intermediate files stored locally in /tmp/genads/{project_id}/
- Final videos saved locally only (no S3 upload)
- User can finalize project to mark as complete (videos stay local)
"""

import asyncio
import logging
import time
import boto3
from uuid import UUID
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
from functools import wraps

from app.database import connection as db_connection
from app.database.connection import init_db
from app.database.crud import (
    get_project,
    update_project_status,
    update_project_output,
    update_project_s3_paths,
)
from app.models.schemas import AdProject, Scene, StyleSpec
from app.services.scene_planner import ScenePlanner
from app.services.product_extractor import ProductExtractor
from app.services.video_generator import VideoGenerator
from app.services.compositor import Compositor
from app.services.text_overlay import TextOverlayRenderer
from app.services.audio_engine import AudioEngine
from app.services.renderer import Renderer
from app.services.reference_image_extractor import ReferenceImageStyleExtractor
from app.utils.s3_utils import (
    create_project_folder_structure,
    delete_project_folder,
    upload_to_project_folder,
)
from app.utils.local_storage import LocalStorageManager, format_storage_size

logger = logging.getLogger(__name__)

# Cost constants (in USD, based on API documentation)
COST_REFERENCE_EXTRACTION = Decimal("0.025")  # GPT-4 Vision extraction
COST_SCENE_PLANNING = Decimal("0.01")  # GPT-4o-mini cheap
COST_PRODUCT_EXTRACTION = Decimal("0.00")  # rembg local, free
COST_VIDEO_GENERATION = Decimal("0.08")  # SeedAnce-1-lite per scene
COST_COMPOSITING = Decimal("0.00")  # Local OpenCV, free
COST_TEXT_OVERLAY = Decimal("0.00")  # Local FFmpeg, free
COST_MUSIC_GENERATION = Decimal("0.10")  # MusicGen per track
COST_RENDERING = Decimal("0.00")  # Local FFmpeg, free


# ============================================================================
# Task 7: Timing Decorator for Pipeline Steps
# ============================================================================

def timed_step(step_name: str):
    """Decorator to time pipeline steps.
    
    Task 7: Adds timing tracking to each pipeline step for observability.
    
    Args:
        step_name: Human-readable name of the step
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            logger.info(f"⏱️  Starting step: {step_name}")
            
            try:
                result = await func(self, *args, **kwargs)
                elapsed = time.time() - start_time
                
                # Store timing in pipeline instance
                if hasattr(self, 'step_timings'):
                    self.step_timings[step_name] = elapsed
                
                logger.info(f"✅ Step complete: {step_name} ({elapsed:.1f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"❌ Step failed: {step_name} ({elapsed:.1f}s) - {str(e)}")
                raise
        
        return wrapper
    return decorator


# Cost constants (in USD, based on API documentation)
COST_REFERENCE_EXTRACTION = Decimal("0.025")  # GPT-4 Vision extraction
COST_SCENE_PLANNING = Decimal("0.01")  # GPT-4o-mini cheap
COST_PRODUCT_EXTRACTION = Decimal("0.00")  # rembg local, free
COST_VIDEO_GENERATION = Decimal("0.08")  # SeedAnce-1-lite per scene
COST_COMPOSITING = Decimal("0.00")  # Local OpenCV, free
COST_TEXT_OVERLAY = Decimal("0.00")  # Local FFmpeg, free
COST_MUSIC_GENERATION = Decimal("0.10")  # MusicGen per track
COST_RENDERING = Decimal("0.00")  # Local FFmpeg, free


class GenerationPipeline:
    """Main pipeline orchestrator for video generation."""

    def __init__(self, project_id: UUID):
        """Initialize pipeline for a specific project.
        
        Args:
            project_id: UUID of the project to generate
        """
        self.project_id = project_id
        init_db()
        
        if db_connection.SessionLocal is None:
            raise RuntimeError(
                "Database not initialized. "
                "Check DATABASE_URL environment variable and database connectivity."
            )
        
        self.db = db_connection.SessionLocal()
        self.total_cost = Decimal("0.00")
        self.step_costs: Dict[str, Decimal] = {}
        self.step_timings: Dict[str, float] = {}  # Task 7: Track step timings

    async def run(self) -> Dict[str, Any]:
        """Execute the full generation pipeline.
        
        Task 7: Enhanced with timing tracking, cost breakdown logging, and cleanup on failure.
        
        Returns:
            Dict with pipeline results including final video URLs, cost breakdown, and timings
            
        Raises:
            Exception: If any critical step fails (caught and logged)
        """
        pipeline_start = time.time()
        music_task = None
        
        try:
            logger.info(f"🚀 Starting generation pipeline for project {self.project_id}")

            # Load project from database
            project = get_project(self.db, self.project_id)
            if not project:
                raise ValueError(f"Project {self.project_id} not found")

            # ===== LOCAL-FIRST: Initialize local storage =====
            logger.info("💾 Initializing local storage...")
            try:
                local_paths = LocalStorageManager.initialize_project_storage(self.project_id)
                self.local_paths = local_paths
                storage_info = LocalStorageManager.get_project_storage_size(self.project_id)
                logger.info(f"✅ Local storage initialized: {self.local_paths}")
            except Exception as e:
                logger.error(f"⚠️ Failed to initialize local storage: {e}")
                raise

            # ===== S3 RESTRUCTURING: Initialize project folder structure =====
            logger.info("📁 Initializing S3 project folder structure...")
            try:
                folders = await create_project_folder_structure(str(self.project_id))
                # Note: update_project_s3_paths is NOT async, don't await it
                update_project_s3_paths(
                    self.db,
                    self.project_id,
                    folders["s3_folder"],
                    folders["s3_url"]
                )
                logger.info(f"✅ S3 folders initialized at {folders['s3_url']}")
                self.s3_folders = folders  # Store for use by services
            except Exception as e:
                logger.error(f"⚠️ Failed to initialize S3 folders: {e}")
                self.s3_folders = None  # Fallback to old behavior

            # Parse AdProject JSON
            ad_project = AdProject(**project.ad_project_json)

            # ===== STEP 0: Extract Reference Image Style (Optional, NEW) =====
            logger.info("🎨 Step 0: Checking for reference image...")
            has_reference = False
            if project.ad_project_json:
                reference_local_path = project.ad_project_json.get("referenceImage", {}).get("localPath")
                
                if reference_local_path:
                    import os
                    if os.path.exists(reference_local_path):
                        has_reference = True
                        logger.info(f"🎨 Extracting visual style from reference image...")
                        self.update_progress(self.project_id, 5, "Extracting reference image style...")
                        
                        try:
                            # Initialize OpenAI client for vision extraction
                            from openai import AsyncOpenAI
                            from app.config import settings
                            
                            openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                            extractor = ReferenceImageStyleExtractor(openai_client)
                            
                            # Extract style
                            extracted_style = await extractor.extract_style(
                                image_path=reference_local_path,
                                brand_name=project.brand.get("name", "Brand")
                            )
                            
                            # Save to database
                            project.ad_project_json["referenceImage"]["extractedStyle"] = extracted_style.to_dict()
                            project.ad_project_json["referenceImage"]["extractedAt"] = datetime.now().isoformat()
                            self.db.commit()
                            
                            # Reload project to get updated JSON
                            project = get_project(self.db, self.project_id)
                            ad_project = AdProject(**project.ad_project_json)
                            
                            # Delete temp file
                            os.unlink(reference_local_path)
                            logger.info(f"✅ Reference style extracted and temp file deleted")
                            
                            # Track cost
                            self.step_costs["reference_extraction"] = COST_REFERENCE_EXTRACTION
                            self.total_cost += COST_REFERENCE_EXTRACTION
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to extract reference style: {e}")
                            has_reference = False
                    else:
                        logger.info(f"ℹ️ Reference image file not found: {reference_local_path}")
                else:
                    logger.info(f"ℹ️ No reference image provided")
            else:
                logger.info(f"ℹ️ No ad_project_json available")

            # ===== STEP 1: Extract Product (Optional) =====
            product_url = None
            has_product = ad_project.product_asset is not None and ad_project.product_asset.original_url
            
            if has_product:
                logger.info("📦 Step 1: Extracting product...")
                product_url = await self._extract_product(project, ad_project)
                self.step_costs["extraction"] = COST_PRODUCT_EXTRACTION
                self.total_cost += COST_PRODUCT_EXTRACTION
            else:
                logger.info("📦 Step 1: Skipping product extraction (no product image provided)")

            # ===== STEP 2: Plan Scenes =====
            # Adjust progress start based on whether we have a product
            planning_start = 15 if has_product else 10
            logger.info("🎬 Step 2: Planning scenes...")
            updated_project = await self._plan_scenes(project, ad_project, progress_start=planning_start)
            self.step_costs["scene_planning"] = COST_SCENE_PLANNING
            self.total_cost += COST_SCENE_PLANNING

            # Update project with new ad_project data
            ad_project = AdProject(**updated_project.ad_project_json)

            # ===== STEP 3A: Spawn Music Generation (PARALLEL with video) =====
            logger.info("🎵 Step 3A: Spawning background music generation (running in parallel)...")
            music_task = asyncio.create_task(
                self._generate_audio(project, ad_project, progress_start=30)
            )
            logger.info("🎵 Music generation task spawned - running in background")

            # ===== STEP 3B: Generate Videos (Parallel with Music) =====
            logger.info("🎥 Step 3B: Generating videos for all scenes...")
            video_start = 25 if has_product else 20
            replicate_videos = await self._generate_scene_videos(project, ad_project, progress_start=video_start)
            video_cost = COST_VIDEO_GENERATION * len(ad_project.scenes)
            self.step_costs["video_generation"] = video_cost
            self.total_cost += video_cost
            
            # Save videos locally (Replicate URLs are temporary, so we download immediately)
            logger.info("💾 Saving videos to local storage...")
            scene_videos = await self._save_videos_locally(replicate_videos, str(self.project_id))
            logger.info(f"✅ Saved {len(scene_videos)} videos to local storage")

            # ===== STEP 4: Composite Product (Optional) =====
            # Note: Music is still generating in background
            if product_url:
                logger.info("🎨 Step 4: Compositing product onto scenes (music still generating)...")
                composited_videos = await self._composite_products(
                    scene_videos, product_url, ad_project, progress_start=40
                )
                self.step_costs["compositing"] = COST_COMPOSITING
                self.total_cost += COST_COMPOSITING
            else:
                logger.info("🎨 Step 4: Skipping compositing (no product image)")
                composited_videos = scene_videos  # Use background videos as-is

            # ===== STEP 4B: Composite Logo (Optional, NEW - Task 4) =====
            # Note: Music is still generating in background
            if ad_project.brand.logo_url:
                logger.info("🏷️  Step 4B: Compositing logo onto scenes (music still generating)...")
                logo_composited_videos = await self._composite_logos(
                    composited_videos,
                    ad_project.brand.logo_url,
                    ad_project,
                    progress_start=55 if product_url else 50
                )
                self.step_costs["logo_compositing"] = Decimal("0.00")  # Local, free
                self.total_cost += Decimal("0.00")
            else:
                logger.info("🏷️  Step 4B: Skipping logo compositing (no logo provided)")
                logo_composited_videos = composited_videos

            # ===== STEP 5: Add Text Overlays =====
            # Note: Music is still generating in background
            logger.info("📝 Step 5: Rendering text overlays (music still generating)...")
            overlay_start = 65 if (product_url or ad_project.brand.logo_url) else 50
            text_rendered_videos = await self._add_text_overlays(
                logo_composited_videos, ad_project, progress_start=overlay_start
            )
            self.step_costs["text_overlay"] = COST_TEXT_OVERLAY
            self.total_cost += COST_TEXT_OVERLAY

            # ===== STEP 6: Synchronize - Wait for Music Generation =====
            logger.info("⏳ Step 6: Waiting for background music generation to complete...")
            try:
                audio_url = await music_task
                logger.info(f"✅ Background music generation complete: {audio_url}")
                self.step_costs["audio"] = COST_MUSIC_GENERATION
                self.total_cost += COST_MUSIC_GENERATION
            except asyncio.CancelledError:
                logger.error("❌ Music generation was cancelled")
                raise
            except Exception as e:
                logger.error(f"❌ Music generation failed: {e}")
                raise

            # ===== STEP 7: Render Multi-Aspect =====
            logger.info("📺 Step 7: Rendering final videos (multi-aspect)...")
            render_start = 85 if has_product else 80
            final_videos = await self._render_final(
                text_rendered_videos, audio_url, ad_project, progress_start=render_start
            )
            self.step_costs["rendering"] = COST_RENDERING
            self.total_cost += COST_RENDERING

            # Task 7: Log cost breakdown and timing summary
            total_elapsed = time.time() - pipeline_start
            self._log_cost_breakdown()
            logger.info(f"🎬 PIPELINE COMPLETE in {total_elapsed:.1f}s")
            logger.info(f"⏱️  Step timings: {self.step_timings}")

            # ===== LOCAL-FIRST: Final videos already saved locally by renderer =====
            logger.info("✅ Final videos already saved to local storage by renderer")
            # Renderer now returns local paths directly, not S3 URLs
            local_video_paths = final_videos

            # Calculate local storage size
            storage_size = LocalStorageManager.get_project_storage_size(self.project_id)
            logger.info(f"📊 Total local storage: {format_storage_size(storage_size)}")

            # Update project with local paths (NOT S3 URLs!)
            # output_videos stays empty until user finalizes
            project.local_video_paths = local_video_paths
            project.status = 'COMPLETED'  # Changed from auto-upload
            self.db.commit()

            logger.info(f"✅ Project ready for preview. Videos stored locally.")

            # Update legacy output_videos field for backward compatibility
            update_project_output(
                self.db,
                self.project_id,
                {},  # Empty output_videos - will be filled on finalization
                float(self.total_cost),
                {k: float(v) for k, v in self.step_costs.items()},
            )

            return {
                "status": "COMPLETED",
                "project_id": str(self.project_id),
                "local_video_paths": local_video_paths,
                "storage_size": storage_size,
                "storage_size_formatted": format_storage_size(storage_size),
                "message": "Videos ready for preview. Videos stored in local storage.",
                "total_cost": float(self.total_cost),
                "cost_breakdown": {k: float(v) for k, v in self.step_costs.items()},
                "timing_seconds": total_elapsed,  # Task 7: Total pipeline time
                "step_timings": self.step_timings,  # Task 7: Per-step timings
            }

        except Exception as e:
            # Task 7: Enhanced error handling with cleanup
            total_elapsed = time.time() - pipeline_start
            logger.error(f"❌ Pipeline failed after {total_elapsed:.1f}s: {e}", exc_info=True)

            # Cancel background music task if still running
            if music_task is not None and not music_task.done():
                logger.info("🚫 Cancelling background music generation task...")
                music_task.cancel()
                try:
                    await music_task
                except asyncio.CancelledError:
                    logger.info("✅ Music task cancelled successfully")
                except Exception as cancel_error:
                    logger.warning(f"⚠️  Error cancelling music task: {cancel_error}")

            # Task 7: Cleanup partial files (optional, non-critical)
            try:
                logger.info("🧹 Attempting to cleanup partial files...")
                LocalStorageManager.cleanup_project_storage(self.project_id)
                logger.info("✅ Cleanup completed")
            except Exception as cleanup_error:
                logger.warning(f"⚠️  Failed to cleanup storage: {cleanup_error}")

            # Log cost breakdown even on failure
            if self.step_costs:
                self._log_cost_breakdown()

            # Mark project as failed
            error_msg = str(e)[:500]  # Truncate long errors
            update_project_status(
                self.db,
                self.project_id,
                "FAILED",
                error_message=error_msg,
            )
            # Update cost separately
            from app.database.crud import update_project_cost
            update_project_cost(self.db, self.project_id, float(self.total_cost))

            return {
                "status": "FAILED",
                "project_id": str(self.project_id),
                "error": error_msg,
                "total_cost": float(self.total_cost),
                "cost_breakdown": {k: float(v) for k, v in self.step_costs.items()},
                "timing_seconds": total_elapsed,  # Task 7: Time before failure
                "step_timings": self.step_timings,  # Task 7: Partial timings
            }

    def _log_cost_breakdown(self):
        """Log detailed cost breakdown table.
        
        Task 7: Enhanced cost logging with percentage breakdown.
        """
        logger.info("=" * 60)
        logger.info("💰 COST BREAKDOWN")
        logger.info("=" * 60)
        
        if self.total_cost == 0:
            logger.info("  No costs incurred (all steps were free)")
            logger.info("=" * 60)
            return
        
        for step_name, cost in sorted(self.step_costs.items(), key=lambda x: float(x[1]), reverse=True):
            percentage = (float(cost) / float(self.total_cost) * 100) if self.total_cost > 0 else 0
            logger.info(f"  {step_name:30s} ${float(cost):7.4f} ({percentage:5.1f}%)")
        
        logger.info("-" * 60)
        logger.info(f"  {'TOTAL':30s} ${float(self.total_cost):7.4f} (100.0%)")
        logger.info("=" * 60)

    @timed_step("Product Extraction")
    async def _extract_product(
        self, project: Any, ad_project: AdProject
    ) -> str:
        """Extract product from uploaded image using rembg."""
        try:
            update_project_status(
                self.db, self.project_id, "EXTRACTING_PRODUCT", progress=10
            )

            if not ad_project.product_asset or not ad_project.product_asset.original_url:
                raise ValueError("Product asset not found or missing original_url")
            
            from app.config import settings
            extractor = ProductExtractor(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region,
            )
            
            product_url = await extractor.extract_product(
                image_url=ad_project.product_asset.original_url,
                project_id=str(self.project_id),
            )

            logger.info(f"✅ Product extracted: {product_url}")
            return product_url

        except Exception as e:
            logger.error(f"❌ Product extraction failed: {e}")
            raise

    @timed_step("Scene Planning")
    async def _plan_scenes(self, project: Any, ad_project: AdProject, progress_start: int = 15) -> Any:
        """Plan scenes using LLM and generate style spec."""
        try:
            update_project_status(
                self.db, self.project_id, "PLANNING", progress=progress_start
            )

            from app.config import settings
            planner = ScenePlanner(api_key=settings.openai_api_key)
            
            # Brand colors from LLM or reference image if available
            brand_colors = []
            
            # Check if reference image style was extracted
            extracted_style = None
            if project.ad_project_json:
                extracted_style = project.ad_project_json.get("referenceImage", {}).get("extractedStyle")
                if extracted_style:
                    brand_colors = extracted_style.get("colors", [])
                    logger.info(f"🎨 Using colors from reference image: {brand_colors}")
            
            # Check if product/logo are available
            has_product = ad_project.product_asset is not None and ad_project.product_asset.original_url
            has_logo = ad_project.brand.logo_url is not None
            
            # ===== STEP 1B: Extract Brand Guidelines (Optional, NEW - Task 5) =====
            extracted_guidelines = None
            if ad_project.brand.guidelines_url:
                logger.info(f"📄 Step 1B: Extracting brand guidelines from document...")
                try:
                    from app.services.brand_guidelines_extractor import BrandGuidelineExtractor
                    from openai import AsyncOpenAI
                    
                    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                    extractor = BrandGuidelineExtractor(
                        openai_client=openai_client,
                        aws_access_key_id=settings.aws_access_key_id,
                        aws_secret_access_key=settings.aws_secret_access_key,
                        s3_bucket_name=settings.s3_bucket_name,
                        aws_region=settings.aws_region,
                    )
                    
                    extracted_guidelines = await extractor.extract_guidelines(
                        guidelines_url=ad_project.brand.guidelines_url,
                        brand_name=ad_project.brand.name
                    )
                    
                    if extracted_guidelines:
                        logger.info(
                            f"✅ Extracted guidelines: {len(extracted_guidelines.color_palette)} colors, "
                            f"tone='{extracted_guidelines.tone_of_voice}'"
                        )
                        # Store in video_metadata for reference
                        if not ad_project.video_metadata:
                            ad_project.video_metadata = {}
                        ad_project.video_metadata['extractedGuidelines'] = extracted_guidelines.to_dict()
                    else:
                        logger.warning("⚠️  Guidelines extraction returned None, continuing without")
                    
                    # Cost: ~$0.01 for LLM extraction
                    self.step_costs["guidelines_extraction"] = Decimal("0.01")
                    self.total_cost += Decimal("0.01")
                    
                except Exception as e:
                    logger.error(f"❌ Guidelines extraction failed: {e}")
                    logger.warning("Continuing pipeline without brand guidelines")
                    extracted_guidelines = None
            else:
                logger.info("📄 Step 1B: No brand guidelines URL provided, skipping")
            
            # Task 5: Merge colors from guidelines into brand_colors
            if extracted_guidelines and extracted_guidelines.color_palette:
                brand_colors.extend(extracted_guidelines.color_palette)
                brand_colors = list(set(brand_colors))  # Remove duplicates
                logger.info(f"🎨 Merged brand colors from guidelines: {brand_colors}")
            
            # Build creative prompt with reference style if available
            creative_prompt = ad_project.creative_prompt
            if extracted_style:
                creative_prompt += f"""

REFERENCE VISUAL STYLE (from uploaded mood board):
- Colors: {', '.join(extracted_style.get('colors', []))}
- Mood: {extracted_style.get('mood', 'professional')}
- Lighting: {extracted_style.get('lighting', 'professional')}
- Camera: {extracted_style.get('camera', 'professional')}
- Atmosphere: {extracted_style.get('atmosphere', 'professional')}
- Texture: {extracted_style.get('texture', 'professional')}

Incorporate this visual style consistently throughout all scenes."""
            
            # Task 5: Add brand guidelines context to creative prompt
            if extracted_guidelines:
                guideline_text = f"""

BRAND GUIDELINES (extracted from guidelines document):
- Tone of Voice: {extracted_guidelines.tone_of_voice}
- Color Palette: {', '.join(extracted_guidelines.color_palette) if extracted_guidelines.color_palette else 'Not specified'}"""
                
                if extracted_guidelines.dos_and_donts.get('dos'):
                    guideline_text += f"\n- DO: {'; '.join(extracted_guidelines.dos_and_donts['dos'][:3])}"
                if extracted_guidelines.dos_and_donts.get('donts'):
                    guideline_text += f"\n- DON'T: {'; '.join(extracted_guidelines.dos_and_donts['donts'][:3])}"
                
                guideline_text += "\n\nEnsure all scenes follow these brand guidelines."
                creative_prompt += guideline_text
            
            # PHASE 7: Pass selected_style to ScenePlanner
            plan = await planner.plan_scenes(
                creative_prompt=creative_prompt,
                brand_name=ad_project.brand.name,
                brand_description=ad_project.brand.description,
                brand_colors=brand_colors,
                brand_guidelines=extracted_guidelines.to_dict() if extracted_guidelines else None,
                target_audience=ad_project.target_audience or "general consumers",
                target_duration=ad_project.target_duration,
                has_product=has_product,
                has_logo=has_logo,
                aspect_ratio=ad_project.video_settings.aspect_ratio,
                selected_style=project.selected_style,  # PHASE 7: Pass user-selected style if any
            )

            # PHASE 7: plan_scenes now returns dict with chosenStyle, styleSource
            chosen_style = plan.get('chosenStyle')  # The ONE style for entire video
            style_source = plan.get('styleSource')  # 'user_selected' or 'llm_inferred'
            plan_scenes_list = plan.get('scenes', [])
            plan_style_spec = plan.get('style_spec', {})
            
            logger.info(f"✅ ScenePlanner chose style: {chosen_style} ({style_source})")

            # Update ad_project with scenes and style spec from plan
            # Convert plan scenes to AdProject scenes format
            from app.models.schemas import Overlay, Scene as AdProjectScene
            ad_project.scenes = [
                AdProjectScene(
                    id=str(scene.get('scene_id', i)),
                    role=scene.get('role', 'showcase'),
                    duration=scene.get('duration', 5),
                    description=scene.get('background_prompt', ''),
                    background_prompt=scene.get('background_prompt', ''),
                    background_type=scene.get('background_type', 'cinematic'),
                    
                    # Product fields (Task 1: Schema Enhancements)
                    use_product=scene.get('use_product', False),
                    product_usage=scene.get('product_usage', 'static_insert'),
                    product_position=scene.get('product_position', 'center'),  # NEW
                    product_scale=scene.get('product_scale', 0.3),              # NEW
                    product_opacity=scene.get('product_opacity', 1.0),          # NEW
                    
                    # Logo fields (Task 1: Schema Enhancements)
                    use_logo=scene.get('use_logo', False),
                    logo_position=scene.get('logo_position', 'top_right'),      # NEW
                    logo_scale=scene.get('logo_scale', 0.1),                    # NEW
                    logo_opacity=scene.get('logo_opacity', 0.9),                # NEW
                    
                    # Layout fields (Task 1: Schema Enhancements)
                    camera_movement=scene.get('camera_movement', 'static'),
                    transition_to_next=scene.get('transition_to_next', 'cut'),
                    safe_zone=scene.get('safe_zone'),                           # NEW
                    overlay_preference=scene.get('overlay_preference'),         # NEW
                    
                    # Text overlay
                    overlay=Overlay(
                        text=scene.get('overlay', {}).get('text', ''),
                        position=scene.get('overlay', {}).get('position', 'bottom'),
                        font_size=scene.get('overlay', {}).get('font_size', 48),
                        duration=scene.get('overlay', {}).get('duration', 2.0),
                    ) if scene.get('overlay') else None,
                )
                for i, scene in enumerate(plan_scenes_list)
            ]
            
            # Task 3: Normalize scene durations to match target duration
            ad_project.scenes = self._normalize_scene_durations(
                ad_project.scenes,
                ad_project.target_duration,
                tolerance=0.10
            )
            
            # Convert StyleSpec from plan to AdProject StyleSpec format
            ad_project.style_spec = StyleSpec(
                lighting=plan_style_spec.get('lighting_direction', ''),
                camera_style=plan_style_spec.get('camera_style', ''),
                mood=plan_style_spec.get('mood_atmosphere', ''),
                color_palette=plan_style_spec.get('color_palette', []),
                texture=plan_style_spec.get('texture_materials', ''),
                grade=plan_style_spec.get('grade_postprocessing', ''),
            )

            # PHASE 7 + Task 2: Store chosen style and derived tone in ad_project_json
            if not ad_project.video_metadata:
                ad_project.video_metadata = {}
            ad_project.video_metadata['selectedStyle'] = {
                'style': chosen_style,
                'source': style_source,
                'appliedAt': datetime.utcnow().isoformat()
            }
            # Task 2: Store derived tone for music mood generation
            if 'derivedTone' in plan:
                ad_project.video_metadata['derivedTone'] = plan['derivedTone']
                logger.info(f"📊 Stored derived tone in metadata: {plan['derivedTone']}")

            # Save back to database
            project.ad_project_json = ad_project.dict()
            self.db.commit()

            logger.info(f"✅ Planned {len(ad_project.scenes)} scenes with style spec")
            return project

        except Exception as e:
            logger.error(f"❌ Scene planning failed: {e}")
            raise

    @timed_step("Video Generation")
    async def _generate_scene_videos(
        self, project: Any, ad_project: AdProject, progress_start: int = 25
    ) -> List[str]:
        """Generate background videos for all scenes in parallel."""
        try:
            update_project_status(
                self.db, self.project_id, "GENERATING_SCENES", progress=progress_start
            )

            from app.config import settings
            generator = VideoGenerator(api_token=settings.replicate_api_token)

            # Check if reference style was extracted
            extracted_style = None
            if project.ad_project_json:
                extracted_style = project.ad_project_json.get("referenceImage", {}).get("extractedStyle")
            
            # PHASE 7: Get the chosen style for all scenes
            chosen_style = None
            if project.ad_project_json and "video_metadata" in project.ad_project_json:
                video_metadata = project.ad_project_json.get("video_metadata", {})
                style_info = video_metadata.get("selectedStyle", {})
                chosen_style = style_info.get("style")
                logger.info(f"PHASE 7: Using chosen style for ALL scenes: {chosen_style} ({style_info.get('source', 'unknown')})")
            
            # Task 3: Get aspect ratio from video settings
            aspect_ratio = ad_project.video_settings.aspect_ratio if ad_project.video_settings else "16:9"
            logger.info(f"📐 Generating videos with aspect ratio: {aspect_ratio}")

            # Task 7: Create tasks with better error tracking
            tasks = []
            for i, scene in enumerate(ad_project.scenes):
                try:
                    task = generator.generate_scene_background(
                        prompt=scene.background_prompt,
                        style_spec_dict=ad_project.style_spec.dict() if hasattr(ad_project.style_spec, 'dict') else ad_project.style_spec,
                        duration=scene.duration,
                        aspect_ratio=aspect_ratio,  # Task 3: Pass aspect ratio
                        extracted_style=extracted_style,  # Pass extracted style to generator
                        style_override=chosen_style,  # PHASE 7: Pass chosen style to all scenes
                    )
                    tasks.append(task)
                except Exception as e:
                    logger.error(
                        f"❌ Failed to create task for scene {i} (role: {scene.role}): {e}"
                    )
                    raise

            # Run all tasks concurrently with return_exceptions to catch individual failures
            scene_videos = await asyncio.gather(*tasks, return_exceptions=True)

            # Task 7: Check for errors with scene context
            for i, result in enumerate(scene_videos):
                if isinstance(result, Exception):
                    scene = ad_project.scenes[i]
                    logger.error(
                        f"❌ Scene {i} generation failed:\n"
                        f"   Role: {scene.role}\n"
                        f"   Prompt: {scene.background_prompt[:100]}...\n"
                        f"   Duration: {scene.duration}s\n"
                        f"   Error: {result}"
                    )
                    raise RuntimeError(
                        f"Scene {i} ({scene.role}) generation failed: {result}"
                    )

            logger.info(f"✅ Generated {len(scene_videos)} videos")
            return scene_videos

        except Exception as e:
            logger.error(f"❌ Video generation failed: {e}")
            raise

    async def _save_videos_locally(self, video_urls: List[str], project_id: str) -> List[str]:
        """Download videos from Replicate and save to local storage."""
        try:
            import aiohttp
            from app.utils.local_storage import LocalStorageManager
            
            local_paths = []
            for i, replicate_url in enumerate(video_urls):
                try:
                    # Download from Replicate
                    async with aiohttp.ClientSession() as session:
                        async with session.get(replicate_url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                            if resp.status == 200:
                                video_data = await resp.read()
                            else:
                                logger.warning(f"Failed to download video {i}: HTTP {resp.status}")
                                raise Exception(f"Failed to download video {i}: HTTP {resp.status}")
                    
                    # Save to local storage in drafts folder
                    local_path = LocalStorageManager.save_draft_file(
                        UUID(project_id),
                        f"scene_{i:02d}.mp4",
                        video_data
                    )
                    local_paths.append(local_path)
                    logger.debug(f"✅ Saved scene {i} locally: {local_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to save video {i} locally: {e}")
                    raise
            
            return local_paths
            
        except Exception as e:
            logger.error(f"Error saving videos locally: {e}")
            raise

    @timed_step("Product Compositing")
    async def _composite_products(
        self,
        scene_videos: List[str],
        product_url: str,
        ad_project: AdProject,
        progress_start: int = 40,
    ) -> List[str]:
        """
        Composite product onto each scene video using scene-specific positioning.
        
        Task 4: Now uses product_position, product_scale, product_opacity from each Scene.
        """
        try:
            update_project_status(
                self.db, self.project_id, "COMPOSITING", progress=progress_start
            )

            from app.config import settings
            compositor = Compositor(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region,
            )

            # Composite for each scene that has use_product=True
            composited = []
            for i, (video_url, scene) in enumerate(zip(scene_videos, ad_project.scenes)):
                # Task 4: Check if scene should have product, use scene-specific positioning
                if scene.use_product:
                    position = scene.product_position or "center"
                    scale = scene.product_scale or 0.3
                    opacity = scene.product_opacity or 1.0
                    
                    logger.info(
                        f"Compositing scene {i}/{len(scene_videos)}: "
                        f"position={position}, scale={scale:.2f}, opacity={opacity:.2f}"
                    )
                    
                    composited_url = await compositor.composite_product(
                        background_video_url=video_url,
                        product_image_url=product_url,
                        project_id=str(self.project_id),
                        position=position,   # Scene-specific (from Task 1 fields)
                        scale=scale,         # Scene-specific
                        opacity=opacity,     # Scene-specific
                        scene_index=i,
                    )
                    composited.append(composited_url)
                else:
                    # Skip compositing for this scene
                    composited.append(video_url)
                    logger.debug(f"Skipping scene {i} (use_product=False)")
                progress = progress_start + (i / len(ad_project.scenes)) * 15
                update_project_status(
                    self.db, self.project_id, "COMPOSITING", progress=int(progress)
                )

            product_scenes_count = sum(1 for s in ad_project.scenes if s.use_product)
            logger.info(
                f"✅ Composited {len(composited)} videos "
                f"({product_scenes_count} scenes with product, {len(composited) - product_scenes_count} skipped)"
            )
            return composited

        except Exception as e:
            logger.error(f"❌ Compositing failed: {e}")
            raise

    @timed_step("Logo Compositing")
    async def _composite_logos(
        self,
        scene_videos: List[str],
        logo_url: str,
        ad_project: AdProject,
        progress_start: int = 50,
    ) -> List[str]:
        """
        Composite logo onto scenes that have use_logo=True.
        
        Task 4: New method to handle logo compositing per scene.
        """
        try:
            update_project_status(
                self.db, self.project_id, "COMPOSITING_LOGO", progress=progress_start
            )
            
            from app.config import settings
            compositor = Compositor(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region,
            )
            
            # Composite logo only for scenes with use_logo=True
            result = []
            for i, (video_url, scene) in enumerate(zip(scene_videos, ad_project.scenes)):
                if scene.use_logo:
                    position = scene.logo_position or "top_right"
                    scale = scene.logo_scale or 0.1
                    opacity = scene.logo_opacity or 0.9
                    
                    logger.info(f"🏷️  Compositing logo on scene {i}: {position} at {scale*100:.0f}% scale")
                    
                    logo_url_result = await compositor.composite_logo(
                        video_url=video_url,
                        logo_image_url=logo_url,
                        project_id=str(self.project_id),
                        position=position,
                        scale=scale,
                        opacity=opacity,
                        scene_index=i,
                    )
                    result.append(logo_url_result)
                else:
                    # No logo for this scene
                    result.append(video_url)
                    logger.debug(f"Skipping logo for scene {i} (use_logo=False)")
                
                progress = progress_start + (i / len(ad_project.scenes)) * 10
                update_project_status(
                    self.db, self.project_id, "COMPOSITING_LOGO", progress=int(progress)
                )
            
            logo_scenes_count = sum(1 for s in ad_project.scenes if s.use_logo)
            logger.info(
                f"✅ Logo composited on {logo_scenes_count} scenes, "
                f"{len(result) - logo_scenes_count} scenes without logo"
            )
            return result
            
        except Exception as e:
            logger.error(f"❌ Logo compositing failed: {e}")
            # Non-critical - return videos without logo
            logger.warning("Continuing pipeline without logo compositing")
            return scene_videos

    async def _add_text_overlays(
        self, video_urls: List[str], ad_project: AdProject, progress_start: int = 60
    ) -> List[str]:
        """Render text overlays on videos."""
        try:
            update_project_status(
                self.db, self.project_id, "ADDING_OVERLAYS", progress=progress_start
            )

            from app.config import settings
            renderer = TextOverlayRenderer(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region,
            )
            
            # Task 3: Get aspect ratio for proper text positioning
            aspect_ratio = ad_project.video_settings.aspect_ratio if ad_project.video_settings else "16:9"
            logger.info(f"📐 Adding text overlays for {aspect_ratio} aspect ratio")

            # Add overlays to each scene
            overlaid = []
            for i, (video_url, scene) in enumerate(
                zip(video_urls, ad_project.scenes)
            ):
                # Extract overlay properties from scene overlay
                overlay = scene.overlay
                if overlay and overlay.text:
                    overlaid_url = await renderer.add_text_overlay(
                        video_url=video_url,
                        text=overlay.text,
                        position=overlay.position,
                        duration=overlay.duration or scene.duration,
                        start_time=overlay.start_time if hasattr(overlay, 'start_time') else 0.0,
                        font_size=overlay.font_size or 48,
                        color="#FFFFFF",  # Default white color (can be overridden by style_spec in future)
                        animation="fade_in",  # Default animation
                        project_id=str(self.project_id),
                        scene_index=i,  # Pass scene index for unique filenames
                        aspect_ratio=aspect_ratio,  # Task 3: Pass aspect ratio for positioning
                    )
                else:
                    # No overlay, just pass through
                    overlaid_url = video_url
                overlaid.append(overlaid_url)
                progress = progress_start + (i / len(ad_project.scenes)) * 10
                update_project_status(
                    self.db, self.project_id, "ADDING_OVERLAYS", progress=int(progress)
                )

            logger.info(f"✅ Added text overlays to {len(overlaid)} videos")
            return overlaid

        except Exception as e:
            logger.error(f"❌ Text overlay rendering failed: {e}")
            raise

    @timed_step("Audio Generation")
    async def _generate_audio(self, project: Any, ad_project: AdProject, progress_start: int = 75) -> str:
        """Generate background music using MusicGen."""
        try:
            update_project_status(
                self.db, self.project_id, "GENERATING_AUDIO", progress=progress_start
            )

            from app.config import settings
            audio_engine = AudioEngine(
                replicate_api_token=settings.replicate_api_token,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region,
            )
            
            # Get mood from style_spec (set by LLM during planning)
            music_mood = ad_project.style_spec.mood if ad_project.style_spec else "uplifting"
            if hasattr(ad_project.style_spec, 'music_mood'):
                music_mood = ad_project.style_spec.music_mood
            
            # Task 2: Use derived tone to influence music mood if available
            if ad_project.video_metadata and 'derivedTone' in ad_project.video_metadata:
                tone = ad_project.video_metadata['derivedTone']
                music_mood = self._map_tone_to_music_mood(tone, music_mood)
                logger.info(f"🎵 Using tone-derived music mood: {music_mood} (from tone: {tone})")
            else:
                logger.info(f"🎵 Using default music mood: {music_mood}")
            
            # Calculate total duration from scenes
            total_duration = sum(scene.duration for scene in ad_project.scenes) if ad_project.scenes else ad_project.target_duration
            
            audio_url = await audio_engine.generate_background_music(
                mood=music_mood,
                duration=total_duration,
                project_id=str(self.project_id),
            )

            logger.info(f"✅ Generated audio: {audio_url}")
            return audio_url

        except Exception as e:
            logger.error(f"❌ Audio generation failed: {e}")
            raise

    def _normalize_scene_durations(
        self,
        scenes: List[Scene],
        target_duration: int,
        tolerance: float = 0.10
    ) -> List[Scene]:
        """
        Normalize scene durations to match target duration within tolerance.
        
        Task 3: Ensures total video duration matches user's target duration request.
        
        Args:
            scenes: List of scenes with durations
            target_duration: Target total duration in seconds
            tolerance: Acceptable deviation (0.10 = ±10%)
            
        Returns:
            List of scenes with normalized durations
        """
        total_duration = sum(scene.duration for scene in scenes)
        
        # Check if within tolerance
        deviation = abs(total_duration - target_duration) / target_duration if target_duration > 0 else 0
        
        if deviation <= tolerance:
            logger.info(f"✅ Duration within tolerance: {total_duration}s vs {target_duration}s target ({deviation*100:.1f}% deviation)")
            return scenes
        
        # Normalize durations proportionally
        scale_factor = target_duration / total_duration if total_duration > 0 else 1.0
        logger.warning(f"⚠️  Duration outside tolerance: {total_duration}s vs {target_duration}s target ({deviation*100:.1f}% deviation)")
        logger.info(f"📏 Normalizing with scale factor: {scale_factor:.3f}")
        
        normalized_scenes = []
        for scene in scenes:
            new_duration = max(3, min(15, int(scene.duration * scale_factor)))  # Clamp to 3-15s
            
            # Create new scene with updated duration
            scene_dict = scene.model_dump() if hasattr(scene, 'model_dump') else scene.dict()
            scene_dict['duration'] = new_duration
            
            normalized_scenes.append(Scene(**scene_dict))
            logger.debug(f"  Scene {scene.id} ({scene.role}): {scene.duration}s → {new_duration}s")
        
        new_total = sum(s.duration for s in normalized_scenes)
        logger.info(f"✅ Normalized duration: {new_total}s (target: {target_duration}s, {abs(new_total-target_duration)}s diff)")
        
        return normalized_scenes

    def _map_tone_to_music_mood(self, tone: str, default_mood: str) -> str:
        """
        Map derived tone to appropriate music mood for MusicGen.
        
        Args:
            tone: Derived tone from audience (e.g., "warm and reassuring")
            default_mood: Default mood from style_spec
            
        Returns:
            Music mood suitable for MusicGen
        """
        tone_lower = tone.lower()
        
        # Map tone keywords to music moods
        if any(word in tone_lower for word in ['energetic', 'youthful', 'playful', 'vibrant']):
            return 'upbeat'
        elif any(word in tone_lower for word in ['sophisticated', 'luxury', 'exclusive', 'elegant', 'premium']):
            return 'elegant'
        elif any(word in tone_lower for word in ['warm', 'reassuring', 'caring', 'supportive', 'calm']):
            return 'calm'
        elif any(word in tone_lower for word in ['confident', 'powerful', 'bold', 'strong', 'commanding']):
            return 'dramatic'
        elif any(word in tone_lower for word in ['motivating', 'inspiring', 'uplifting', 'positive']):
            return 'uplifting'
        elif any(word in tone_lower for word in ['modern', 'tech', 'innovative', 'futuristic']):
            return 'electronic'
        else:
            logger.info(f"No tone mapping found for '{tone}', using default mood: {default_mood}")
            return default_mood

    @timed_step("Final Rendering")
    async def _render_final(
        self,
        scene_videos: List[str],
        audio_url: str,
        ad_project: AdProject,
        progress_start: int = 85,
    ) -> Dict[str, str]:
        """Render final multi-aspect videos."""
        try:
            update_project_status(
                self.db, self.project_id, "RENDERING", progress=progress_start
            )

            from app.config import settings
            renderer = Renderer(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region,
            )
            
            # Get project from database to retrieve stored aspect_ratio
            project = get_project(self.db, self.project_id)
            # Use the aspect ratio specified when project was created
            output_aspect_ratios = [project.aspect_ratio] if project.aspect_ratio else ["16:9"]
            
            final_videos = await renderer.render_final_video(
                scene_video_urls=scene_videos,
                audio_url=audio_url,
                project_id=str(self.project_id),
                output_aspect_ratios=output_aspect_ratios,
            )

            update_project_status(
                self.db, self.project_id, "RENDERING", progress=100
            )

            logger.info(f"✅ Rendered final videos: {final_videos.keys()}")
            
            # NOTE: Intermediate files are kept for Phase 2 (editing)
            # They will be deleted when user exports final video in Phase 2
            # See _cleanup_intermediate_files() method for cleanup logic
            
            return final_videos

        except Exception as e:
            logger.error(f"❌ Final rendering failed: {e}")
            raise
    
    async def _cleanup_intermediate_files(self, project_id: str) -> None:
        """
        Delete intermediate S3 files after user exports final video.
        
        Called during Phase 2 export when user is done editing.
        Keeps only the final output video (16:9).
        
        Deletes:
        - scene_*.mp4 (individual generated clips)
        - scene_*_composited.mp4 (product overlay versions)
        - scene_*_overlaid.mp4 (text overlay versions)
        - music_*.mp3 (background music file)
        
        Keeps:
        - final_9_16.mp4
        - final_1_1.mp4
        - final_16_9.mp4
        
        This reduces S3 storage from ~950MB to ~150MB per project.
        """
        try:
            from app.config import settings
            
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
            
            # List all objects in project folder
            prefix = f"projects/{project_id}/"
            response = s3_client.list_objects_v2(
                Bucket=settings.s3_bucket_name,
                Prefix=prefix
            )
            
            if "Contents" not in response:
                return
            
            # Files to keep (the final outputs)
            keep_files = {"final_9_16.mp4", "final_1_1.mp4", "final_16_9.mp4"}
            
            # Delete all other files
            deleted_count = 0
            for obj in response.get("Contents", []):
                key = obj["Key"]
                filename = key.split("/")[-1]
                
                if filename not in keep_files:
                    s3_client.delete_object(
                        Bucket=settings.s3_bucket_name,
                        Key=key
                    )
                    deleted_count += 1
                    logger.debug(f"Deleted intermediate: {filename}")
            
            logger.info(f"✅ Cleaned up {deleted_count} intermediate files from S3")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup intermediate files: {e}")
            # Don't fail the pipeline if cleanup fails

    async def _save_final_video_locally(
        self, s3_video_url: str, aspect_ratio: str
    ) -> str:
        """Download final video from S3 and save to local storage.
        
        Args:
            s3_video_url: S3 URL of the rendered video
            aspect_ratio: Video aspect ratio (16:9)
            
        Returns:
            Local file path
        """
        try:
            import requests
            import os
            
            logger.info(f"⬇️ Downloading {aspect_ratio} video from S3...")
            
            # Download from S3 URL
            response = requests.get(s3_video_url, timeout=300)
            response.raise_for_status()
            
            # Save to local storage
            local_path = LocalStorageManager.save_final_video(
                self.project_id,
                aspect_ratio,
                None  # We'll write bytes instead of copying
            )
            
            # Create parent directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Write video bytes to local file
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(local_path)
            logger.info(f"✅ Saved {aspect_ratio} ({file_size / 1024 / 1024:.1f} MB) to {local_path}")
            
            return local_path
            
        except Exception as e:
            logger.error(f"❌ Failed to save {aspect_ratio} video locally: {e}")
            raise


def generate_video(project_id: str) -> Dict[str, Any]:
    """
    RQ job function for video generation.
    
    This is the entry point called by RQ worker.
    Runs in a forked child process on macOS.
    
    Args:
        project_id: String UUID of project to generate
        
    Returns:
        Dict with generation results
    """
    try:
        # Ensure environment variable is set (should be set by shell script)
        import os
        os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
        
        # Reinitialize database connection in child process
        # This ensures we don't reuse connections from parent
        from app.database.connection import init_db
        init_db()
        
        logger.info(f"🚀 Starting generation pipeline for project {project_id}")
        project_uuid = UUID(project_id)
        pipeline = GenerationPipeline(project_uuid)
        
        # Handle event loop properly for RQ
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(pipeline.run())
        return result
    except KeyboardInterrupt:
        logger.warning(f"⚠️ Generation interrupted for project {project_id}")
        raise
    except Exception as e:
        logger.error(f"❌ RQ job failed for project {project_id}: {e}", exc_info=True)
        return {
            "status": "FAILED",
            "project_id": project_id,
            "error": str(e),
        }

