"""RQ Background job for end-to-end  product video generation pipeline.

VEO S3 MIGRATION: Simplified 5-step pipeline (November 2025)
This module contains the main generation pipeline that orchestrates all services:
1. Product Extraction (remove background)
2. Scene Planning (LLM-based with product shot grammar constraints)
3. Video Generation (parallel for all scenes, TikTok vertical 9:16 only)
4. Compositing (product overlay)
5. Text Overlay Rendering (luxury typography)
6. Audio Generation (luxury ambient music)
7. Final Rendering

REMOVED STEPS (Veo S3 handles natively):
- ❌ Compositing (product overlay) - Veo integrates product naturally
- ❌ Text Overlay Rendering - Veo embeds text in scene

PERFUME-SPECIFIC FEATURES:
- User-first creative approach (user vision = primary, grammar = secondary)
- Perfume shot grammar as visual language library (not strict rules)
- Perfume name extraction and storage
- TikTok vertical optimization (9:16 hardcoded)

S3-FIRST ARCHITECTURE:
- Inputs (guidelines, logo, products) fetched from S3
- Intermediate files uploaded to S3 draft folders
- Final videos uploaded to S3 final folders
- Frontend streams directly from S3 or via API proxy
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
    get_product_by_id,
    get_brand_by_id,
    update_campaign,
)
from app.models.schemas import AdProject, Scene, StyleSpec
from app.services.scene_planner import ScenePlanner
from app.services.product_extractor import ProductExtractor
from app.services.video_generator import VideoGenerator
# REMOVED: Compositor - Veo S3 integrates product naturally
# REMOVED: TextOverlayRenderer - Veo S3 generates text in scene
from app.services.audio_engine import AudioEngine
from app.services.renderer import Renderer
from app.services.reference_image_extractor import ReferenceImageStyleExtractor
from app.utils.s3_utils import (
    get_campaign_s3_path,
    upload_draft_video,
    upload_final_video,
    upload_draft_music,
)
from app.utils.local_storage import LocalStorageManager, format_storage_size
from decimal import Decimal

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


# ============================================================================
# Provider Metadata Tracking (Story 4.4)
# ============================================================================

def build_provider_metadata(
    primary_provider: str,
    actual_provider: str,
    endpoint: str,
    failover_used: bool = False,
    failover_reason: Optional[str] = None,
    generation_duration_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """Build provider metadata dictionary for storage in database.

    This metadata helps debug issues, track failover events, and analyze costs.

    Args:
        primary_provider: User's selected provider ("replicate" or "ecs")
        actual_provider: Provider that successfully generated the video
        endpoint: Actual endpoint URL used for generation
        failover_used: Whether failover to backup provider occurred
        failover_reason: Error message that triggered failover (optional)
        generation_duration_ms: Total generation time in milliseconds (optional)

    Returns:
        Dictionary with provider metadata in standard format
    """
    metadata = {
        "primary_provider": primary_provider,
        "actual_provider": actual_provider,
        "failover_used": failover_used,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoint": endpoint,
    }

    if failover_reason:
        metadata["failover_reason"] = failover_reason

    if generation_duration_ms is not None:
        metadata["generation_duration_ms"] = generation_duration_ms

    return metadata


class GenerationPipeline:
    """Main pipeline orchestrator for video generation."""

    def __init__(self, campaign_id: UUID, video_provider: str = "replicate"):
        """Initialize pipeline for a specific campaign.
        
        Args:
            campaign_id: UUID of the campaign to generate
        """
        self.campaign_id = campaign_id
        self.video_provider = video_provider
        init_db()

        if db_connection.SessionLocal is None:
            raise RuntimeError(
                "Database not initialized. "
                "Check DATABASE_URL environment variable and database connectivity."
            )

        self.db = db_connection.SessionLocal()
        self.step_timings: Dict[str, float] = {}
        
        # Load campaign, product, and brand from database
        self.campaign = get_campaign_by_id(self.db, campaign_id)
        if not self.campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        logger.info(f"🔍 Loaded campaign {self.campaign.campaign_id}: product_id={self.campaign.product_id}, brand_id={self.campaign.brand_id}")
        
        self.product = get_product_by_id(self.db, self.campaign.product_id)
        if not self.product:
            raise ValueError(f"Perfume {self.campaign.product_id} not found")
        
        logger.info(f"🔍 Loaded product {self.product.product_id}: brand_id={self.product.brand_id}")
        
        # Verify product belongs to campaign's brand
        if self.product.brand_id != self.campaign.brand_id:
            logger.error(f"❌ CRITICAL: Perfume {self.product.product_id} brand_id {self.product.brand_id} doesn't match campaign brand_id {self.campaign.brand_id}")
            raise ValueError(f"Perfume {self.product.product_id} does not belong to campaign's brand {self.campaign.brand_id}")
        
        self.brand = get_brand_by_id(self.db, self.campaign.brand_id)
        if not self.brand:
            raise ValueError(f"Brand {self.campaign.brand_id} not found")
        
        logger.info(f"🔍 Loaded brand {self.brand.brand_id}: user_id={self.brand.user_id}")
        
        # Verify brand matches product's brand
        if self.brand.brand_id != self.product.brand_id:
            logger.error(f"❌ CRITICAL: Brand {self.brand.brand_id} doesn't match product brand_id {self.product.brand_id}")
            raise ValueError(f"Brand {self.brand.brand_id} does not match product's brand {self.product.brand_id}")
        
        logger.info(f"✅ Verified IDs: brand={self.brand.brand_id}, product={self.product.product_id}, campaign={self.campaign.campaign_id}")

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

            # Campaign, product, and brand already loaded in __init__
            campaign = self.campaign
            product = self.product
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
            ad_project = self._build_ad_project_from_campaign(campaign, product, brand, campaign_json)
            
            # STEP 0 REMOVED: Reference image extraction (feature removed in Phase 2 B2B SaaS)

            # STEP 1: Extract Product from Perfume Images
            product_url = None
            has_product = product.front_image_url is not None
            
            if has_product:
                logger.info("Step 1: Extracting product from product image...")
                from app.config import settings
                extractor = ProductExtractor(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    s3_bucket_name=settings.s3_bucket_name,
                    aws_region=settings.aws_region,
                )
                product_url = await extractor.extract_product_for_campaign(campaign, product)
            else:
                logger.info("Step 1: Skipping product extraction (no product front image)")

            # STEP 2: Plan Scenes (with multi-variation support)
            planning_start = 15 if has_product else 10
            num_variations = campaign.num_variations or 1
            logger.info(f"Step 2: Planning scenes (variations: {num_variations})...")
            
            if num_variations > 1:
                # Multi-variation flow: Generate N scene plan variations
                logger.info(f"Generating {num_variations} scene plan variations...")
                scene_variations = await self._plan_scenes_variations(
                    campaign, product, brand, ad_project, num_variations, progress_start=planning_start
                )
                # Use first variation's ad_project for metadata (all variations share same brand/product info)
                # _plan_scenes modifies ad_project in place, so we don't need to recreate it
                await self._plan_scenes(campaign, product, brand, ad_project, progress_start=planning_start)
            else:
                # Single variation flow (existing behavior)
                # _plan_scenes modifies ad_project in place, so we don't need to recreate it
                await self._plan_scenes(campaign, product, brand, ad_project, progress_start=planning_start)
                scene_variations = [ad_project.scenes]

            # STEP 3-7: Process all variations IN PARALLEL
            logger.info(f"Processing {num_variations} variations in parallel...")
            variation_tasks = [
                self._process_variation(
                    scenes=scenes,
                    var_idx=var_idx,
                    num_variations=num_variations,
                    campaign=campaign,
                    product=product,
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
            
            # Update campaign with successful variation info (S3 URLs)
            actual_num_variations = len(successful_videos)
            await self._update_campaign_variations(actual_num_variations, successful_videos)
            
            total_elapsed = time.time() - pipeline_start
            logger.info(f"Pipeline complete in {total_elapsed:.1f}s ({actual_num_variations}/{num_variations} variations succeeded)")
            
            # Build message indicating partial success if applicable
            if failed_variations:
                message = f"{actual_num_variations} TikTok vertical video variations ready for preview ({len(failed_variations)} variation(s) failed due to API timeout)."
            else:
                message = f"{actual_num_variations} TikTok vertical video variations ready for preview."
            
            return {
                "status": "COMPLETED",
                "local_video_paths": local_video_paths,
                "storage_size": storage_size,
                "storage_size_formatted": format_storage_size(storage_size),
                "message": "Videos ready for preview. Videos stored in local storage.",
                "total_cost": float(self.total_cost),
                "cost_breakdown": {k: float(v) for k, v in self.step_costs.items()},
                "campaign_id": str(self.campaign_id),
                "video_urls": successful_videos,  # S3 URLs
                "num_variations": actual_num_variations,
                "requested_variations": num_variations,
                "failed_variations": len(failed_variations) if failed_variations else 0,
                "message": message,
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

    # REMOVED: _extractproduct - now using ProductExtractor.extract_product_for_campaign directly

    async def _upload_scene_videos_to_s3(
        self, 
        video_urls: List[str], 
        variation_index: int
    ) -> List[str]:
        """
        Download videos from Replicate/URL and upload to S3 as draft.
        
        Args:
            video_urls: List of Replicate URLs or local paths
            variation_index: Variation index (0, 1, 2)
            
        Returns:
            List of S3 URLs for the uploaded videos
        """
        try:
            import aiohttp
            import os
            import tempfile
            from pathlib import Path
            
            s3_urls = []
            
            # Create a temp session for downloads
            from app.config import settings
            from app.utils.s3_utils import parse_s3_url, get_s3_client
            
            # Initialize S3 client for authenticated downloads
            s3_client = get_s3_client()
            
            async with aiohttp.ClientSession() as session:
                for i, url in enumerate(video_urls):
                    # Check if it's already an S3 URL - if so, skip re-uploading
                    is_s3_url = (
                        url.startswith("https://") and 
                        ("s3." in url or "s3.amazonaws.com" in url or settings.s3_bucket_name in url)
                    )
                    if is_s3_url:
                        logger.info(f"Scene {i+1} video already in S3, skipping re-upload: {url[:80]}...")
                        s3_urls.append(url)
                        continue
                    
                    # Create temp file
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                        temp_path = tmp.name
                    
                    try:
                        # Download content using appropriate method
                        if url.startswith("http"):
                            # Check if it's an S3 URL that needs authentication
                            if ".s3." in url or "s3.amazonaws.com" in url:
                                # Use boto3 for authenticated S3 download
                                try:
                                    bucket_name, s3_key = parse_s3_url(url)
                                    s3_client.download_file(bucket_name, s3_key, temp_path)
                                    logger.info(f"✅ Downloaded from S3 using boto3: {s3_key}")
                                except Exception as e:
                                    logger.error(f"Failed to download from S3 with boto3: {e}")
                                    raise ValueError(f"Failed to download video {i+1} from S3: {str(e)}")
                            else:
                                # Use HTTP for non-S3 URLs (e.g., Replicate URLs)
                                async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                                    if resp.status != 200:
                                        raise ValueError(f"Failed to download video {i+1}: HTTP {resp.status}")
                                    content = await resp.read()
                                    with open(temp_path, "wb") as f:
                                        f.write(content)
                        else:
                            # It's a local path
                            import shutil
                            shutil.copy2(url, temp_path)
                            
                        # Upload to S3
                        result = await upload_draft_video(
                            brand_id=str(self.brand.brand_id),
                            product_id=str(self.product.product_id),
                            campaign_id=str(self.campaign.campaign_id),
                            variation_index=variation_index,
                            scene_index=i+1,  # 1-based index
                            file_path=temp_path
                        )
                        s3_urls.append(result["url"])
                        
                    finally:
                        # Cleanup temp file
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
            
            logger.info(f"Uploaded {len(s3_urls)} scenes to S3 for variation {variation_index}")
            return s3_urls
            
            product_url = await extractor.extract_product(
                image_url=ad_project.product_asset.original_url,
                project_id=str(self.project_id),
            )

            logger.info(f"✅ Product extracted: {product_url}")
            return product_url

        except Exception as e:
            logger.error(f"Failed to upload scenes to S3: {e}")
            raise

    @timed_step("Scene Planning")
    async def _plan_scenes(self, campaign: Any, product: Any, brand: Any, ad_project: AdProject, progress_start: int = 15) -> Dict[str, Any]:
        """Plan product scenes using LLM with shot grammar constraints."""
        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
            )

            from app.config import settings
            planner = ScenePlanner(api_key=settings.openai_api_key)
            
            # Extract product-specific info from product table
            product_name = product.product_name
            logger.info(f"Using product name: {product_name}")
            
            # Brand colors from brand guidelines (extracted from brand table)
            brand_colors = []
            
            # Check if product/logo are available
            has_product = product.front_image_url is not None
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
            
            # Convert brand guidelines dict to string format for scene planner
            brand_guidelines_str = None
            if extracted_guidelines:
                import json
                guidelines_dict = extracted_guidelines.to_dict()
                # Format as readable string instead of raw JSON
                guidelines_parts = []
                if guidelines_dict.get('tone_of_voice'):
                    guidelines_parts.append(f"Tone: {guidelines_dict['tone_of_voice']}")
                if guidelines_dict.get('color_palette'):
                    guidelines_parts.append(f"Colors: {', '.join(guidelines_dict['color_palette'])}")
                if guidelines_dict.get('dos_and_donts', {}).get('dos'):
                    guidelines_parts.append(f"DO: {'; '.join(guidelines_dict['dos_and_donts']['dos'][:3])}")
                if guidelines_dict.get('dos_and_donts', {}).get('donts'):
                    guidelines_parts.append(f"DON'T: {'; '.join(guidelines_dict['dos_and_donts']['donts'][:3])}")
                brand_guidelines_str = " | ".join(guidelines_parts) if guidelines_parts else None
            
            plan = await planner.plan_scenes(
                creative_prompt=creative_prompt,
                brand_name=brand.brand_name,
                brand_description="",  # Not stored in brand table (extracted from guidelines)
                brand_colors=brand_colors,
                brand_guidelines=brand_guidelines_str,
                target_audience="general consumers",  # Removed feature in Phase 2
                target_duration=campaign.target_duration,
                has_product=has_product,
                has_logo=has_logo,
                selected_style=campaign.selected_style,
                extracted_style=None,  # Reference image removed in Phase 2
                product_name=product_name,
                product_gender=product.product_gender,
            )

            chosen_style = plan.get('chosenStyle')
            style_source = plan.get('styleSource')
            plan_scenes_list = plan.get('scenes', [])
            plan_style_spec = plan.get('style_spec', {})
            
            logger.info(f"ScenePlanner chose style: {chosen_style} ({style_source})")
            
            # PHASE 8: Validate grammar compliance
            from app.services.product_grammar_loader import PerfumeGrammarLoader
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
            campaign_json['product_name'] = product_name

            # PHASE 7: Store chosen style in ad_project_json
            if not ad_project.video_metadata:
                ad_project.video_metadata = {}
            ad_project.video_metadata['selectedStyle'] = {
                'style': chosen_style,
                'source': style_source,
                'appliedAt': datetime.utcnow().isoformat()
            }

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
        """Generate background videos for all scenes in parallel.

        STORY 3 (AC#5): For scenes with custom backgrounds, use uploaded image instead of AI generation.
        STORY 4.4: Track provider metadata during generation.
        """
        # Track generation start time for metadata
        generation_start = datetime.utcnow()

        try:
            update_campaign(
                self.db, self.campaign_id, status="processing", progress=progress_start
            )

            from app.config import settings

            # STORY 4.4: Get provider from project (defaults to "replicate")
            # Validate provider parameter
            if self.video_provider not in ["replicate", "ecs"]:
                logger.warning(f"Invalid provider '{self.video_provider}', defaulting to 'replicate'")
                self.video_provider = "replicate"

            # Check if ECS selected but not configured
            if self.video_provider == "ecs" and not settings.ecs_provider_enabled:
                logger.warning("ECS provider requested but not configured, falling back to Replicate")
                self.video_provider = "replicate"

            logger.info(f"🎬 Project {self.project_id}: Using video provider: {self.video_provider}")
            video_provider = self.video_provider

            # Initialize VideoGenerator with provider
            generator = VideoGenerator(
                provider=video_provider,
                api_token=settings.replicate_api_token,
                ecs_endpoint_url=str(settings.ecs_endpoint_url) if settings.ecs_provider_enabled else None
            )

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

    # REMOVED: _composite_products() - Veo S3 integrates product naturally (no manual overlay needed)
    # REMOVED: _composite_logos() - Veo S3 integrates logo naturally (no manual overlay needed)
    # REMOVED: _add_text_overlays() - Veo S3 generates text embedded in scene (not overlaid)
    # REMOVED: _infer_text_type() - No longer needed without manual text rendering

    @timed_step("Audio Generation")
    async def _generate_audio(self, campaign: Any, product: Any, ad_project: AdProject, progress_start: int = 75) -> str:
        """Generate luxury product background music using MusicGen."""
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
            
            # Get mood from style_spec (set by LLM during planning)
            music_mood = ad_project.style_spec.mood if ad_project.style_spec else "uplifting"
            if hasattr(ad_project.style_spec, 'music_mood'):
                music_mood = ad_project.style_spec.music_mood
            # Use product gender directly from product table
            logger.info(f"Using product gender: {product.product_gender}")
            
            # Calculate total duration from scenes
            total_duration = sum(scene.duration for scene in ad_project.scenes) if ad_project.scenes else campaign.target_duration
            
            audio_url = await audio_engine.generate_background_music(
                mood=music_mood,
                duration=total_duration,
                project_id=str(self.project_id),
                gender=product.product_gender,  # Use product gender directly
            )

            logger.info(f"Generated product audio: {audio_url}")
            return audio_url

        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            raise

    # REMOVED: _infer_product_gender - product gender now comes directly from product table

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
                campaign_id=str(self.campaign_id),
                output_aspect_ratios=output_aspect_ratios,
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
        product: Any,
        brand: Any,
        ad_project: AdProject,
        num_variations: int,
        progress_start: int = 15,
    ) -> List[List[Dict[str, Any]]]:
        """
        Generate N variations of scene plans with different visual approaches.
        
        Args:
            campaign: Campaign database object
            product: Perfume database object
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
            
            # Extract product-specific info from product table
            product_name = product.product_name
            
            # Brand colors from brand guidelines (extracted from brand table)
            brand_colors = []
            
            # Check if product/logo are available
            has_product = product.front_image_url is not None
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
            
            # Convert brand guidelines dict to string format for scene planner
            brand_guidelines_str = None
            if extracted_guidelines:
                import json
                guidelines_dict = extracted_guidelines.to_dict()
                # Format as readable string instead of raw JSON
                guidelines_parts = []
                if guidelines_dict.get('tone_of_voice'):
                    guidelines_parts.append(f"Tone: {guidelines_dict['tone_of_voice']}")
                if guidelines_dict.get('color_palette'):
                    guidelines_parts.append(f"Colors: {', '.join(guidelines_dict['color_palette'])}")
                if guidelines_dict.get('dos_and_donts', {}).get('dos'):
                    guidelines_parts.append(f"DO: {'; '.join(guidelines_dict['dos_and_donts']['dos'][:3])}")
                if guidelines_dict.get('dos_and_donts', {}).get('donts'):
                    guidelines_parts.append(f"DON'T: {'; '.join(guidelines_dict['dos_and_donts']['donts'][:3])}")
                brand_guidelines_str = " | ".join(guidelines_parts) if guidelines_parts else None
            
            # Generate scene variations
            scene_variations = await planner._generate_scene_variations(
                num_variations=num_variations,
                creative_prompt=creative_prompt,
                brand_name=brand.brand_name,
                brand_description="",  # Not stored in brand table
                brand_colors=brand_colors,
                brand_guidelines=brand_guidelines_str,
                target_audience="general consumers",  # Removed feature
                target_duration=campaign.target_duration,
                has_product=has_product,
                has_logo=has_logo,
                selected_style=campaign.selected_style,
                extracted_style=None,  # Reference image removed
                product_name=product_name,
                product_gender=product.product_gender,
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
        product: Any,
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
            product: Perfume database object
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
            # Handle both dictionaries and Scene objects
            ad_project_scenes = []
            for i, scene_item in enumerate(scenes):
                # Check if scene_item is already a Scene object or a dictionary
                if isinstance(scene_item, AdProjectScene):
                    # Already a Scene object, use it directly
                    ad_project_scenes.append(scene_item)
                elif isinstance(scene_item, dict):
                    # Dictionary, convert to Scene object
                    scene_dict = scene_item
                    overlay_dict = scene_dict.get('overlay')
                    ad_project_scenes.append(
                        AdProjectScene(
                            id=str(scene_dict.get('scene_id', scene_dict.get('id', i))),
                            role=scene_dict.get('role', 'showcase'),
                            duration=scene_dict.get('duration', 5),
                            description=scene_dict.get('background_prompt', scene_dict.get('description', '')),
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
                                text=overlay_dict.get('text', '') if isinstance(overlay_dict, dict) else getattr(overlay_dict, 'text', ''),
                                position=overlay_dict.get('position', 'bottom') if isinstance(overlay_dict, dict) else getattr(overlay_dict, 'position', 'bottom'),
                                duration=overlay_dict.get('duration', 3.0) if isinstance(overlay_dict, dict) else getattr(overlay_dict, 'duration', 3.0),
                                font_size=overlay_dict.get('font_size', 48) if isinstance(overlay_dict, dict) else getattr(overlay_dict, 'font_size', 48),
                                color=overlay_dict.get('color', '#FFFFFF') if isinstance(overlay_dict, dict) else getattr(overlay_dict, 'color', '#FFFFFF'),
                                animation=overlay_dict.get('animation', 'fade_in') if isinstance(overlay_dict, dict) else getattr(overlay_dict, 'animation', 'fade_in'),
                            ) if overlay_dict else None,
                        )
                    )
                else:
                    # Unknown type, try to convert using getattr
                    logger.warning(f"Unknown scene type: {type(scene_item)}, attempting attribute access")
                    ad_project_scenes.append(
                        AdProjectScene(
                            id=str(getattr(scene_item, 'scene_id', getattr(scene_item, 'id', i))),
                            role=getattr(scene_item, 'role', 'showcase'),
                            duration=getattr(scene_item, 'duration', 5),
                            description=getattr(scene_item, 'background_prompt', getattr(scene_item, 'description', '')),
                            background_prompt=getattr(scene_item, 'background_prompt', ''),
                            background_type=getattr(scene_item, 'background_type', 'cinematic'),
                            style=getattr(scene_item, 'style', chosen_style),
                            use_product=getattr(scene_item, 'use_product', False),
                            product_usage=getattr(scene_item, 'product_usage', 'static_insert'),
                            product_position=getattr(scene_item, 'product_position', 'center'),
                            product_scale=getattr(scene_item, 'product_scale', None),
                            product_opacity=getattr(scene_item, 'product_opacity', 1.0),
                            use_logo=getattr(scene_item, 'use_logo', False),
                            logo_position=getattr(scene_item, 'logo_position', 'top_right'),
                            logo_scale=getattr(scene_item, 'logo_scale', 0.1),
                            logo_opacity=getattr(scene_item, 'logo_opacity', 0.9),
                            camera_movement=getattr(scene_item, 'camera_movement', 'static'),
                            transition_to_next=getattr(scene_item, 'transition_to_next', 'cut'),
                            overlay=(
                                Overlay(
                                    text=getattr(overlay_obj, 'text', ''),
                                    position=getattr(overlay_obj, 'position', 'bottom'),
                                    duration=getattr(overlay_obj, 'duration', 3.0),
                                    font_size=getattr(overlay_obj, 'font_size', 48),
                                    color=getattr(overlay_obj, 'color', '#FFFFFF'),
                                    animation=getattr(overlay_obj, 'animation', 'fade_in'),
                                ) if (overlay_obj := getattr(scene_item, 'overlay', None)) else None
                            )
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
            
            # VEO S3 MIGRATION: Simplified 5-step pipeline (removed compositor + text overlay)
            # Product and text now integrated by Veo S3 during video generation
            
            # STEP 1: Generate Videos (Veo S3 integrates product + text natively)
            video_start = progress_start + (var_idx * 5)
            replicate_videos = await self._generate_scene_videos(
                campaign, variation_ad_project, progress_start=video_start
            )
            
            # Upload scene videos to S3 (Draft)
            scene_videos = await self._upload_scene_videos_to_s3(replicate_videos, variation_index=var_idx)
            
            # REMOVED STEP 2: Composite Product - Veo S3 integrates naturally
            # REMOVED STEP 3: Composite Logo - Veo S3 integrates naturally
            # REMOVED STEP 4: Add Text Overlays - Veo S3 embeds text in scene
            
            # STEP 2: Generate Audio (formerly step 5)
            # Audio engine saves locally, returns local path
            audio_local_path = await self._generate_audio(campaign, perfume, variation_ad_project, progress_start=video_start + 45)
            
            # Upload audio to S3 (Draft)
            audio_url_result = await upload_draft_music(
                brand_id=str(self.brand.brand_id),
                product_id=str(self.product.product_id),
                campaign_id=str(self.campaign.campaign_id),
                variation_index=var_idx,
                file_path=audio_local_path
            )
            audio_url = audio_url_result["url"]
            
            # STEP 3: Render Final Video (formerly step 6)
            final_local_path = await self._render_final(
                scene_videos, audio_url, variation_ad_project, progress_start=video_start + 60, variation_index=var_idx
            )
            
            # Upload final video to S3 (Final)
            final_result = await upload_final_video(
                brand_id=str(self.brand.brand_id),
                product_id=str(self.product.product_id),
                campaign_id=str(self.campaign.campaign_id),
                variation_index=var_idx,
                file_path=final_local_path
            )
            final_video_url = final_result["url"]
            
            logger.info(f"Variation {var_idx + 1} complete: {final_video_url}")
            return final_video_url
            
        except Exception as e:
            logger.error(f"Failed to process variation {var_idx + 1}: {e}")
            raise

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

    def _build_ad__from_campaign(
        self,
        campaign: Any,
        product: Any,
        brand: Any,
        campaign_json: Dict[str, Any],
        video_provider: str = "replicate"
    ) -> AdProject:
        """
        Build AdProject schema from campaign, product, and brand data.
        
        Args:
            campaign: Campaign database object
            product: Perfume database object
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
        
        # Build product asset from product images (use front image as primary)
        product_asset = {
            "original_url": product.front_image_url,
            "extracted_url": None,  # Will be set after extraction
            "angles": {
                "front": product.front_image_url,
                "back": product.back_image_url,
                "top": product.top_image_url,
                "left": product.left_image_url,
                "right": product.right_image_url,
            }
        }
        
        # Build AdProject from campaign data
        # Note: style_spec will be populated during scene planning, but we need to provide defaults here
        # to satisfy AdProject validation. These defaults will be replaced during planning.
        default_style_spec = campaign_json.get("style_spec", {})
        if not default_style_spec or not isinstance(default_style_spec, dict):
            # Provide minimal defaults - these will be replaced during scene planning
            default_style_spec = {
                "lighting_direction": "",
                "camera_style": "",
                "texture_materials": "",
                "mood_atmosphere": "",
                "color_palette": [],
                "grade_postprocessing": "",
                "music_mood": "uplifting",
            }
        
        ad_project_dict = {
            "creative_prompt": campaign.creative_prompt,
            "brand": brand_dict,
            "target_audience": "general consumers",  # Not stored in campaign (removed feature)
            "target_duration": campaign.target_duration,
            "product_name": product.product_name,
            "product_gender": product.product_gender,
            "product_asset": product_asset,
            "scenes": campaign_json.get("scenes", []),
            "style_spec": default_style_spec,
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
            final_videos: List of final video S3 URLs
        """
        try:
            campaign = get_campaign_by_id(self.db, self.campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {self.campaign_id} not found")
            
            # Update campaign_json
            campaign_json = campaign.campaign_json
            if isinstance(campaign_json, str):
                import json
                campaign_json = json.loads(campaign_json)
            elif campaign_json is None:
                campaign_json = {}
            elif not isinstance(campaign_json, dict):
                logger.warning(f"⚠️ campaign_json is not a dict, got {type(campaign_json)}, initializing as empty dict")
                campaign_json = {}
            
            logger.info(f"🔍 Current campaign_json before update: {campaign_json}")
            logger.info(f"🔍 Final videos to store: {final_videos}")
            
            # Store S3 URLs in variationPaths with correct structure for API
            # Format: {"variation_0": {"aspectExports": {"9:16": "url"}}, ...}
            variation_paths = {}
            for i, url in enumerate(final_videos):
                variation_paths[f"variation_{i}"] = {
                    "aspectExports": {
                        "9:16": url  # Only 9:16 supported for now
                    }
                }
            
            campaign_json["variationPaths"] = variation_paths
            
            logger.info(f"🔍 Updated campaign_json with variationPaths: {campaign_json}")
            
            # Clean up legacy local path fields to ensure S3 usage
            if "local_video_paths" in campaign_json:
                del campaign_json["local_video_paths"]
            if "local_video_path" in campaign_json:
                del campaign_json["local_video_path"]
            
            update_campaign(
                self.db,
                self.campaign_id,
                status="completed",
                progress=100,
                campaign_json=campaign_json,
                selected_variation_index=None  # User hasn't selected yet
            )
            
            # Verify the update was successful
            updated_campaign = get_campaign_by_id(self.db, self.campaign_id)
            if updated_campaign:
                verify_json = updated_campaign.campaign_json
                if isinstance(verify_json, str):
                    import json
                    verify_json = json.loads(verify_json)
                logger.info(f"✅ Verified campaign_json after update: {verify_json}")
                logger.info(f"✅ variationPaths keys: {list(verify_json.get('variationPaths', {}).keys())}")
            
            logger.info(f"Updated campaign with {num_variations} variations (S3 URLs)")
            
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
        video_provider: Video generation provider ("replicate" or "ecs")
        
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

