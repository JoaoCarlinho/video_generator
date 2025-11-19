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
    get_campaign_by_id,
    get_perfume_by_id,
    get_brand_by_id,
    update_campaign,
)
from app.models.schemas import AdProject, Scene, StyleSpec
from app.services.scene_planner import ScenePlanner
from app.services.product_extractor import ProductExtractor
from app.services.video_generator import VideoGenerator
from app.services.compositor import Compositor
from app.services.text_overlay import TextOverlayRenderer
from app.services.audio_engine import AudioEngine
from app.services.renderer import Renderer
# REMOVED: ReferenceImageStyleExtractor (feature removed in Phase 2 B2B SaaS)
from app.utils.s3_utils import (
    get_campaign_s3_path,
    upload_draft_video,
    upload_final_video,
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

    def __init__(self, campaign_id: UUID):
        """Initialize pipeline for a specific campaign.
        
        Args:
            campaign_id: UUID of the campaign to generate
        """
        self.campaign_id = campaign_id
        init_db()
        
        if db_connection.SessionLocal is None:
            raise RuntimeError(
                "Database not initialized. "
                "Check DATABASE_URL environment variable and database connectivity."
            )
        
        self.db = db_connection.SessionLocal()
        self.step_timings: Dict[str, float] = {}
        
        # Load campaign, perfume, and brand from database
        self.campaign = get_campaign_by_id(self.db, campaign_id)
        if not self.campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        self.perfume = get_perfume_by_id(self.db, self.campaign.perfume_id)
        if not self.perfume:
            raise ValueError(f"Perfume {self.campaign.perfume_id} not found")
        
        self.brand = get_brand_by_id(self.db, self.campaign.brand_id)
        if not self.brand:
            raise ValueError(f"Brand {self.campaign.brand_id} not found")

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
            logger.info(f"Starting generation pipeline for campaign {self.campaign_id}")

            # Campaign, perfume, and brand already loaded in __init__
            campaign = self.campaign
            perfume = self.perfume
            brand = self.brand

            # Initialize local storage (using campaign_id)
            logger.info("Initializing local storage...")
            try:
                local_paths = LocalStorageManager.initialize_project_storage(self.campaign_id)
                self.local_paths = local_paths
                storage_info = LocalStorageManager.get_project_storage_size(self.campaign_id)
                logger.info(f"Local storage initialized: {self.local_paths}")
            except Exception as e:
                logger.error(f"Failed to initialize local storage: {e}")
                raise

            # Parse Campaign JSON
            # Ensure campaign_json is a dict (handle JSONB/string cases)
            campaign_json = campaign.campaign_json
            if isinstance(campaign_json, str):
                import json
                campaign_json = json.loads(campaign_json)
            elif not isinstance(campaign_json, dict):
                raise ValueError(f"Invalid campaign_json type: {type(campaign_json)}")
            
            # Ensure video_metadata exists in the JSON
            if 'video_metadata' not in campaign_json:
                campaign_json['video_metadata'] = {}
            
            # Build AdProject from campaign data
            ad_project = self._build_ad_project_from_campaign(campaign, perfume, brand, campaign_json)
            
            # STEP 0 REMOVED: Reference image extraction (feature removed in Phase 2 B2B SaaS)

            # STEP 1: Extract Product from Perfume Images
            product_url = None
            has_product = perfume.front_image_url is not None
            
            if has_product:
                logger.info("Step 1: Extracting product from perfume image...")
                from app.config import settings
                extractor = ProductExtractor(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    s3_bucket_name=settings.s3_bucket_name,
                    aws_region=settings.aws_region,
                )
                product_url = await extractor.extract_perfume_for_campaign(campaign, perfume)
            else:
                logger.info("Step 1: Skipping product extraction (no perfume front image)")

            # STEP 2: Plan Scenes (with multi-variation support)
            planning_start = 15 if has_product else 10
            num_variations = campaign.num_variations or 1
            logger.info(f"Step 2: Planning scenes (variations: {num_variations})...")
            
            if num_variations > 1:
                # Multi-variation flow: Generate N scene plan variations
                logger.info(f"Generating {num_variations} scene plan variations...")
                scene_variations = await self._plan_scenes_variations(
                    campaign, perfume, brand, ad_project, num_variations, progress_start=planning_start
                )
                # Use first variation's ad_project for metadata (all variations share same brand/product info)
                updated_campaign_json = await self._plan_scenes(campaign, perfume, brand, ad_project, progress_start=planning_start)
                ad_project = AdProject(**updated_campaign_json)
            else:
                # Single variation flow (existing behavior)
                updated_campaign_json = await self._plan_scenes(campaign, perfume, brand, ad_project, progress_start=planning_start)
                ad_project = AdProject(**updated_campaign_json)
                scene_variations = [ad_project.scenes]

            # STEP 3-7: Process all variations IN PARALLEL
            if num_variations > 1:
                logger.info(f"Processing {num_variations} variations in parallel...")
                variation_tasks = [
                    self._process_variation(
                        scenes=scenes,
                        var_idx=var_idx,
                        num_variations=num_variations,
                        campaign=campaign,
                        perfume=perfume,
                        brand=brand,
                        ad_project=ad_project,
                        product_url=product_url,
                        has_product=has_product,
                        progress_start=planning_start + 5,
                    )
                    for var_idx, scenes in enumerate(scene_variations)
                ]
                final_videos = await asyncio.gather(*variation_tasks, return_exceptions=True)
                
                # Separate successful variations from errors
                successful_videos = []
                failed_variations = []
                for var_idx, result in enumerate(final_videos):
                    if isinstance(result, Exception):
                        failed_variations.append((var_idx, result))
                        logger.error(f"Variation {var_idx + 1} failed: {result}")
                    else:
                        successful_videos.append(result)
                        logger.info(f"Variation {var_idx + 1} succeeded: {result}")
                
                # If all variations failed, raise error
                if len(successful_videos) == 0:
                    error_msg = f"All {num_variations} variation(s) failed: {failed_variations[0][1]}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                # If some variations failed, log warning but continue with successful ones
                if failed_variations:
                    failed_indices = [idx + 1 for idx, _ in failed_variations]
                    logger.warning(
                        f"⚠️ {len(failed_variations)} variation(s) failed (indices: {failed_indices}), "
                        f"but {len(successful_videos)} variation(s) succeeded. Continuing with successful variations."
                    )
                
                # Store successful variations locally
                actual_num_variations = len(successful_videos)
                local_video_paths = self._save_variations_locally(successful_videos, actual_num_variations)
                
                # Update campaign with successful variation info
                await self._update_campaign_variations(actual_num_variations, successful_videos)
                
                total_elapsed = time.time() - pipeline_start
                logger.info(f"Pipeline complete in {total_elapsed:.1f}s ({actual_num_variations}/{num_variations} variations succeeded)")
                
                storage_size = LocalStorageManager.get_project_storage_size(self.campaign_id)
                logger.info(f"Total local storage: {format_storage_size(storage_size)}")
                
                # Build message indicating partial success if applicable
                if failed_variations:
                    message = f"{actual_num_variations} TikTok vertical video variations ready for preview ({len(failed_variations)} variation(s) failed due to API timeout)."
                else:
                    message = f"{actual_num_variations} TikTok vertical video variations ready for preview."
                
                return {
                    "status": "COMPLETED",
                    "campaign_id": str(self.campaign_id),
                    "local_video_paths": local_video_paths,
                    "num_variations": actual_num_variations,
                    "requested_variations": num_variations,
                    "failed_variations": len(failed_variations) if failed_variations else 0,
                    "storage_size": storage_size,
                    "storage_size_formatted": format_storage_size(storage_size),
                    "message": message,
                    "timing_seconds": total_elapsed,
                    "step_timings": self.step_timings,
                }
            else:
                # Single variation flow (existing code)
                # STEP 3A: Spawn Music Generation (parallel with video)
                logger.info("Step 3A: Spawning background music generation...")
                music_task = asyncio.create_task(
                    self._generate_audio(campaign, perfume, ad_project, progress_start=30)
                )

                # STEP 3B: Generate Videos (parallel with music)
                logger.info("Step 3B: Generating videos for all scenes...")
                video_start = 25 if has_product else 20
                replicate_videos = await self._generate_scene_videos(campaign, ad_project, progress_start=video_start)
                
                logger.info("Saving videos to local storage...")
                scene_videos = await self._save_videos_locally(replicate_videos, str(self.campaign_id))
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
                storage_size = LocalStorageManager.get_project_storage_size(self.campaign_id)
                logger.info(f"Total local storage: {format_storage_size(storage_size)}")

                # Update campaign with results
                campaign_json = campaign.campaign_json
                if isinstance(campaign_json, str):
                    import json
                    campaign_json = json.loads(campaign_json)
                
                campaign_json["local_video_paths"] = local_video_paths
                campaign_json["local_video_path"] = final_video_path
                
                update_campaign(
                    self.db,
                    self.campaign_id,
                    status="completed",
                    progress=100,
                    campaign_json=campaign_json
                )

                logger.info(f"Campaign ready for preview. TikTok vertical video stored locally.")

                return {
                    "status": "COMPLETED",
                    "campaign_id": str(self.campaign_id),
                    "local_video_paths": local_video_paths,
                    "local_video_path": final_video_path,
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
                LocalStorageManager.cleanup_project_storage(self.campaign_id)
                logger.info("Cleanup completed")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup storage: {cleanup_error}")

            # Mark campaign as failed
            error_msg = str(e)[:500]
            update_campaign(
                self.db,
                self.campaign_id,
                status="failed",
                error_message=error_msg,
            )

            return {
                "status": "FAILED",
                "campaign_id": str(self.campaign_id),
                "error": error_msg,
                "timing_seconds": total_elapsed,
                "step_timings": self.step_timings,
            }

    # REMOVED: _extract_perfume_product - now using ProductExtractor.extract_perfume_for_campaign directly

    @timed_step("Scene Planning")
    async def _plan_scenes(self, campaign: Any, perfume: Any, brand: Any, ad_project: AdProject, progress_start: int = 15) -> Dict[str, Any]:
        """Plan perfume scenes using LLM with shot grammar constraints."""
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
            )

            from app.config import settings
            planner = ScenePlanner(api_key=settings.openai_api_key)
            
            # Extract perfume-specific info from perfume table
            perfume_name = perfume.perfume_name
            logger.info(f"Using perfume name: {perfume_name}")
            
            # Brand colors from brand guidelines (extracted from brand table)
            brand_colors = []
            
            # Check if product/logo are available
            has_product = perfume.front_image_url is not None
            has_logo = brand.brand_logo_url is not None
            
            # Extract Brand Guidelines from brand table (required in B2B SaaS)
            extracted_guidelines = None
            guidelines_url = brand.brand_guidelines_url
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
            
            # Build creative prompt (reference image removed in Phase 2 B2B SaaS)
            creative_prompt = campaign.creative_prompt
            
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
                brand_name=brand.brand_name,
                brand_description="",  # Not stored in brand table (extracted from guidelines)
                brand_colors=brand_colors,
                brand_guidelines=extracted_guidelines.to_dict() if extracted_guidelines else None,
                target_audience="general consumers",  # Removed feature in Phase 2
                target_duration=campaign.target_duration,
                has_product=has_product,
                has_logo=has_logo,
                selected_style=campaign.selected_style,
                extracted_style=None,  # Reference image removed in Phase 2
                perfume_name=perfume_name,
                perfume_gender=perfume.perfume_gender,
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
            
            # Store results in campaign_json
            campaign_json = campaign.campaign_json
            if isinstance(campaign_json, str):
                import json
                campaign_json = json.loads(campaign_json)
            
            campaign_json['scenes'] = [scene.dict() if hasattr(scene, 'dict') else scene.model_dump() if hasattr(scene, 'model_dump') else scene for scene in ad_project.scenes]
            campaign_json['style_spec'] = style_spec_dict
            campaign_json['video_metadata'] = ad_project.video_metadata
            campaign_json['perfume_name'] = perfume_name

            # Save back to database
            update_campaign(
                self.db,
                self.campaign_id,
                campaign_json=campaign_json
            )

            logger.info(f"Planned {len(ad_project.scenes)} scenes with style spec")
            return campaign_json

        except Exception as e:
            logger.error(f"Scene planning failed: {e}")
            raise

    @timed_step("Video Generation")
    async def _generate_scene_videos(
        self, campaign: Any, ad_project: AdProject, progress_start: int = 25
    ) -> List[str]:
        """Generate background videos for all scenes in parallel."""
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
            )

            from app.config import settings
            generator = VideoGenerator(api_token=settings.replicate_api_token)

            # Get the chosen style for all scenes (from campaign)
            chosen_style = campaign.selected_style
            logger.info(f"Using chosen style for ALL scenes: {chosen_style}")
            
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
                        extracted_style=None,  # Reference image removed in Phase 2
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

    async def _save_videos_locally(self, video_urls: List[str], campaign_id: str, variation_index: Optional[int] = None) -> List[str]:
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
                    
                    # Save to local storage in drafts folder with variation index if provided
                    if variation_index is not None:
                        filename = f"scene_{variation_index}_{index:02d}.mp4"
                    else:
                        filename = f"scene_{index:02d}.mp4"
                    
                    local_path = LocalStorageManager.save_draft_file(
                        UUID(campaign_id),
                        filename,
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
        variation_index: Optional[int] = None,
    ) -> List[str]:
        """Composite product onto each scene video using scene-specific positioning."""
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
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
                        project_id=str(self.campaign_id),  # LocalStorageManager uses project_id naming
                        position=position,
                        scale=scale,  # None = use role-based scaling
                        opacity=opacity,
                        scene_index=i,
                        scene_role=scene_role,  # Pass role for perfume scaling
                        variation_index=variation_index,  # Pass variation index
                    )
                    composited.append(composited_url)
                else:
                    composited.append(video_url)
                    logger.debug(f"Skipping scene {i} (use_product=False)")
                progress = progress_start + (i / len(ad_project.scenes)) * 15
                update_campaign(
                    self.db, self.campaign_id, status="processing", progress=int(progress)
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
        variation_index: Optional[int] = None,
    ) -> List[str]:
        """Composite logo onto scenes that have use_logo=True."""
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
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
                        project_id=str(self.campaign_id),  # LocalStorageManager uses project_id naming
                        position=position,
                        scale=scale,
                        opacity=opacity,
                        scene_index=i,
                        variation_index=variation_index,  # Pass variation index
                    )
                    result.append(logo_url_result)
                else:
                    result.append(video_url)
                    logger.debug(f"Skipping logo for scene {i} (use_logo=False)")
                
                progress = progress_start + (i / len(ad_project.scenes)) * 10
                update_campaign(
                    self.db, self.campaign_id, status="processing", progress=int(progress)
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
        self, video_urls: List[str], ad_project: AdProject, progress_start: int = 60, variation_index: Optional[int] = None
    ) -> List[str]:
        """Render text overlays on videos with luxury perfume typography constraints."""
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
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
                        project_id=str(self.campaign_id),  # LocalStorageManager uses project_id naming
                        scene_index=i,
                        variation_index=variation_index,  # Pass variation index
                    )
                    text_overlay_count += 1
                else:
                    overlaid_url = video_url
                overlaid.append(overlaid_url)
                progress = progress_start + (i / len(ad_project.scenes)) * 10
                update_campaign(
                    self.db, self.campaign_id, status="processing", progress=int(progress)
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
    async def _generate_audio(self, campaign: Any, perfume: Any, ad_project: AdProject, progress_start: int = 75) -> str:
        """Generate luxury perfume background music using MusicGen."""
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
            )

            from app.config import settings
            audio_engine = AudioEngine(
                replicate_api_token=settings.replicate_api_token,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region,
            )
            
            # Use perfume gender directly from perfume table
            logger.info(f"Using perfume gender: {perfume.perfume_gender}")
            
            # Calculate total duration from scenes
            total_duration = sum(scene.duration for scene in ad_project.scenes) if ad_project.scenes else campaign.target_duration
            
            # Use new perfume-specific audio generation method
            audio_url = await audio_engine.generate_perfume_background_music(
                duration=total_duration,
                project_id=str(self.campaign_id),  # LocalStorageManager uses project_id naming
                gender=perfume.perfume_gender,  # Use perfume gender directly
            )

            logger.info(f"Generated perfume audio: {audio_url}")
            return audio_url

        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            raise

    # REMOVED: _infer_perfume_gender - perfume gender now comes directly from perfume table

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
        variation_index: int = None,
    ) -> str:
        """Render final TikTok vertical video (9:16 only)."""
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
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
                project_id=str(self.campaign_id),  # LocalStorageManager uses project_id naming
                variation_index=variation_index,
            )

            update_campaign(
                self.db, self.campaign_id, status="processing", progress=100
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
                self.campaign_id,
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

    async def _plan_scenes_variations(
        self,
        campaign: Any,
        perfume: Any,
        brand: Any,
        ad_project: AdProject,
        num_variations: int,
        progress_start: int = 15,
    ) -> List[List[Dict[str, Any]]]:
        """
        Generate N variations of scene plans with different visual approaches.
        
        Args:
            campaign: Campaign database object
            perfume: Perfume database object
            brand: Brand database object
            ad_project: AdProject schema object
            num_variations: Number of variations to generate (1-3)
            progress_start: Progress percentage start
            
        Returns:
            List of scene plan lists: [[scenes_v1], [scenes_v2], [scenes_v3]]
        """
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
            )
            
            from app.config import settings
            planner = ScenePlanner(api_key=settings.openai_api_key)
            
            # Extract perfume-specific info from perfume table
            perfume_name = perfume.perfume_name
            
            # Brand colors from brand guidelines (extracted from brand table)
            brand_colors = []
            
            # Check if product/logo are available
            has_product = perfume.front_image_url is not None
            has_logo = brand.brand_logo_url is not None
            
            # Extract brand guidelines from brand table
            extracted_guidelines = None
            guidelines_url = brand.brand_guidelines_url
            if guidelines_url:
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
                except Exception as e:
                    logger.warning(f"Guidelines extraction failed: {e}")
                    extracted_guidelines = None
            
            # Merge colors from guidelines
            if extracted_guidelines and extracted_guidelines.color_palette:
                brand_colors.extend(extracted_guidelines.color_palette)
                brand_colors = list(set(brand_colors))
            
            # Build creative prompt (reference image removed in Phase 2)
            creative_prompt = campaign.creative_prompt
            
            # Generate scene variations
            scene_variations = await planner._generate_scene_variations(
                num_variations=num_variations,
                creative_prompt=creative_prompt,
                brand_name=brand.brand_name,
                brand_description="",  # Not stored in brand table
                brand_colors=brand_colors,
                brand_guidelines=extracted_guidelines.to_dict() if extracted_guidelines else None,
                target_audience="general consumers",  # Removed feature
                target_duration=campaign.target_duration,
                has_product=has_product,
                has_logo=has_logo,
                selected_style=campaign.selected_style,
                extracted_style=None,  # Reference image removed
                perfume_name=perfume_name,
                perfume_gender=perfume.perfume_gender,
            )
            
            logger.info(f"Generated {len(scene_variations)} scene plan variations")
            return scene_variations
            
        except Exception as e:
            logger.error(f"Failed to plan scene variations: {e}")
            raise

    async def _process_variation(
        self,
        scenes: List[Any],
        var_idx: int,
        num_variations: int,
        campaign: Any,
        perfume: Any,
        brand: Any,
        ad_project: AdProject,
        product_url: Optional[str],
        has_product: bool,
        progress_start: int = 20,
    ) -> str:
        """
        Process one variation through the full pipeline.
        
        This method processes a single variation through all steps:
        - Generate videos
        - Composite products/logos
        - Add text overlays
        - Generate audio
        - Render final video
        
        Args:
            scenes: List of scene dictionaries for this variation
            var_idx: Variation index (0-based)
            num_variations: Total number of variations
            campaign: Campaign database object
            perfume: Perfume database object
            brand: Brand database object
            ad_project: AdProject schema object
            product_url: Product image URL (if available)
            has_product: Whether product is available
            progress_start: Progress percentage start
            
        Returns:
            Final video path for this variation
        """
        logger.info(f"Processing variation {var_idx + 1}/{num_variations}...")
        
        try:
            # Convert scene dictionaries to AdProjectScene objects
            from app.models.schemas import Overlay, Scene as AdProjectScene, AdProject
            
            # Get chosen style from campaign
            chosen_style = campaign.selected_style or "gold_luxe"
            
            # Convert scenes to AdProjectScene format
            ad_project_scenes = []
            for i, scene_dict in enumerate(scenes):
                ad_project_scenes.append(
                    AdProjectScene(
                        id=str(scene_dict.get('scene_id', i)),
                        role=scene_dict.get('role', 'showcase'),
                        duration=scene_dict.get('duration', 5),
                        description=scene_dict.get('background_prompt', ''),
                        background_prompt=scene_dict.get('background_prompt', ''),
                        background_type=scene_dict.get('background_type', 'cinematic'),
                        style=scene_dict.get('style', chosen_style),
                        use_product=scene_dict.get('use_product', False),
                        product_usage=scene_dict.get('product_usage', 'static_insert'),
                        product_position=scene_dict.get('product_position', 'center'),
                        product_scale=scene_dict.get('product_scale'),
                        product_opacity=scene_dict.get('product_opacity', 1.0),
                        use_logo=scene_dict.get('use_logo', False),
                        logo_position=scene_dict.get('logo_position', 'top_right'),
                        logo_scale=scene_dict.get('logo_scale', 0.1),
                        logo_opacity=scene_dict.get('logo_opacity', 0.9),
                        camera_movement=scene_dict.get('camera_movement', 'static'),
                        transition_to_next=scene_dict.get('transition_to_next', 'cut'),
                        overlay=Overlay(
                            text=scene_dict.get('overlay', {}).get('text', ''),
                            position=scene_dict.get('overlay', {}).get('position', 'bottom'),
                            duration=scene_dict.get('overlay', {}).get('duration', 3.0),
                            font_size=scene_dict.get('overlay', {}).get('font_size', 48),
                            color=scene_dict.get('overlay', {}).get('color', '#FFFFFF'),
                            animation=scene_dict.get('overlay', {}).get('animation', 'fade_in'),
                        ) if scene_dict.get('overlay') else None,
                    )
                )
            
            # Create a temporary ad_project with this variation's scenes
            variation_ad_project = AdProject(
                creative_prompt=ad_project.creative_prompt,
                brand=ad_project.brand,
                target_audience=ad_project.target_audience,
                target_duration=ad_project.target_duration,
                scenes=ad_project_scenes,
                style_spec=ad_project.style_spec,
                product_asset=ad_project.product_asset,
                video_metadata=ad_project.video_metadata,
            )
            
            # STEP 1: Generate Videos
            video_start = progress_start + (var_idx * 5)
            replicate_videos = await self._generate_scene_videos(
                campaign, variation_ad_project, progress_start=video_start
            )
            
            # Save videos locally with variation index
            scene_videos = await self._save_videos_locally(replicate_videos, str(self.campaign_id), variation_index=var_idx)
            
            # STEP 2: Composite Product (if available)
            if product_url:
                composited_videos = await self._composite_products(
                    scene_videos, product_url, variation_ad_project, progress_start=video_start + 10, variation_index=var_idx
                )
            else:
                composited_videos = scene_videos
            
            # STEP 3: Composite Logo (if available)
            logo_url = variation_ad_project.brand.get('logo_url') if isinstance(variation_ad_project.brand, dict) else None
            if logo_url:
                logo_composited_videos = await self._composite_logos(
                    composited_videos,
                    logo_url,
                    variation_ad_project,
                    progress_start=video_start + 15,
                    variation_index=var_idx
                )
            else:
                logo_composited_videos = composited_videos
            
            # STEP 4: Add Text Overlays
            text_rendered_videos = await self._add_text_overlays(
                logo_composited_videos, variation_ad_project, progress_start=video_start + 20, variation_index=var_idx
            )
            
            # STEP 5: Generate Audio (shared across variations, but we need it per variation)
            audio_url = await self._generate_audio(campaign, perfume, variation_ad_project, progress_start=video_start + 25)
            
            # STEP 6: Render Final Video
            final_video_path = await self._render_final(
                text_rendered_videos, audio_url, variation_ad_project, progress_start=video_start + 30, variation_index=var_idx
            )
            
            logger.info(f"Variation {var_idx + 1} complete: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logger.error(f"Failed to process variation {var_idx + 1}: {e}")
            raise

    def _save_variations_locally(self, final_videos: List[str], num_variations: int) -> Dict[str, Any]:
        """
        Save all variation videos locally and return paths structure.
        
        Args:
            final_videos: List of final video paths (one per variation)
            num_variations: Number of variations
            
        Returns:
            Dictionary with video paths structure:
            - If num_variations == 1: {"9:16": "path/to/video.mp4"}
            - If num_variations > 1: {"9:16": ["path/to/v1.mp4", "path/to/v2.mp4", ...]}
        """
        if num_variations == 1:
            return {"9:16": final_videos[0] if final_videos else ""}
        else:
            return {"9:16": final_videos}

    def _build_ad_project_from_campaign(
        self,
        campaign: Any,
        perfume: Any,
        brand: Any,
        campaign_json: Dict[str, Any]
    ) -> AdProject:
        """
        Build AdProject schema from campaign, perfume, and brand data.
        
        Args:
            campaign: Campaign database object
            perfume: Perfume database object
            brand: Brand database object
            campaign_json: Campaign JSON data
            
        Returns:
            AdProject: Built AdProject schema object
        """
        # Build brand dict from brand table
        brand_dict = {
            "name": brand.brand_name,
            "logo_url": brand.brand_logo_url,
            "guidelines_url": brand.brand_guidelines_url,
            "description": ""  # Not stored in brand table (extracted from guidelines)
        }
        
        # Build product asset from perfume images (use front image as primary)
        product_asset = {
            "original_url": perfume.front_image_url,
            "extracted_url": None,  # Will be set after extraction
            "angles": {
                "front": perfume.front_image_url,
                "back": perfume.back_image_url,
                "top": perfume.top_image_url,
                "left": perfume.left_image_url,
                "right": perfume.right_image_url,
            }
        }
        
        # Build AdProject from campaign data
        ad_project_dict = {
            "creative_prompt": campaign.creative_prompt,
            "brand": brand_dict,
            "target_audience": "general consumers",  # Not stored in campaign (removed feature)
            "target_duration": campaign.target_duration,
            "perfume_name": perfume.perfume_name,
            "perfume_gender": perfume.perfume_gender,
            "product_asset": product_asset,
            "scenes": campaign_json.get("scenes", []),
            "style_spec": campaign_json.get("style_spec", {}),
            "video_metadata": campaign_json.get("video_metadata", {}),
            "selectedStyle": {
                "id": campaign.selected_style,
                "source": "user_selected"
            }
        }
        
        return AdProject(**ad_project_dict)

    async def _update_campaign_variations(self, num_variations: int, final_videos: List[str]) -> None:
        """
        Update campaign database with variation information.
        
        Args:
            num_variations: Number of variations generated
            final_videos: List of final video paths
        """
        try:
            campaign = get_campaign_by_id(self.db, self.campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {self.campaign_id} not found")
            
            # Update local_video_paths
            local_video_paths = self._save_variations_locally(final_videos, num_variations)
            
            # Update campaign_json
            campaign_json = campaign.campaign_json
            if isinstance(campaign_json, str):
                import json
                campaign_json = json.loads(campaign_json)
            
            campaign_json["local_video_paths"] = local_video_paths
            if num_variations == 1:
                campaign_json["local_video_path"] = final_videos[0] if final_videos else None
            else:
                campaign_json["local_video_path"] = final_videos[0] if final_videos else None
            
            update_campaign(
                self.db,
                self.campaign_id,
                status="completed",
                progress=100,
                campaign_json=campaign_json,
                selected_variation_index=None  # User hasn't selected yet
            )
            
            logger.info(f"Updated campaign with {num_variations} variations")
            
        except Exception as e:
            logger.error(f"Failed to update campaign variations: {e}")
            raise


def generate_video(campaign_id: str) -> Dict[str, Any]:
    """
    RQ job function for video generation.
    
    This is the entry point called by RQ worker.
    Runs in a forked child process on macOS.
    
    Args:
        campaign_id: String UUID of campaign to generate
        
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
        
        logger.info(f"Starting generation pipeline for campaign {campaign_id}")
        campaign_uuid = UUID(campaign_id)
        pipeline = GenerationPipeline(campaign_uuid)
        
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
        logger.warning(f"Generation interrupted for campaign {campaign_id}")
        raise
    except Exception as e:
        logger.error(f"RQ job failed for campaign {campaign_id}: {e}", exc_info=True)
        return {
            "status": "FAILED",
            "campaign_id": campaign_id,
            "error": str(e),
        }

