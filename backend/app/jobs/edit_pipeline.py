"""Scene editing pipeline job."""

import asyncio
import logging
import time
import os
import tempfile
import aiohttp
import boto3
from uuid import UUID
from typing import Dict, Any
from datetime import datetime

from app.database.connection import init_db
from app.database import connection as db_connection
from app.database.crud import get_campaign_by_id, update_campaign
from app.services.edit_service import EditService
from app.services.video_generator import VideoGenerator
from app.services.renderer import Renderer
from app.utils.s3_utils import (
    upload_draft_video,
    upload_final_video,
    get_scene_s3_url,
    get_final_video_s3_url,
    parse_s3_url,
    download_from_s3
)
from app.config import settings

logger = logging.getLogger(__name__)


class SceneEditPipeline:
    """Pipeline for editing a single scene in a campaign."""
    
    def __init__(
        self,
        campaign_id: UUID,
        scene_index: int,
        edit_instruction: str
    ):
        """Initialize edit pipeline."""
        self.campaign_id = campaign_id
        self.scene_index = scene_index
        self.edit_instruction = edit_instruction
        self.db = None  # Will be initialized in run()
        
        logger.info(f"Initialized edit pipeline for campaign {campaign_id}, scene {scene_index}")
    
    async def run(self) -> Dict[str, Any]:
        """Execute scene edit pipeline."""
        start_time = time.time()
        total_cost = 0.0
        
        # Initialize DB session
        self.db = db_connection.SessionLocal()
        
        try:
            logger.info(f"Starting scene edit: Campaign {self.campaign_id}, Scene {self.scene_index}")
            
            # Load campaign
            self.campaign = get_campaign_by_id(self.db, self.campaign_id)
            if not self.campaign:
                raise ValueError(f"Campaign {self.campaign_id} not found")
            
            # Update status
            update_campaign(self.db, self.campaign_id, status="processing")
            
            campaign_json = self.campaign.campaign_json
            if isinstance(campaign_json, str):
                import json
                campaign_json = json.loads(campaign_json)
            
            # STEP 1: Get scene data
            scenes = campaign_json.get('scenes', [])
            if self.scene_index >= len(scenes):
                raise ValueError(f"Scene index {self.scene_index} out of range")
            
            scene = scenes[self.scene_index]
            original_prompt = scene.get('background_prompt', '')
            scene_role = scene.get('role', 'unknown')
            scene_duration = scene.get('duration', 4)
            
            style_spec = campaign_json.get('style_spec', {})
            product_name = campaign_json.get('product_name', 'Product')
            
            logger.info(f"Scene {self.scene_index}: role={scene_role}, duration={scene_duration}s")
            
            # STEP 2: Modify prompt via LLM
            edit_service = EditService(openai_api_key=settings.openai_api_key)
            
            result = await edit_service.modify_scene_prompt(
                original_prompt=original_prompt,
                edit_instruction=self.edit_instruction,
                style_spec=style_spec,
                scene_role=scene_role,
                product_name=product_name
            )
            
            modified_prompt = result['modified_prompt']
            changes_summary = result['changes_summary']
            total_cost += 0.01  # GPT-4o-mini cost
            
            logger.info(f"Prompt modified. Changes: {changes_summary}")
            
            # STEP 3: Regenerate scene video
            video_generator = VideoGenerator(api_token=settings.replicate_api_token)
            
            new_video_url = await video_generator.generate_scene_background(
                prompt=modified_prompt,
                style_spec_dict=style_spec,
                duration=float(scene_duration)
            )
            total_cost += 0.20  # ByteDance cost
            
            logger.info(f"New scene video generated: {new_video_url}")
            
            # STEP 4: Download and upload to S3 (replace old scene)
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                tmp_path = tmp.name
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(new_video_url) as resp:
                        if resp.status != 200:
                            raise RuntimeError(f"Failed to download video: HTTP {resp.status}")
                        content = await resp.read()
                        tmp.write(content)
            
            # Upload to S3 (replaces old scene video)
            s3_result = await upload_draft_video(
                brand_id=str(self.campaign.product.brand_id),
                product_id=str(self.campaign.product_id),
                campaign_id=str(self.campaign_id),
                variation_index=self.campaign.selected_variation_index or 0,
                scene_index=self.scene_index + 1,  # 1-based
                file_path=tmp_path
            )
            new_scene_s3_url = s3_result['url']
            
            os.unlink(tmp_path)
            logger.info(f"Scene uploaded to S3: {new_scene_s3_url}")
            
            # STEP 5: Download ALL scenes for re-rendering
            all_scene_urls = []
            for i, s in enumerate(scenes):
                if i == self.scene_index:
                    # Use new scene
                    all_scene_urls.append(new_scene_s3_url)
                else:
                    # Use existing scene from S3
                    scene_s3_url = get_scene_s3_url(
                        brand_id=str(self.campaign.product.brand_id),
                        product_id=str(self.campaign.product_id),
                        campaign_id=str(self.campaign_id),
                        variation_index=self.campaign.selected_variation_index or 0,
                        scene_index=i
                    )
                    all_scene_urls.append(scene_s3_url)
            
            # Download scenes temporarily
            scene_temps = []
            for url in all_scene_urls:
                temp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                temp_path = temp.name
                # Download from S3 using boto3
                bucket_name, s3_key = parse_s3_url(url)
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
                s3_client.download_file(bucket_name, s3_key, temp_path)
                scene_temps.append(temp_path)
            
            # STEP 6: Re-render final video
            renderer = Renderer(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region
            )
            
            # Get audio URL - try from campaign_json first, otherwise construct S3 URL
            audio_url = campaign_json.get('audio_url', '')
            if not audio_url:
                # Construct S3 URL for audio file
                from app.utils.s3_utils import get_audio_s3_url
                audio_url = get_audio_s3_url(
                    brand_id=str(self.campaign.product.brand_id),
                    product_id=str(self.campaign.product_id),
                    campaign_id=str(self.campaign_id),
                    variation_index=self.campaign.selected_variation_index or 0
                )
                logger.info(f"Constructed audio S3 URL: {audio_url}")
            
            if not audio_url:
                raise ValueError("Audio URL not found in campaign_json and could not be constructed")
            
            final_video_path = await renderer.render_final_video(
                scene_video_urls=scene_temps,
                audio_url=audio_url,
                campaign_id=str(self.campaign_id),
                variation_index=self.campaign.selected_variation_index or 0
            )
            
            # STEP 7: Upload new final video (replaces old)
            final_result = await upload_final_video(
                brand_id=str(self.campaign.product.brand_id),
                product_id=str(self.campaign.product_id),
                campaign_id=str(self.campaign_id),
                variation_index=self.campaign.selected_variation_index or 0,
                file_path=final_video_path
            )
            
            # STEP 8: Update campaign database
            # Update scene prompt
            scenes[self.scene_index]['background_prompt'] = modified_prompt
            scenes[self.scene_index]['edit_count'] = scenes[self.scene_index].get('edit_count', 0) + 1
            scenes[self.scene_index]['last_edited_at'] = datetime.utcnow().isoformat() + "Z"
            
            # Update variationPaths with new final video URL
            # This ensures frontend gets the updated video URL
            variation_index = self.campaign.selected_variation_index or 0
            new_final_video_url = final_result['url']  # New presigned URL
            
            if 'variationPaths' not in campaign_json:
                campaign_json['variationPaths'] = {}
            
            if f'variation_{variation_index}' not in campaign_json['variationPaths']:
                campaign_json['variationPaths'][f'variation_{variation_index}'] = {
                    'aspectExports': {}
                }
            
            # Update the 9:16 aspect export with new URL
            campaign_json['variationPaths'][f'variation_{variation_index}']['aspectExports']['9:16'] = new_final_video_url
            
            logger.info(f"✅ Updated variationPaths with new final video URL for variation_{variation_index}")
            
            # Add to edit history
            if 'edit_history' not in campaign_json:
                campaign_json['edit_history'] = {
                    'edits': [],
                    'total_edit_cost': 0.0,
                    'edit_count': 0
                }
            
            edit_record = edit_service.create_edit_record(
                scene_index=self.scene_index,
                edit_prompt=self.edit_instruction,
                original_prompt=original_prompt,
                modified_prompt=modified_prompt,
                changes_summary=changes_summary,
                cost=total_cost,
                duration_seconds=int(time.time() - start_time)
            )
            
            campaign_json['edit_history']['edits'].append(edit_record)
            campaign_json['edit_history']['total_edit_cost'] += total_cost
            campaign_json['edit_history']['edit_count'] += 1
            
            # Update campaign
            update_campaign(
                self.db,
                self.campaign_id,
                campaign_json=campaign_json,
                cost=float(self.campaign.cost) + total_cost,
                status="completed"
            )
            
            # STEP 9: Cleanup temps
            for temp in scene_temps + [final_video_path]:
                if os.path.exists(temp):
                    try:
                        os.unlink(temp)
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {temp}: {e}")
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Scene edit complete! Time: {elapsed:.1f}s, Cost: ${total_cost:.2f}")
            
            return {
                "success": True,
                "campaign_id": str(self.campaign_id),
                "scene_index": self.scene_index,
                "cost": total_cost,
                "duration_seconds": int(elapsed),
                "changes_summary": changes_summary,
                "new_video_url": final_result['url']
            }
            
        except Exception as e:
            logger.error(f"❌ Scene edit failed: {e}", exc_info=True)
            update_campaign(self.db, self.campaign_id, status="failed", error_message=str(e))
            raise
        
        finally:
            self.db.close()


# Job entry point for RQ
def edit_scene_job(campaign_id: str, scene_index: int, edit_instruction: str) -> Dict[str, Any]:
    """
    RQ job function for scene editing.
    
    This is the entry point called by RQ worker.
    Runs in a forked child process on macOS.
    
    Args:
        campaign_id: String UUID of campaign
        scene_index: Scene index to edit (0-based)
        edit_instruction: User's edit instruction/prompt
        
    Returns:
        Dict with edit result
    """
    try:
        # Ensure environment variable is set (should be set by shell script)
        import os
        os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
        
        # Reinitialize database connection in child process
        from app.database.connection import init_db
        init_db()
        
        logger.info(f"Starting edit pipeline for campaign {campaign_id}, scene {scene_index}")
        pipeline = SceneEditPipeline(
            campaign_id=UUID(campaign_id),
            scene_index=scene_index,
            edit_instruction=edit_instruction
        )
        
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
        logger.warning(f"Edit interrupted for campaign {campaign_id}, scene {scene_index}")
        raise
    except Exception as e:
        logger.error(f"RQ edit job failed for campaign {campaign_id}, scene {scene_index}: {e}", exc_info=True)
        return {
            "success": False,
            "campaign_id": campaign_id,
            "scene_index": scene_index,
            "error": str(e),
        }

