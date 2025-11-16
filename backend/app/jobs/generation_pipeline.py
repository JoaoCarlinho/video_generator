"""RQ Background job for end-to-end video generation pipeline.

This module contains the main generation pipeline that orchestrates all services:
1. Product Extraction (remove background)
2. Scene Planning (LLM-based)
3. Video Generation (parallel for all scenes)
4. Compositing (product overlay)
5. Text Overlay Rendering
6. Audio Generation (MusicGen)
7. Multi-Aspect Rendering (9:16, 1:1, 16:9)

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
from app.utils.s3_utils import (
    create_project_folder_structure,
    delete_project_folder,
    upload_to_project_folder,
)
from app.utils.local_storage import LocalStorageManager, format_storage_size

logger = logging.getLogger(__name__)

# Cost constants (in USD, based on API documentation)
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

            # ===== STEP 3: Generate Videos (Parallel) =====
            logger.info("🎥 Step 3: Generating videos for all scenes...")
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
            if product_url:
                logger.info("🎨 Step 4: Compositing product onto scenes...")
                composited_videos = await self._composite_products(
                    scene_videos, product_url, ad_project, progress_start=40
                )
                self.step_costs["compositing"] = COST_COMPOSITING
                self.total_cost += COST_COMPOSITING
            else:
                logger.info("🎨 Step 4: Skipping compositing (no product image)")
                composited_videos = scene_videos  # Use background videos as-is

            # ===== STEP 5: Add Text Overlays =====
            logger.info("📝 Step 5: Rendering text overlays...")
            overlay_start = 60 if has_product else 50
            text_rendered_videos = await self._add_text_overlays(
                composited_videos, ad_project, progress_start=overlay_start
            )
            self.step_costs["text_overlay"] = COST_TEXT_OVERLAY
            self.total_cost += COST_TEXT_OVERLAY

            # ===== STEP 6: Generate Audio =====
            logger.info("🎵 Step 6: Generating background music...")
            audio_start = 75 if has_product else 70
            audio_url = await self._generate_audio(project, ad_project, progress_start=audio_start)
            self.step_costs["audio"] = COST_MUSIC_GENERATION
            self.total_cost += COST_MUSIC_GENERATION

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
            }

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}", exc_info=True)

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
            
            # Prepare brand colors
            brand_colors = [ad_project.brand.primary_color]
            if ad_project.brand.secondary_color:
                brand_colors.append(ad_project.brand.secondary_color)
            
            # Check if product/logo are available
            has_product = ad_project.product_asset is not None and ad_project.product_asset.original_url
            has_logo = ad_project.brand.logo_url is not None
            
            # TODO: Load brand guidelines from S3 if guidelines_url is present
            brand_guidelines = None
            if ad_project.brand.guidelines_url:
                # For now, we'll skip loading the guidelines text
                # In production, you'd download and parse the file from S3
                logger.info(f"Brand guidelines URL provided: {ad_project.brand.guidelines_url}")
            
            plan = await planner.plan_scenes(
                creative_prompt=ad_project.creative_prompt,
                brand_name=ad_project.brand.name,
                brand_description=ad_project.brand.description,
                brand_colors=brand_colors,
                brand_guidelines=brand_guidelines,
                target_audience=ad_project.target_audience or "general consumers",
                target_duration=ad_project.target_duration,
                has_product=has_product,
                has_logo=has_logo,
            )

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
                    ) if scene.overlay else None,
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
        """Generate background videos for all scenes in parallel."""
        try:
            update_project_status(
                self.db, self.project_id, "GENERATING_SCENES", progress=progress_start
            )

            from app.config import settings
            generator = VideoGenerator(api_token=settings.replicate_api_token)

            # Create tasks for all scenes
            tasks = [
                generator.generate_scene_background(
                    prompt=scene.background_prompt,
                    style_spec_dict=ad_project.style_spec.dict() if hasattr(ad_project.style_spec, 'dict') else ad_project.style_spec,
                    duration=scene.duration,
                )
                for scene in ad_project.scenes
            ]

            # Run all tasks concurrently
            scene_videos = await asyncio.gather(*tasks)

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
                        color=ad_project.brand.primary_color,  # Use brand primary color
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
            final_videos = await renderer.render_final_video(
                scene_video_urls=scene_videos,
                audio_url=audio_url,
                project_id=str(self.project_id),
                output_aspect_ratios=["9:16", "1:1", "16:9"],
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
        Keeps only the final 3 output videos (9:16, 1:1, 16:9).
        
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
            aspect_ratio: Video aspect ratio (9:16, 1:1, 16:9)
            
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

