"""RQ Background job for end-to-end luxury perfume TikTok video generation pipeline.

This module contains the main generation pipeline that orchestrates all services:
1. Product Extraction (remove background)
2. Scene Planning (LLM-based with perfume shot grammar constraints)
3. Video Generation (parallel for all scenes, TikTok vertical 9:16 only)
4. Compositing (product overlay)
5. Text Overlay Rendering (luxury typography)
6. Audio Generation (luxury ambient music)
7. Final Rendering (TikTok vertical 9:16 only)

PERFUME-SPECIFIC FEATURES (Phase 8):
- Perfume shot grammar validation
- Perfume name extraction and storage
- Grammar compliance checking
- TikTok vertical optimization (9:16 hardcoded)

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


def timed_step(step_name: str):
    """Decorator to time pipeline steps."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            logger.info(f"Starting step: {step_name}")
            
            try:
                result = await func(self, *args, **kwargs)
                elapsed = time.time() - start_time
                
                if hasattr(self, 'step_timings'):
                    self.step_timings[step_name] = elapsed
                
                logger.info(f"Step complete: {step_name} ({elapsed:.1f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Step failed: {step_name} ({elapsed:.1f}s) - {str(e)}")
                raise
        
        return wrapper
    return decorator


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
        self.step_timings: Dict[str, float] = {}

    async def run(self) -> Dict[str, Any]:
        """Execute the full generation pipeline.
        
        Returns:
            Dict with pipeline results including final video URLs and timings
            
        Raises:
            Exception: If any critical step fails
        """
        pipeline_start = time.time()
        music_task = None
        
        try:
            logger.info(f"Starting generation pipeline for project {self.project_id}")

            # Load project from database
            project = get_project(self.db, self.project_id)
            if not project:
                raise ValueError(f"Project {self.project_id} not found")

            # Initialize local storage
            logger.info("Initializing local storage...")
            try:
                local_paths = LocalStorageManager.initialize_project_storage(self.project_id)
                self.local_paths = local_paths
                storage_info = LocalStorageManager.get_project_storage_size(self.project_id)
                logger.info(f"Local storage initialized: {self.local_paths}")
            except Exception as e:
                logger.error(f"Failed to initialize local storage: {e}")
                raise

            # Initialize S3 project folder structure
            logger.info("Initializing S3 project folder structure...")
            try:
                folders = await create_project_folder_structure(str(self.project_id))
                update_project_s3_paths(
                    self.db,
                    self.project_id,
                    folders["s3_folder"],
                    folders["s3_url"]
                )
                logger.info(f"S3 folders initialized at {folders['s3_url']}")
                self.s3_folders = folders
            except Exception as e:
                logger.error(f"Failed to initialize S3 folders: {e}")
                self.s3_folders = None

            # Parse AdProject JSON
            # Ensure ad_project_json is a dict (handle JSONB/string cases)
            project_json = project.ad_project_json
            if isinstance(project_json, str):
                import json
                project_json = json.loads(project_json)
            elif not isinstance(project_json, dict):
                raise ValueError(f"Invalid ad_project_json type: {type(project_json)}")
            
            # Ensure video_metadata exists in the JSON
            if 'video_metadata' not in project_json:
                project_json['video_metadata'] = {}
            
            ad_project = AdProject(**project_json)

            # STEP 0: Extract Reference Image Style (Optional)
            logger.info("Step 0: Checking for reference image...")
            has_reference = False
            if project.ad_project_json:
                reference_local_path = project.ad_project_json.get("referenceImage", {}).get("localPath")
                
                if reference_local_path:
                    import os
                    if os.path.exists(reference_local_path):
                        has_reference = True
                        logger.info("Extracting visual style from reference image...")
                        
                        try:
                            from openai import AsyncOpenAI
                            from app.config import settings
                            
                            openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                            extractor = ReferenceImageStyleExtractor(openai_client)
                            
                            brand_name = project.ad_project_json.get("brand", {}).get("name", "Brand") if isinstance(project.ad_project_json, dict) else "Brand"
                            extracted_style = await extractor.extract_style(
                                image_path=reference_local_path,
                                brand_name=brand_name
                            )
                            
                            project.ad_project_json["referenceImage"]["extractedStyle"] = extracted_style.to_dict()
                            project.ad_project_json["referenceImage"]["extractedAt"] = datetime.now().isoformat()
                            self.db.commit()
                            
                            # Reload project to get updated JSON
                            project = get_project(self.db, self.project_id)
                            project_json = project.ad_project_json
                            if isinstance(project_json, str):
                                import json
                                project_json = json.loads(project_json)
                            elif not isinstance(project_json, dict):
                                raise ValueError(f"Invalid ad_project_json type: {type(project_json)}")
                            
                            if 'video_metadata' not in project_json:
                                project_json['video_metadata'] = {}
                            
                            ad_project = AdProject(**project_json)
                            
                            os.unlink(reference_local_path)
                            logger.info("Reference style extracted and temp file deleted")
                            
                        except Exception as e:
                            logger.warning(f"Failed to extract reference style: {e}")
                            has_reference = False
                    else:
                        logger.info(f"Reference image file not found: {reference_local_path}")
                else:
                    logger.info("No reference image provided")
            else:
                logger.info("No ad_project_json available")

            # STEP 1: Extract Product (Optional)
            product_url = None
            has_product = ad_project.product_asset is not None and (ad_project.product_asset.get('original_url') if isinstance(ad_project.product_asset, dict) else False)
            
            if has_product:
                logger.info("Step 1: Extracting product...")
                product_url = await self._extract_product(project, ad_project)
            else:
                logger.info("Step 1: Skipping product extraction (no product image provided)")

            # STEP 2: Plan Scenes
            planning_start = 15 if has_product else 10
            logger.info("Step 2: Planning scenes...")
            updated_project = await self._plan_scenes(project, ad_project, progress_start=planning_start)

            # Update project with new ad_project data
            ad_project = AdProject(**updated_project.ad_project_json)

            # STEP 3A: Spawn Music Generation (parallel with video)
            logger.info("Step 3A: Spawning background music generation...")
            music_task = asyncio.create_task(
                self._generate_audio(project, ad_project, progress_start=30)
            )

            # STEP 3B: Generate Videos (parallel with music)
            logger.info("Step 3B: Generating videos for all scenes...")
            video_start = 25 if has_product else 20
            replicate_videos = await self._generate_scene_videos(project, ad_project, progress_start=video_start)
            
            logger.info("Saving videos to local storage...")
            scene_videos = await self._save_videos_locally(replicate_videos, str(self.project_id))
            logger.info(f"Saved {len(scene_videos)} videos to local storage")

            # STEP 4: Composite Product (Optional)
            if product_url:
                logger.info("Step 4: Compositing product onto scenes...")
                composited_videos = await self._composite_products(
                    scene_videos, product_url, ad_project, progress_start=40
                )
            else:
                logger.info("Step 4: Skipping compositing (no product image)")
                composited_videos = scene_videos

            # STEP 4B: Composite Logo (Optional)
            logo_url = ad_project.brand.get('logo_url') if isinstance(ad_project.brand, dict) else None
            if logo_url:
                logger.info("Step 4B: Compositing logo onto scenes...")
                logo_composited_videos = await self._composite_logos(
                    composited_videos,
                    logo_url,
                    ad_project,
                    progress_start=55 if product_url else 50
                )
            else:
                logger.info("Step 4B: Skipping logo compositing (no logo provided)")
                logo_composited_videos = composited_videos

            # STEP 5: Add Text Overlays
            logger.info("Step 5: Rendering text overlays...")
            overlay_start = 65 if (product_url or logo_url) else 50
            text_rendered_videos = await self._add_text_overlays(
                logo_composited_videos, ad_project, progress_start=overlay_start
            )

            # STEP 6: Wait for Music Generation
            logger.info("Step 6: Waiting for background music generation to complete...")
            try:
                audio_url = await music_task
                logger.info(f"Background music generation complete: {audio_url}")
            except asyncio.CancelledError:
                logger.error("Music generation was cancelled")
                raise
            except Exception as e:
                logger.error(f"Music generation failed: {e}", exc_info=True)
                # Ensure task exception is retrieved to avoid "Task exception was never retrieved" warning
                if music_task.done() and music_task.exception():
                    logger.debug(f"Task exception details: {music_task.exception()}")
                raise

            # STEP 7: Render Final TikTok Vertical Video (9:16 only)
            logger.info("Step 7: Rendering final TikTok vertical video (9:16)...")
            render_start = 85 if has_product else 80
            final_video_path = await self._render_final(
                text_rendered_videos, audio_url, ad_project, progress_start=render_start
            )

            total_elapsed = time.time() - pipeline_start
            logger.info(f"Pipeline complete in {total_elapsed:.1f}s")
            logger.info(f"Step timings: {self.step_timings}")

            # ===== LOCAL-FIRST: Final video already saved locally by renderer =====
            logger.info("Final TikTok vertical video already saved to local storage by renderer")
            # Store as dict with single 9:16 entry for backward compatibility
            local_video_paths = {"9:16": final_video_path}

            # Calculate local storage size
            storage_size = LocalStorageManager.get_project_storage_size(self.project_id)
            logger.info(f"Total local storage: {format_storage_size(storage_size)}")

            # Update project with local path
            project.local_video_paths = local_video_paths  # Backward compat (deprecated)
            project.local_video_path = final_video_path  # Phase 9: Single TikTok vertical video path
            project.aspect_ratio = "9:16"  # Set default aspect ratio
            project.status = 'COMPLETED'
            self.db.commit()

            logger.info(f"Project ready for preview. TikTok vertical video stored locally.")

            # Update legacy output_videos field for backward compatibility
            update_project_output(
                self.db,
                self.project_id,
                {},
                0.0,
                {},
            )

            return {
                "status": "COMPLETED",
                "project_id": str(self.project_id),
                "local_video_paths": local_video_paths,  # Backward compat (deprecated)
                "local_video_path": final_video_path,  # Phase 9: Single TikTok vertical video path
                "storage_size": storage_size,
                "storage_size_formatted": format_storage_size(storage_size),
                "message": "TikTok vertical video ready for preview. Video stored in local storage.",
                "timing_seconds": total_elapsed,
                "step_timings": self.step_timings,
            }

        except Exception as e:
            total_elapsed = time.time() - pipeline_start
            logger.error(f"Pipeline failed after {total_elapsed:.1f}s: {e}", exc_info=True)

            # Handle background music task (cancel if running, retrieve exception if failed)
            if music_task is not None:
                if music_task.done():
                    # Task already completed - retrieve exception if it failed
                    try:
                        await music_task  # This will raise if task failed
                    except Exception as task_error:
                        logger.warning(f"Music task had exception: {task_error}")
                else:
                    # Task still running - cancel it
                    logger.info("Cancelling background music generation task...")
                    music_task.cancel()
                    try:
                        await music_task
                    except asyncio.CancelledError:
                        logger.info("Music task cancelled successfully")
                    except Exception as cancel_error:
                        logger.warning(f"Error cancelling music task: {cancel_error}")

            # Cleanup partial files
            try:
                logger.info("Attempting to cleanup partial files...")
                LocalStorageManager.cleanup_project_storage(self.project_id)
                logger.info("Cleanup completed")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup storage: {cleanup_error}")

            # Mark project as failed
            error_msg = str(e)[:500]
            update_project_status(
                self.db,
                self.project_id,
                "FAILED",
                error_message=error_msg,
            )

            return {
                "status": "FAILED",
                "project_id": str(self.project_id),
                "error": error_msg,
                "timing_seconds": total_elapsed,
                "step_timings": self.step_timings,
            }

    @timed_step("Product Extraction")
    async def _extract_product(
        self, project: Any, ad_project: AdProject
    ) -> str:
        """Extract product from uploaded image using rembg."""
        try:
            update_project_status(
                self.db, self.project_id, "EXTRACTING_PRODUCT", progress=10
            )

            product_asset = ad_project.product_asset
            if not product_asset or not (product_asset.get('original_url') if isinstance(product_asset, dict) else None):
                raise ValueError("Product asset not found or missing original_url")
            
            product_image_url = product_asset.get('original_url') if isinstance(product_asset, dict) else None
            
            from app.config import settings
            extractor = ProductExtractor(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region,
            )
            
            product_url = await extractor.extract_product(
                image_url=product_image_url,
                project_id=str(self.project_id),
            )

            logger.info(f"Product extracted: {product_url}")
            return product_url

        except Exception as e:
            logger.error(f"Product extraction failed: {e}")
            raise

    @timed_step("Scene Planning")
    async def _plan_scenes(self, project: Any, ad_project: AdProject, progress_start: int = 15) -> Any:
        """Plan perfume scenes using LLM with shot grammar constraints."""
        try:
            update_project_status(
                self.db, self.project_id, "PLANNING", progress=progress_start
            )

            from app.config import settings
            planner = ScenePlanner(api_key=settings.openai_api_key)
            
            # Extract perfume-specific info (Phase 9)
            # First check ad_project (from schema), then fallback to ad_project_json
            perfume_name = getattr(ad_project, 'perfume_name', None) or None
            if not perfume_name and project.ad_project_json and isinstance(project.ad_project_json, dict):
                perfume_name = project.ad_project_json.get("perfume_name")
            # Fallback to brand name if perfume_name not available
            if not perfume_name:
                perfume_name = ad_project.brand.get('name', 'Perfume') if isinstance(ad_project.brand, dict) else 'Perfume'
            logger.info(f"Using perfume name: {perfume_name}")
            
            # Brand colors from LLM or reference image if available
            brand_colors = []
            
            # Check if reference image style was extracted
            extracted_style = None
            if project.ad_project_json:
                extracted_style = project.ad_project_json.get("referenceImage", {}).get("extractedStyle")
                if extracted_style:
                    brand_colors = extracted_style.get("colors", [])
                    logger.info(f"Using colors from reference image: {brand_colors}")
            
            # Check if product/logo are available
            has_product = ad_project.product_asset is not None and ad_project.product_asset.get('original_url') if isinstance(ad_project.product_asset, dict) else False
            has_logo = ad_project.brand.get('logo_url') is not None if isinstance(ad_project.brand, dict) else False
            
            # Extract Brand Guidelines (Optional)
            extracted_guidelines = None
            guidelines_url = ad_project.brand.get('guidelines_url') if isinstance(ad_project.brand, dict) else None
            if guidelines_url:
                logger.info("Extracting brand guidelines from document...")
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
                        guidelines_url=guidelines_url,
                        brand_name=ad_project.brand.get('name', '') if isinstance(ad_project.brand, dict) else ''
                    )
                    
                    if extracted_guidelines:
                        logger.info(
                            f"Extracted guidelines: {len(extracted_guidelines.color_palette)} colors, "
                            f"tone='{extracted_guidelines.tone_of_voice}'"
                        )
                        if ad_project.video_metadata is None:
                            ad_project.video_metadata = {}
                        ad_project.video_metadata['extractedGuidelines'] = extracted_guidelines.to_dict()
                    else:
                        logger.warning("Guidelines extraction returned None, continuing without")
                    
                except Exception as e:
                    logger.error(f"Guidelines extraction failed: {e}")
                    logger.warning("Continuing pipeline without brand guidelines")
                    extracted_guidelines = None
            else:
                logger.info("No brand guidelines URL provided, skipping")
            
            # Merge colors from guidelines into brand_colors
            if extracted_guidelines and extracted_guidelines.color_palette:
                brand_colors.extend(extracted_guidelines.color_palette)
                brand_colors = list(set(brand_colors))
                logger.info(f"Merged brand colors from guidelines: {brand_colors}")
            
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
            
            # Add brand guidelines context to creative prompt
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
            
            plan = await planner.plan_scenes(
                creative_prompt=creative_prompt,
                brand_name=ad_project.brand.get('name', '') if isinstance(ad_project.brand, dict) else '',
                brand_description=ad_project.brand.get('description', '') if isinstance(ad_project.brand, dict) else '',
                brand_colors=brand_colors,
                brand_guidelines=extracted_guidelines.to_dict() if extracted_guidelines else None,
                target_audience=ad_project.target_audience or "general consumers",
                target_duration=ad_project.target_duration,
                has_product=has_product,
                has_logo=has_logo,
                selected_style=project.selected_style,
                extracted_style=extracted_style,
                perfume_name=perfume_name,
                perfume_gender=ad_project.perfume_gender if hasattr(ad_project, 'perfume_gender') else None,
            )

            chosen_style = plan.get('chosenStyle')
            style_source = plan.get('styleSource')
            plan_scenes_list = plan.get('scenes', [])
            plan_style_spec = plan.get('style_spec', {})
            
            logger.info(f"ScenePlanner chose style: {chosen_style} ({style_source})")
            
            # PHASE 8: Validate grammar compliance
            from app.services.perfume_grammar_loader import PerfumeGrammarLoader
            grammar_loader = PerfumeGrammarLoader()
            
            is_valid, violations = grammar_loader.validate_scene_plan(plan_scenes_list)
            
            if not is_valid:
                logger.warning(f"⚠️ Grammar violations detected: {violations}")

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
                    style=scene.get('style', chosen_style),
                    
                    use_product=scene.get('use_product', False),
                    product_usage=scene.get('product_usage', 'static_insert'),
                    product_position=scene.get('product_position', 'center'),
                    product_scale=scene.get('product_scale', 0.3),
                    product_opacity=scene.get('product_opacity', 1.0),
                    
                    use_logo=scene.get('use_logo', False),
                    logo_position=scene.get('logo_position', 'top_right'),
                    logo_scale=scene.get('logo_scale', 0.1),
                    logo_opacity=scene.get('logo_opacity', 0.9),
                    
                    camera_movement=scene.get('camera_movement', 'static'),
                    transition_to_next=scene.get('transition_to_next', 'cut'),
                    safe_zone=scene.get('safe_zone'),
                    overlay_preference=scene.get('overlay_preference'),
                    
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
            
            # Normalize scene durations to match target duration
            ad_project.scenes = self._normalize_scene_durations(
                ad_project.scenes,
                ad_project.target_duration,
                tolerance=0.10
            )
            
            # Convert StyleSpec from plan to AdProject StyleSpec format
            style_spec_dict = {
                'lighting_direction': plan_style_spec.get('lighting_direction') or plan_style_spec.get('lighting', ''),
                'camera_style': plan_style_spec.get('camera_style', ''),
                'texture_materials': plan_style_spec.get('texture_materials') or plan_style_spec.get('texture', ''),
                'mood_atmosphere': plan_style_spec.get('mood_atmosphere') or plan_style_spec.get('mood', ''),
                'color_palette': plan_style_spec.get('color_palette', []),
                'grade_postprocessing': plan_style_spec.get('grade_postprocessing', ''),
                'music_mood': plan_style_spec.get('music_mood', 'uplifting'),
            }
            ad_project.style_spec = StyleSpec(**style_spec_dict)

            # Store chosen style and derived tone in ad_project_json
            if ad_project.video_metadata is None:
                ad_project.video_metadata = {}
            ad_project.video_metadata['selectedStyle'] = {
                'style': chosen_style,
                'source': style_source,
                'appliedAt': datetime.utcnow().isoformat()
            }
            if 'derivedTone' in plan:
                ad_project.video_metadata['derivedTone'] = plan['derivedTone']
                logger.info(f"Stored derived tone in metadata: {plan['derivedTone']}")
            
            # PHASE 8: Store perfume_name in ad_project_json for future use
            if perfume_name:
                project.ad_project_json['perfume_name'] = perfume_name
                logger.info(f"Stored perfume_name in ad_project_json: {perfume_name}")

            # Save back to database
            project.ad_project_json = ad_project.dict()
            self.db.commit()

            logger.info(f"Planned {len(ad_project.scenes)} scenes with style spec")
            return project

        except Exception as e:
            logger.error(f"Scene planning failed: {e}")
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
            
            # Get the chosen style for all scenes
            chosen_style = None
            if project.ad_project_json and "video_metadata" in project.ad_project_json:
                video_metadata = project.ad_project_json.get("video_metadata", {})
                style_info = video_metadata.get("selectedStyle", {})
                chosen_style = style_info.get("style")
                logger.info(f"Using chosen style for ALL scenes: {chosen_style} ({style_info.get('source', 'unknown')})")
            
            # Generate TikTok vertical videos (9:16 hardcoded)
            logger.info("Generating TikTok vertical videos (9:16)")

            # LOG: Show scene scripts that will be sent to video generator
            logger.info(f"📝 Scene scripts to send to video generator ({len(ad_project.scenes)} scenes):")
            for i, scene in enumerate(ad_project.scenes):
                logger.info(f"   Scene {i+1} script: {scene.background_prompt}")
            
            tasks = []
            for i, scene in enumerate(ad_project.scenes):
                try:
                    task = generator.generate_scene_background(
                        prompt=scene.background_prompt,
                        style_spec_dict=ad_project.style_spec.dict() if hasattr(ad_project.style_spec, 'dict') else (ad_project.style_spec if isinstance(ad_project.style_spec, dict) else {}),
                        duration=scene.duration,
                        extracted_style=extracted_style,
                        style_override=scene.style or chosen_style,
                    )
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"Failed to create task for scene {i} (role: {scene.role}): {e}")
                    raise

            scene_videos = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors with scene context
            for i, result in enumerate(scene_videos):
                if isinstance(result, Exception):
                    scene = ad_project.scenes[i]
                    logger.error(
                        f"Scene {i} generation failed:\n"
                        f"   Role: {scene.role}\n"
                        f"   Prompt: {scene.background_prompt[:100]}...\n"
                        f"   Duration: {scene.duration}s\n"
                        f"   Error: {result}"
                    )
                    raise RuntimeError(f"Scene {i} ({scene.role}) generation failed: {result}")

            logger.info(f"Generated {len(scene_videos)} videos")
            return scene_videos

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            raise

    async def _save_videos_locally(self, video_urls: List[str], project_id: str) -> List[str]:
        """Download videos from Replicate and save to local storage in parallel."""
        try:
            import aiohttp
            from app.utils.local_storage import LocalStorageManager
            
            async def download_and_save_video(session: aiohttp.ClientSession, index: int, url: str) -> str:
                """Download a single video and save it to local storage."""
                try:
                    # Download from Replicate
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                        if resp.status == 200:
                            video_data = await resp.read()
                        else:
                            logger.warning(f"Failed to download video {index}: HTTP {resp.status}")
                            raise Exception(f"Failed to download video {index}: HTTP {resp.status}")
                    
                    # Save to local storage in drafts folder
                    local_path = LocalStorageManager.save_draft_file(
                        UUID(project_id),
                        f"scene_{index:02d}.mp4",
                        video_data
                    )
                    logger.debug(f"Saved scene {index} locally: {local_path}")
                    return local_path
                    
                except Exception as e:
                    logger.error(f"Failed to save video {index} locally: {e}")
                    raise
            
            # Download all videos in parallel using a single session
            async with aiohttp.ClientSession() as session:
                tasks = [
                    download_and_save_video(session, i, url)
                    for i, url in enumerate(video_urls)
                ]
                local_paths = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for errors with scene context
            for i, result in enumerate(local_paths):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to download/save video {i}:\n"
                        f"   URL: {video_urls[i][:100]}...\n"
                        f"   Error: {result}"
                    )
                    raise RuntimeError(f"Video {i} download/save failed: {result}")
            
            logger.info(f"Downloaded and saved {len(local_paths)} videos in parallel")
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
        """Composite product onto each scene video using scene-specific positioning."""
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

            # Composite perfume bottles for each scene that has use_product=True
            composited = []
            for i, (video_url, scene) in enumerate(zip(scene_videos, ad_project.scenes)):
                if scene.use_product:
                    position = scene.product_position or "center"
                    # Use explicit scale if set, otherwise let compositor use role-based scaling
                    scale = scene.product_scale if scene.product_scale is not None else None
                    opacity = scene.product_opacity or 1.0
                    scene_role = scene.role  # Pass scene role for perfume-specific scaling
                    
                    logger.info(
                        f"Compositing perfume bottle on scene {i}/{len(scene_videos)}: "
                        f"role={scene_role}, position={position}, "
                        f"scale={'auto' if scale is None else f'{scale:.2f}'}, opacity={opacity:.2f}"
                    )
                    
                    composited_url = await compositor.composite_product(
                        background_video_url=video_url,
                        product_image_url=product_url,
                        project_id=str(self.project_id),
                        position=position,
                        scale=scale,  # None = use role-based scaling
                        opacity=opacity,
                        scene_index=i,
                        scene_role=scene_role,  # Pass role for perfume scaling
                    )
                    composited.append(composited_url)
                else:
                    composited.append(video_url)
                    logger.debug(f"Skipping scene {i} (use_product=False)")
                progress = progress_start + (i / len(ad_project.scenes)) * 15
                update_project_status(
                    self.db, self.project_id, "COMPOSITING", progress=int(progress)
                )

            product_scenes_count = sum(1 for s in ad_project.scenes if s.use_product)
            logger.info(
                f"Composited {len(composited)} videos "
                f"({product_scenes_count} scenes with product, {len(composited) - product_scenes_count} skipped)"
            )
            return composited

        except Exception as e:
            logger.error(f"Compositing failed: {e}")
            raise

    @timed_step("Logo Compositing")
    async def _composite_logos(
        self,
        scene_videos: List[str],
        logo_url: str,
        ad_project: AdProject,
        progress_start: int = 50,
    ) -> List[str]:
        """Composite logo onto scenes that have use_logo=True."""
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
                    
                    logger.info(f"Compositing logo on scene {i}: {position} at {scale*100:.0f}% scale")
                    
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
                    result.append(video_url)
                    logger.debug(f"Skipping logo for scene {i} (use_logo=False)")
                
                progress = progress_start + (i / len(ad_project.scenes)) * 10
                update_project_status(
                    self.db, self.project_id, "COMPOSITING_LOGO", progress=int(progress)
                )
            
            logo_scenes_count = sum(1 for s in ad_project.scenes if s.use_logo)
            logger.info(
                f"Logo composited on {logo_scenes_count} scenes, "
                f"{len(result) - logo_scenes_count} scenes without logo"
            )
            return result
            
        except Exception as e:
            logger.error(f"Logo compositing failed: {e}")
            logger.warning("Continuing pipeline without logo compositing")
            return scene_videos

    async def _add_text_overlays(
        self, video_urls: List[str], ad_project: AdProject, progress_start: int = 60
    ) -> List[str]:
        """Render text overlays on videos with luxury perfume typography constraints."""
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
            
            # Add text overlays to TikTok vertical videos (9:16) with luxury typography
            logger.info("Adding luxury perfume text overlays to TikTok vertical videos")

            # Collect all text overlays for validation
            text_overlays = []
            for i, scene in enumerate(ad_project.scenes):
                overlay = scene.overlay
                if overlay and overlay.text:
                    text_overlays.append(i)
            
            # Validate max text blocks (3-4 max for perfume ads)
            max_text_blocks = 4
            if len(text_overlays) > max_text_blocks:
                logger.warning(
                    f"Too many text overlays: {len(text_overlays)} (max {max_text_blocks}). "
                    f"Only first {max_text_blocks} scenes will have text overlays."
                )
                # Track which scenes should have overlays
                allowed_indices = set(text_overlays[:max_text_blocks])
            else:
                allowed_indices = set(text_overlays)

            # Add overlays to each scene
            overlaid = []
            text_overlay_count = 0
            for i, (video_url, scene) in enumerate(zip(video_urls, ad_project.scenes)):
                overlay = scene.overlay
                if overlay and overlay.text and i in allowed_indices:
                    # Determine text type based on scene role and position
                    text_type = self._infer_text_type(scene, overlay, i, len(ad_project.scenes))
                    
                    # Use perfume-specific luxury text overlay
                    overlaid_url = await renderer.add_perfume_text_overlay(
                        video_url=video_url,
                        text=overlay.text,
                        text_type=text_type,
                        position=overlay.position or "bottom",
                        duration=overlay.duration or min(scene.duration, 4.0),  # Max 4s per grammar
                        start_time=0.0,  # Start at beginning of scene
                        project_id=str(self.project_id),
                        scene_index=i,
                    )
                    text_overlay_count += 1
                else:
                    overlaid_url = video_url
                overlaid.append(overlaid_url)
                progress = progress_start + (i / len(ad_project.scenes)) * 10
                update_project_status(
                    self.db, self.project_id, "ADDING_OVERLAYS", progress=int(progress)
                )

            logger.info(f"Added {text_overlay_count} luxury text overlays to videos")
            return overlaid

        except Exception as e:
            logger.error(f"Text overlay rendering failed: {e}")
            raise

    def _infer_text_type(self, scene: Any, overlay: Any, scene_index: int, total_scenes: int) -> str:
        """Infer text type for perfume ad text overlay.
        
        Args:
            scene: Scene object
            overlay: Overlay object
            scene_index: Current scene index (0-based)
            total_scenes: Total number of scenes
            
        Returns:
            Text type: 'perfume_name', 'brand_name', 'tagline', or 'cta'
        """
        # Last scene is typically brand moment with perfume/brand name
        is_last_scene = scene_index == total_scenes - 1
        
        # Check scene role
        scene_role = getattr(scene, 'role', '').lower()
        
        # Infer from text content (simple heuristics)
        text_lower = overlay.text.lower()
        
        # Check if text contains brand indicators
        if any(word in text_lower for word in ['discover', 'explore', 'experience', 'unveil']):
            return 'tagline'
        
        # Check if text is short (likely perfume/brand name)
        word_count = len(overlay.text.split())
        if word_count <= 3 and is_last_scene:
            # Could be perfume name or brand name - default to perfume_name
            return 'perfume_name'
        
        # CTA scenes
        if scene_role in ['cta', 'call_to_action'] or 'shop' in text_lower or 'buy' in text_lower:
            return 'cta'
        
        # Default based on scene position
        if is_last_scene:
            return 'brand_name'  # Last scene typically shows brand
        elif scene_index == 0:
            return 'tagline'  # First scene might have tagline
        else:
            return 'tagline'  # Default to tagline

    @timed_step("Audio Generation")
    async def _generate_audio(self, project: Any, ad_project: AdProject, progress_start: int = 75) -> str:
        """Generate luxury perfume background music using MusicGen."""
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
            
            # Infer perfume gender from selected style or default to unisex
            gender = self._infer_perfume_gender(ad_project)
            logger.info(f"Using perfume gender: {gender} (inferred from style/context)")
            
            # Calculate total duration from scenes
            total_duration = sum(scene.duration for scene in ad_project.scenes) if ad_project.scenes else ad_project.target_duration
            
            # Use new perfume-specific audio generation method
            audio_url = await audio_engine.generate_perfume_background_music(
                duration=total_duration,
                project_id=str(self.project_id),
                gender=gender,
            )

            logger.info(f"Generated perfume audio: {audio_url}")
            return audio_url

        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            raise

    def _infer_perfume_gender(self, ad_project: AdProject) -> str:
        """Infer perfume gender from selected style or context.
        
        Returns:
            'masculine', 'feminine', or 'unisex'
        """
        from app.services.style_manager import StyleManager
        
        # Phase 9: Check if perfume_gender is already set in ad_project
        if ad_project.perfume_gender:
            valid_genders = ['masculine', 'feminine', 'unisex']
            if ad_project.perfume_gender in valid_genders:
                return ad_project.perfume_gender
        
        # Check if style is selected
        if ad_project.selectedStyle:
            style_id = None
            if isinstance(ad_project.selectedStyle, dict):
                style_id = ad_project.selectedStyle.get('id') or ad_project.selectedStyle.get('style')
            elif isinstance(ad_project.selectedStyle, str):
                style_id = ad_project.selectedStyle
            
            if style_id:
                style_config = StyleManager.get_style_config(style_id)
                if style_config:
                    best_for = style_config.get('best_for', [])
                    # Check best_for descriptions for gender hints
                    best_for_str = ' '.join(best_for).lower()
                    if 'masculine' in best_for_str:
                        return 'masculine'
                    elif 'feminine' in best_for_str:
                        return 'feminine'
        
        # Check creative prompt for gender hints
        if ad_project.creative_prompt:
            prompt_lower = ad_project.creative_prompt.lower()
            if any(word in prompt_lower for word in ['masculine', 'men', 'male', 'gentleman', 'man']):
                return 'masculine'
            elif any(word in prompt_lower for word in ['feminine', 'women', 'female', 'lady', 'woman']):
                return 'feminine'
        
        # Default to unisex
        return 'unisex'

    def _normalize_scene_durations(
        self,
        scenes: List[Scene],
        target_duration: int,
        tolerance: float = 0.10
    ) -> List[Scene]:
        """
        Normalize scene durations to match target duration within tolerance.
        
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
            logger.info(f"Duration within tolerance: {total_duration}s vs {target_duration}s target ({deviation*100:.1f}% deviation)")
            return scenes
        
        # Normalize durations proportionally
        scale_factor = target_duration / total_duration if total_duration > 0 else 1.0
        logger.warning(f"Duration outside tolerance: {total_duration}s vs {target_duration}s target ({deviation*100:.1f}% deviation)")
        logger.info(f"Normalizing with scale factor: {scale_factor:.3f}")
        
        normalized_scenes = []
        for scene in scenes:
            new_duration = max(3, min(15, int(scene.duration * scale_factor)))
            
            scene_dict = scene.model_dump() if hasattr(scene, 'model_dump') else scene.dict()
            scene_dict['duration'] = new_duration
            
            normalized_scenes.append(Scene(**scene_dict))
            logger.debug(f"Scene {scene.id} ({scene.role}): {scene.duration}s → {new_duration}s")
        
        new_total = sum(s.duration for s in normalized_scenes)
        logger.info(f"Normalized duration: {new_total}s (target: {target_duration}s, {abs(new_total-target_duration)}s diff)")
        
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
    ) -> str:
        """Render final TikTok vertical video (9:16 only)."""
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
            
            # Render final TikTok vertical video (9:16 hardcoded)
            final_video_path = await renderer.render_final_video(
                scene_video_urls=scene_videos,
                audio_url=audio_url,
                project_id=str(self.project_id),
            )

            update_project_status(
                self.db, self.project_id, "RENDERING", progress=100
            )

            logger.info(f"✅ Rendered final TikTok vertical video: {final_video_path}")
            return final_video_path

        except Exception as e:
            logger.error(f"Final rendering failed: {e}")
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
            
            logger.info(f"Cleaned up {deleted_count} intermediate files from S3")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup intermediate files: {e}")

    async def _save_final_video_locally(
        self, s3_video_url: str
    ) -> str:
        """Download final TikTok vertical video from S3 and save to local storage.
        
        Args:
            s3_video_url: S3 URL of the rendered video
            
        Returns:
            Local file path
        """
        try:
            import requests
            import os
            
            logger.info("Downloading TikTok vertical (9:16) video from S3...")
            
            response = requests.get(s3_video_url, timeout=300)
            response.raise_for_status()
            
            local_path = LocalStorageManager.save_final_video(
                self.project_id,
                "9:16",  # Hardcoded TikTok vertical
                None
            )
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(local_path)
            logger.info(f"Saved TikTok vertical (9:16) ({file_size / 1024 / 1024:.1f} MB) to {local_path}")
            
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to save TikTok vertical video locally: {e}")
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
        
        logger.info(f"Starting generation pipeline for project {project_id}")
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
        logger.warning(f"Generation interrupted for project {project_id}")
        raise
    except Exception as e:
        logger.error(f"RQ job failed for project {project_id}: {e}", exc_info=True)
        return {
            "status": "FAILED",
            "project_id": project_id,
            "error": str(e),
        }

