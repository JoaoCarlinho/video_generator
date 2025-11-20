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
import boto3
from uuid import UUID
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime

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

    async def run(self) -> Dict[str, Any]:
        """Execute the full generation pipeline.
        
        Returns:
            Dict with pipeline results including final video URLs and cost breakdown
            
        Raises:
            Exception: If any critical step fails (caught and logged)
        """
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

            # ===== STEP 5: Add Text Overlays =====
            # Note: Music is still generating in background
            logger.info("📝 Step 5: Rendering text overlays (music still generating)...")
            overlay_start = 60 if has_product else 50
            text_rendered_videos = await self._add_text_overlays(
                composited_videos, ad_project, progress_start=overlay_start
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

            logger.info(f"✅ Pipeline complete! Total cost: ${self.total_cost:.2f}")
            logger.info(f"💰 Cost breakdown: {self.step_costs}")

            # ===== UPLOAD TO S3: Upload final videos to S3 for preview =====
            logger.info("📤 Uploading final videos to S3...")
            from app.utils.s3_utils import upload_video_to_s3

            # Renderer returns local paths, upload each to S3
            local_video_paths = final_videos
            s3_video_urls = {}

            for aspect_ratio, local_path in local_video_paths.items():
                try:
                    s3_result = upload_video_to_s3(
                        local_video_path=local_path,
                        project_id=str(self.project_id),
                        aspect_ratio=aspect_ratio
                    )
                    s3_video_urls[aspect_ratio] = s3_result["url"]
                    logger.info(f"✅ Uploaded {aspect_ratio} video to S3: {s3_result['s3_key']}")
                except Exception as e:
                    logger.error(f"❌ Failed to upload {aspect_ratio} video to S3: {e}")
                    # Continue with local path if S3 upload fails
                    s3_video_urls[aspect_ratio] = None

            # Calculate local storage size
            storage_size = LocalStorageManager.get_project_storage_size(self.project_id)
            logger.info(f"📊 Total local storage: {format_storage_size(storage_size)}")

            # Update project with both local paths and S3 URLs
            project.local_video_paths = local_video_paths
            project.output_videos = s3_video_urls  # S3 URLs for serving
            project.status = 'COMPLETED'
            self.db.commit()

            logger.info(f"✅ Project ready for preview. Videos uploaded to S3.")

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
            }

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}", exc_info=True)

            # Cancel music task if it's still running (from parallel execution)
            if 'music_task' in locals() and not music_task.done():
                logger.info("🚫 Cancelling background music generation task...")
                music_task.cancel()
                try:
                    await music_task
                except asyncio.CancelledError:
                    logger.info("✅ Music task cancelled successfully")

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
            }

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

    async def _plan_scenes(self, project: Any, ad_project: AdProject, progress_start: int = 15) -> Any:
        """Plan scenes using LLM and generate style spec."""
        try:
            update_project_status(
                self.db, self.project_id, "PLANNING", progress=progress_start
            )

            from app.config import settings
            planner = ScenePlanner(api_key=settings.openai_api_key)
            
            # Brand colors are now determined by LLM during scene planning
            # based on creative prompt and brand guidelines
            brand_colors = []
            # Check if reference image style was extracted
            extracted_style = None
            if project.ad_project_json:
                extracted_style = project.ad_project_json.get("referenceImage", {}).get("extractedStyle")
                if extracted_style:
                    brand_colors = extracted_style.get("colors", [])
                    logger.info(f"🎨 Using colors from reference image: {brand_colors}")

            # STORY 3: Check if product/logo are available (support multiple product images)
            has_product = (ad_project.product_asset is not None and ad_project.product_asset.original_url) or \
                          (ad_project.product_images is not None and len(ad_project.product_images) > 0)
            has_logo = ad_project.brand.logo_url is not None

            # STORY 3: Prepare product reference images for scene planner
            # First image is primary, rest are references for AI understanding
            product_reference_images = ad_project.product_images if ad_project.product_images else []
            if ad_project.product_asset and ad_project.product_asset.original_url:
                # Backward compatibility: include product_asset as primary if no product_images
                if not product_reference_images:
                    product_reference_images = [ad_project.product_asset.original_url]
            
            # TODO: Load brand guidelines from S3 if guidelines_url is present
            brand_guidelines = None
            if ad_project.brand.guidelines_url:
                # For now, we'll skip loading the guidelines text
                # In production, you'd download and parse the file from S3
                logger.info(f"Brand guidelines URL provided: {ad_project.brand.guidelines_url}")
            
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
            
            # PHASE 7: Pass selected_style to ScenePlanner
            plan = await planner.plan_scenes(
                creative_prompt=creative_prompt,
                brand_name=ad_project.brand.name,
                brand_description=ad_project.brand.description,
                brand_colors=brand_colors,
                brand_guidelines=brand_guidelines,
                target_audience=ad_project.target_audience or "general consumers",
                target_duration=ad_project.target_duration,
                has_product=has_product,
                has_logo=has_logo,
                aspect_ratio=ad_project.video_settings.aspect_ratio,
                selected_style=project.selected_style,  # PHASE 7: Pass user-selected style if any
            )

            # PHASE 7: plan_scenes now returns AdProjectPlan instance
            chosen_style = plan.chosen_style
            style_source = plan.style_source

            logger.info(f"✅ ScenePlanner chose style: {chosen_style} ({style_source})")

            # Update ad_project with scenes and style spec from plan
            # Convert plan scenes to AdProject scenes format
            from app.models.schemas import Overlay, Scene as AdProjectScene
            ad_project.scenes = [
                AdProjectScene(
                    id=str(scene.scene_id),
                    role=scene.role,
                    duration=scene.duration,
                    description=scene.background_prompt,
                    background_prompt=scene.background_prompt,
                    background_type=scene.background_type,
                    use_product=scene.use_product,
                    use_logo=scene.use_logo,
                    product_usage="static_insert" if scene.use_product else "none",
                    camera_movement=scene.camera_movement,
                    transition_to_next=scene.transition_to_next,
                    overlay=Overlay(
                        text=scene.overlay.text,
                        position=scene.overlay.position,
                        font_size=scene.overlay.font_size,
                        duration=scene.overlay.duration,
                    ) if scene.overlay.text else None,
                )
                for scene in plan.scenes
            ]
            # Convert StyleSpec from plan to AdProject StyleSpec format
            ad_project.style_spec = StyleSpec(
                lighting=plan.style_spec.lighting_direction,
                camera_style=plan.style_spec.camera_style,
                mood=plan.style_spec.mood_atmosphere,
                color_palette=plan.style_spec.color_palette,
                texture=plan.style_spec.texture_materials,
                grade=plan.style_spec.grade_postprocessing,
            )

            # PHASE 7: Store chosen style in ad_project_json
            if not ad_project.video_metadata:
                ad_project.video_metadata = {}
            ad_project.video_metadata['selectedStyle'] = {
                'style': chosen_style,
                'source': style_source,
                'appliedAt': datetime.utcnow().isoformat()
            }

            # Save back to database
            project.ad_project_json = ad_project.dict()
            self.db.commit()

            logger.info(f"✅ Planned {len(ad_project.scenes)} scenes with style spec")
            return project

        except Exception as e:
            logger.error(f"❌ Scene planning failed: {e}")
            raise

    async def _generate_scene_videos(
        self, project: Any, ad_project: AdProject, progress_start: int = 25
    ) -> List[str]:
        """Generate background videos for all scenes in parallel.

        STORY 3 (AC#5): For scenes with custom backgrounds, use uploaded image instead of AI generation.
        """
        try:
            update_project_status(
                self.db, self.project_id, "GENERATING_SCENES", progress=progress_start
            )

            from app.config import settings
            generator = VideoGenerator(api_token=settings.replicate_api_token)

            # STORY 3: Build scene background mapping for quick lookup
            scene_background_map = {}
            if ad_project.scene_backgrounds:
                for sb in ad_project.scene_backgrounds:
                    scene_background_map[sb.get('scene_id')] = sb.get('background_url')

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

            # Create tasks for all scenes
            tasks = []
            for scene in ad_project.scenes:
                # STORY 3 (AC#5): Check if this scene has a custom background
                custom_bg_url = scene_background_map.get(scene.id)

                if custom_bg_url:
                    # Use custom background - just return the URL (no AI generation needed)
                    logger.info(f"Scene {scene.id}: Using custom background {custom_bg_url}")
                    # Create a coroutine that returns the custom URL directly
                    async def return_custom_bg(url=custom_bg_url):
                        return url
                    tasks.append(return_custom_bg())
                else:
                    # Generate AI background as normal
                    tasks.append(
                        generator.generate_scene_background(
                            prompt=scene.background_prompt,
                            style_spec_dict=ad_project.style_spec.dict() if hasattr(ad_project.style_spec, 'dict') else ad_project.style_spec,
                            duration=scene.duration,
                            extracted_style=extracted_style,
                            style_override=chosen_style,
                        )
                    )

            # Run all tasks concurrently
            scene_videos = await asyncio.gather(*tasks)

            logger.info(f"✅ Generated {len(scene_videos)} videos ({len(scene_background_map)} custom backgrounds)")
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

    async def _composite_products(
        self,
        scene_videos: List[str],
        product_url: str,
        ad_project: AdProject,
        progress_start: int = 40,
    ) -> List[str]:
        """Composite product onto each scene video."""
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

            # Composite for each scene
            composited = []
            for i, (video_url, scene) in enumerate(zip(scene_videos, ad_project.scenes)):
                composited_url = await compositor.composite_product(
                    background_video_url=video_url,
                    product_image_url=product_url,
                    project_id=str(self.project_id),
                    position=getattr(scene, 'position', 'center'),
                    scale=getattr(scene, 'scale', 0.3),
                    scene_index=i,  # Pass scene index for unique filenames
                )
                composited.append(composited_url)
                progress = progress_start + (i / len(ad_project.scenes)) * 15
                update_project_status(
                    self.db, self.project_id, "COMPOSITING", progress=int(progress)
                )

            logger.info(f"✅ Composited {len(composited)} videos")
            return composited

        except Exception as e:
            logger.error(f"❌ Compositing failed: {e}")
            raise

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
            
            # STORY 3 (AC#6): Get project from database to retrieve output_formats
            project = get_project(self.db, self.project_id)

            # Use output_formats array if available, fall back to aspect_ratio for backward compat
            if project.output_formats and len(project.output_formats) > 0:
                output_aspect_ratios = project.output_formats
            elif project.aspect_ratio:
                output_aspect_ratios = [project.aspect_ratio]
            else:
                output_aspect_ratios = ["16:9"]  # Default fallback

            logger.info(f"Rendering {len(output_aspect_ratios)} aspect ratios: {output_aspect_ratios}")

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

