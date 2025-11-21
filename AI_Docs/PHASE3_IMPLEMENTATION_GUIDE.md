# Phase 3: AI Scene Editing - Detailed Implementation Guide

**Version:** 1.0  
**Created:** January 20, 2025  
**Purpose:** Detailed code examples and implementation patterns for Phase 3

---

## Table of Contents

1. [Backend Code Examples](#backend-code-examples)
2. [Frontend Code Examples](#frontend-code-examples)
3. [Database Migration Details](#database-migration-details)
4. [S3 Integration Patterns](#s3-integration-patterns)
5. [Error Handling Patterns](#error-handling-patterns)
6. [Testing Examples](#testing-examples)

---

## Backend Code Examples

### EditService - Complete Implementation

**File:** `backend/app/services/edit_service.py`

```python
"""Scene editing service for prompt-based modifications."""

import logging
import uuid
import json
from typing import Dict, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class EditService:
    """Service for editing campaign scenes via prompt modifications."""
    
    def __init__(self, openai_api_key: str):
        """Initialize with OpenAI API key."""
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = "gpt-4o-mini"
        logger.info("✅ EditService initialized")
    
    async def modify_scene_prompt(
        self,
        original_prompt: str,
        edit_instruction: str,
        style_spec: Dict[str, Any],
        scene_role: str,
        perfume_name: str
    ) -> Dict[str, str]:
        """
        Modify scene prompt based on user's edit instruction.
        
        Args:
            original_prompt: Current scene prompt
            edit_instruction: User's edit request (e.g., "make brighter")
            style_spec: Campaign's style specification
            scene_role: Scene role (hook, showcase, cta, etc.)
            perfume_name: Name of the perfume product
            
        Returns:
            Dict with:
              - modified_prompt: New prompt with edits applied
              - changes_summary: Human-readable summary of changes
        """
        logger.info(f"Modifying scene prompt - Role: {scene_role}, Edit: '{edit_instruction}'")
        
        system_prompt = """You are an expert video director editing luxury perfume TikTok ads.

Given an original scene prompt and an edit instruction, modify the prompt to incorporate the changes while maintaining:
1. The core scene concept and composition
2. Perfume shot grammar rules (luxury, elegant, cinematic)
3. Overall style consistency with the campaign
4. TikTok vertical (9:16) optimization
5. User-first creative philosophy (honor the user's vision)

IMPORTANT:
- Apply the edit instruction precisely
- Keep the same scene structure (duration, role, transitions)
- Maintain perfume product visibility and placement
- Preserve brand visual identity
- Add specific cinematography details (lighting, camera, movement)

Return a JSON object with:
{
  "modified_prompt": "The full modified prompt with changes applied",
  "changes_summary": "Brief 2-3 sentence summary of what changed"
}"""
        
        user_message = f"""Original Scene Prompt:
{original_prompt}

Edit Instruction: {edit_instruction}

Context:
- Scene Role: {scene_role}
- Perfume: {perfume_name}
- Style Spec:
  - Lighting: {style_spec.get('lighting_direction', 'N/A')}
  - Camera: {style_spec.get('camera_style', 'N/A')}
  - Mood: {style_spec.get('mood_atmosphere', 'N/A')}
  - Colors: {', '.join(style_spec.get('color_palette', []))}

Modified Prompt (JSON):"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            logger.info(f"✅ Prompt modified successfully")
            logger.info(f"Changes: {result.get('changes_summary', 'N/A')}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM response as JSON: {e}")
            raise ValueError("LLM returned invalid JSON response")
        except Exception as e:
            logger.error(f"❌ Failed to modify prompt: {e}")
            raise
    
    def create_edit_record(
        self,
        scene_index: int,
        edit_prompt: str,
        original_prompt: str,
        modified_prompt: str,
        cost: float,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """
        Create edit history record for campaign_json.
        
        Returns:
            Edit record dict
        """
        return {
            "edit_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "scene_index": scene_index,
            "edit_prompt": edit_prompt,
            "original_prompt": original_prompt,
            "modified_prompt": modified_prompt,
            "cost": cost,
            "duration_seconds": duration_seconds
        }
```

---

### SceneEditPipeline - Complete Implementation

**File:** `backend/app/jobs/edit_pipeline.py`

```python
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
    get_final_video_s3_url
)

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
        
        init_db()
        self.db = db_connection.SessionLocal()
        
        # Load campaign
        self.campaign = get_campaign_by_id(self.db, campaign_id)
        if not self.campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        logger.info(f"Initialized edit pipeline for campaign {campaign_id}, scene {scene_index}")
    
    async def run(self) -> Dict[str, Any]:
        """Execute scene edit pipeline."""
        start_time = time.time()
        total_cost = 0.0
        
        try:
            logger.info(f"Starting scene edit: Campaign {self.campaign_id}, Scene {self.scene_index}")
            
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
            perfume_name = campaign_json.get('perfume_name', 'Perfume')
            
            logger.info(f"Scene {self.scene_index}: role={scene_role}, duration={scene_duration}s")
            
            # STEP 2: Modify prompt via LLM
            from app.config import settings
            edit_service = EditService(openai_api_key=settings.openai_api_key)
            
            result = await edit_service.modify_scene_prompt(
                original_prompt=original_prompt,
                edit_instruction=self.edit_instruction,
                style_spec=style_spec,
                scene_role=scene_role,
                perfume_name=perfume_name
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
                brand_id=str(self.campaign.brand_id),
                perfume_id=str(self.campaign.perfume_id),
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
                        brand_id=str(self.campaign.brand_id),
                        perfume_id=str(self.campaign.perfume_id),
                        campaign_id=str(self.campaign_id),
                        variation_index=self.campaign.selected_variation_index or 0,
                        scene_index=i
                    )
                    all_scene_urls.append(scene_s3_url)
            
            # Download scenes temporarily
            scene_temps = []
            for url in all_scene_urls:
                temp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                # Download from S3 using boto3
                bucket_name, s3_key = self._parse_s3_url(url)
                s3_client = boto3.client('s3')
                s3_client.download_file(bucket_name, s3_key, temp.name)
                scene_temps.append(temp.name)
            
            # STEP 6: Re-render final video
            renderer = Renderer(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                s3_bucket_name=settings.s3_bucket_name,
                aws_region=settings.aws_region
            )
            
            # Get audio URL from campaign_json
            audio_url = campaign_json.get('audio_url', '')
            
            final_video_path = await renderer.render_final_video(
                scene_video_urls=scene_temps,
                audio_url=audio_url,
                project_id=str(self.campaign_id),
                variation_index=self.campaign.selected_variation_index or 0
            )
            
            # STEP 7: Upload new final video (replaces old)
            final_result = await upload_final_video(
                brand_id=str(self.campaign.brand_id),
                perfume_id=str(self.campaign.perfume_id),
                campaign_id=str(self.campaign_id),
                variation_index=self.campaign.selected_variation_index or 0,
                file_path=final_video_path
            )
            
            # STEP 8: Update campaign database
            # Update scene prompt
            scenes[self.scene_index]['background_prompt'] = modified_prompt
            scenes[self.scene_index]['edit_count'] = scenes[self.scene_index].get('edit_count', 0) + 1
            scenes[self.scene_index]['last_edited_at'] = datetime.utcnow().isoformat() + "Z"
            
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
                cost=total_cost,
                duration_seconds=int(time.time() - start_time)
            )
            edit_record['changes_summary'] = changes_summary
            
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
                    os.unlink(temp)
            
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
            logger.error(f"❌ Scene edit failed: {e}")
            update_campaign(self.db, self.campaign_id, status="failed", error_message=str(e))
            raise
        
        finally:
            self.db.close()
    
    def _parse_s3_url(self, url: str) -> tuple[str, str]:
        """Parse S3 URL into bucket name and key."""
        # Handle both s3:// and https:// formats
        if url.startswith('s3://'):
            parts = url.replace('s3://', '').split('/', 1)
            return parts[0], parts[1]
        elif 'amazonaws.com' in url:
            # https://bucket.s3.region.amazonaws.com/key
            parts = url.split('amazonaws.com/')
            bucket_part = parts[0].split('//')[1].split('.')[0]
            key = parts[1]
            return bucket_part, key
        else:
            raise ValueError(f"Invalid S3 URL format: {url}")


# Job entry point for RQ
async def edit_scene_job(campaign_id: str, scene_index: int, edit_instruction: str):
    """RQ job entry point for scene editing."""
    pipeline = SceneEditPipeline(
        campaign_id=UUID(campaign_id),
        scene_index=scene_index,
        edit_instruction=edit_instruction
    )
    return await pipeline.run()
```

---

### API Endpoints - Complete Implementation

**File:** `backend/app/api/editing.py`

```python
"""API endpoints for campaign editing."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.database.connection import get_db
from app.database.crud import get_campaign_by_id
from app.api.auth import get_current_user_id, verify_campaign_ownership
from app.jobs.worker import enqueue_job

router = APIRouter(prefix="/api/campaigns", tags=["editing"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class EditSceneRequest(BaseModel):
    """Request to edit a scene."""
    edit_prompt: str


class EditSceneResponse(BaseModel):
    """Response when edit job is enqueued."""
    job_id: str
    estimated_cost: float
    estimated_duration_seconds: int
    message: str


class SceneInfo(BaseModel):
    """Scene information for editing UI."""
    scene_index: int
    scene_id: int
    role: str
    duration: int
    background_prompt: str
    video_url: str
    thumbnail_url: Optional[str] = None
    edit_count: int = 0
    last_edited_at: Optional[str] = None


class EditHistoryRecord(BaseModel):
    """Single edit history record."""
    edit_id: str
    timestamp: str
    scene_index: int
    edit_prompt: str
    changes_summary: Optional[str] = None
    cost: float
    duration_seconds: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/{campaign_id}/scenes", response_model=List[SceneInfo])
async def get_campaign_scenes(
    campaign_id: UUID,
    variation_index: int = 0,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(lambda: verify_campaign_ownership(campaign_id, user_id))
):
    """
    Get all scenes for a campaign (for editing UI).
    
    Returns scene data with video URLs and thumbnails.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_json = campaign.campaign_json
    if isinstance(campaign_json, str):
        import json
        campaign_json = json.loads(campaign_json)
    
    scenes = campaign_json.get('scenes', [])
    
    from app.utils.s3_utils import get_scene_s3_url
    
    scene_infos = []
    for i, scene in enumerate(scenes):
        # Construct S3 URL for scene video
        video_url = get_scene_s3_url(
            brand_id=str(campaign.brand_id),
            perfume_id=str(campaign.perfume_id),
            campaign_id=str(campaign_id),
            variation_index=variation_index,
            scene_index=i
        )
        
        scene_infos.append(SceneInfo(
            scene_index=i,
            scene_id=scene.get('scene_id', i),
            role=scene.get('role', 'unknown'),
            duration=scene.get('duration', 4),
            background_prompt=scene.get('background_prompt', ''),
            video_url=video_url,
            thumbnail_url=None,  # TODO: Generate thumbnails
            edit_count=scene.get('edit_count', 0),
            last_edited_at=scene.get('last_edited_at')
        ))
    
    return scene_infos


@router.post("/{campaign_id}/scenes/{scene_index}/edit", response_model=EditSceneResponse)
async def edit_scene(
    campaign_id: UUID,
    scene_index: int,
    request: EditSceneRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(lambda: verify_campaign_ownership(campaign_id, user_id))
):
    """
    Edit a specific scene in a campaign.
    
    Enqueues an edit job and returns job ID for status polling.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_json = campaign.campaign_json
    if isinstance(campaign_json, str):
        import json
        campaign_json = json.loads(campaign_json)
    
    scenes = campaign_json.get('scenes', [])
    if scene_index >= len(scenes):
        raise HTTPException(status_code=400, detail=f"Scene index {scene_index} out of range")
    
    if not request.edit_prompt.strip():
        raise HTTPException(status_code=400, detail="Edit prompt cannot be empty")
    
    # Enqueue edit job
    job = enqueue_job(
        "edit_scene",
        campaign_id=str(campaign_id),
        scene_index=scene_index,
        edit_instruction=request.edit_prompt
    )
    
    return EditSceneResponse(
        job_id=job.id,
        estimated_cost=0.21,  # $0.01 LLM + $0.20 video
        estimated_duration_seconds=180,  # ~3 minutes
        message=f"Edit job enqueued for scene {scene_index}"
    )


@router.get("/{campaign_id}/edit-history", response_model=List[EditHistoryRecord])
async def get_edit_history(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(lambda: verify_campaign_ownership(campaign_id, user_id))
):
    """
    Get edit history for a campaign.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_json = campaign.campaign_json
    if isinstance(campaign_json, str):
        import json
        campaign_json = json.loads(campaign_json)
    
    edit_history = campaign_json.get('edit_history', {})
    edits = edit_history.get('edits', [])
    
    return [EditHistoryRecord(**edit) for edit in edits]
```

---

## Frontend Code Examples

### useSceneEditing Hook - Complete Implementation

**File:** `frontend/src/hooks/useSceneEditing.ts`

```typescript
import { useState, useCallback } from 'react';
import { editing } from '../services/api';
import { Scene, EditHistoryRecord } from '../types';

interface UseSceneEditingReturn {
  scenes: Scene[];
  isLoading: boolean;
  editingSceneIndex: number | null;
  error: string | null;
  loadScenes: (campaignId: string) => Promise<void>;
  editScene: (campaignId: string, sceneIndex: number, editPrompt: string) => Promise<void>;
  getEditHistory: (campaignId: string) => Promise<EditHistoryRecord[]>;
}

export const useSceneEditing = (): UseSceneEditingReturn => {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingSceneIndex, setEditingSceneIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadScenes = useCallback(async (campaignId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await editing.getScenes(campaignId);
      setScenes(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load scenes');
      console.error('Error loading scenes:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const pollEditJob = async (jobId: string): Promise<void> => {
    const maxAttempts = 120; // 4 minutes max (2s intervals)
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        const response = await fetch(`/api/generation/jobs/${jobId}/status`);
        const data = await response.json();
        
        if (data.status === 'completed') {
          return; // Success
        } else if (data.status === 'failed') {
          throw new Error(data.error || 'Edit failed');
        }
        
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2s
        attempts++;
      } catch (err) {
        throw err;
      }
    }
    
    throw new Error('Edit timeout - please refresh page');
  };

  const editScene = useCallback(async (
    campaignId: string,
    sceneIndex: number,
    editPrompt: string
  ) => {
    setEditingSceneIndex(sceneIndex);
    setError(null);
    
    try {
      // Submit edit request
      const response = await editing.editScene(campaignId, sceneIndex, editPrompt);
      const jobId = response.data.job_id;
      
      // Poll for completion
      await pollEditJob(jobId);
      
      // Reload scenes after successful edit
      await loadScenes(campaignId);
    } catch (err: any) {
      setError(err.message || 'Failed to edit scene');
      console.error('Error editing scene:', err);
      throw err;
    } finally {
      setEditingSceneIndex(null);
    }
  }, [loadScenes]);

  const getEditHistory = useCallback(async (campaignId: string): Promise<EditHistoryRecord[]> => {
    try {
      const response = await editing.getEditHistory(campaignId);
      return response.data;
    } catch (err: any) {
      console.error('Error loading edit history:', err);
      return [];
    }
  }, []);

  return {
    scenes,
    isLoading,
    editingSceneIndex,
    error,
    loadScenes,
    editScene,
    getEditHistory
  };
};
```

---

### SceneSidebar Component - Complete Implementation

**File:** `frontend/src/components/SceneSidebar.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { useSceneEditing } from '../hooks/useSceneEditing';
import { SceneCard } from './SceneCard';
import { EditScenePopup } from './EditScenePopup';
import { Scene } from '../types';

interface SceneSidebarProps {
  campaignId: string;
  onVideoUpdate: () => void;
}

export const SceneSidebar: React.FC<SceneSidebarProps> = ({
  campaignId,
  onVideoUpdate
}) => {
  const {
    scenes,
    isLoading,
    editingSceneIndex,
    error,
    loadScenes,
    editScene
  } = useSceneEditing();
  
  const [popupSceneIndex, setPopupSceneIndex] = useState<number | null>(null);
  
  useEffect(() => {
    loadScenes(campaignId);
  }, [campaignId, loadScenes]);
  
  const handleEditSubmit = async (sceneIndex: number, editPrompt: string) => {
    try {
      await editScene(campaignId, sceneIndex, editPrompt);
      setPopupSceneIndex(null);
      await loadScenes(campaignId); // Refresh scenes
      onVideoUpdate(); // Tell parent to reload video
    } catch (error) {
      // Error handling is done in hook
      console.error('Edit submission failed:', error);
    }
  };
  
  if (isLoading && scenes.length === 0) {
    return (
      <div className="scene-sidebar w-full lg:w-1/3 bg-charcoal-900 rounded-lg p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-400">Loading scenes...</div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="scene-sidebar w-full lg:w-1/3 bg-charcoal-900 rounded-lg p-6">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }
  
  return (
    <div className="scene-sidebar w-full lg:w-1/3 bg-charcoal-900 rounded-lg p-6 space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-white">
          Scenes ({scenes.length})
        </h3>
      </div>
      
      {/* Scene List */}
      <div className="space-y-4 max-h-[600px] overflow-y-auto">
        {scenes.map((scene) => (
          <SceneCard
            key={scene.scene_index}
            scene={scene}
            isEditing={editingSceneIndex === scene.scene_index}
            onEditClick={() => setPopupSceneIndex(scene.scene_index)}
          />
        ))}
      </div>
      
      {/* Edit Popup */}
      {popupSceneIndex !== null && scenes[popupSceneIndex] && (
        <EditScenePopup
          scene={scenes[popupSceneIndex]}
          isOpen={popupSceneIndex !== null}
          onClose={() => setPopupSceneIndex(null)}
          onSubmit={(prompt) => handleEditSubmit(popupSceneIndex, prompt)}
        />
      )}
    </div>
  );
};
```

---

## Database Migration Details

### Migration File Structure

**File:** `backend/alembic/versions/009_add_edit_history.py`

```python
"""Add edit history tracking to campaigns

Revision ID: 009
Revises: 008
Create Date: 2025-01-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Add edit_history column to campaigns table
    op.add_column(
        'campaigns',
        sa.Column('edit_history', postgresql.JSONB, nullable=True, comment='Edit history tracking')
    )
    
    # Create GIN index for efficient JSONB queries
    op.create_index(
        'idx_campaigns_edit_history',
        'campaigns',
        ['edit_history'],
        postgresql_using='gin',
        unique=False
    )
    
    # Initialize existing campaigns with empty edit history
    op.execute("""
        UPDATE campaigns 
        SET edit_history = '{"edits": [], "total_edit_cost": 0.0, "edit_count": 0}'::jsonb
        WHERE edit_history IS NULL
    """)


def downgrade():
    # Drop index first
    op.drop_index('idx_campaigns_edit_history', table_name='campaigns')
    
    # Drop column
    op.drop_column('campaigns', 'edit_history')
```

### Running the Migration

```bash
# Check current revision
alembic current

# Upgrade to latest
alembic upgrade head

# Verify migration
alembic history

# Rollback if needed
alembic downgrade -1
```

---

## S3 Integration Patterns

### S3 URL Construction Helpers

**File:** `backend/app/utils/s3_utils.py` (ADDITIONS)

```python
def get_scene_s3_url(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int,
    scene_index: int  # 0-based
) -> str:
    """
    Construct S3 URL for a scene video.
    
    Args:
        brand_id: Brand UUID string
        perfume_id: Perfume UUID string
        campaign_id: Campaign UUID string
        variation_index: Variation index (0, 1, 2)
        scene_index: Scene index (0-based)
        
    Returns:
        Full S3 URL string
    """
    from app.config import settings
    
    s3_key = (
        f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"
        f"variations/variation_{variation_index}/draft/scene_{scene_index+1}_bg.mp4"
    )
    
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"


def get_final_video_s3_url(
    brand_id: str,
    perfume_id: str,
    campaign_id: str,
    variation_index: int
) -> str:
    """
    Construct S3 URL for final video.
    
    Args:
        brand_id: Brand UUID string
        perfume_id: Perfume UUID string
        campaign_id: Campaign UUID string
        variation_index: Variation index (0, 1, 2)
        
    Returns:
        Full S3 URL string
    """
    from app.config import settings
    
    s3_key = (
        f"brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/"
        f"variations/variation_{variation_index}/final_video.mp4"
    )
    
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
```

---

## Error Handling Patterns

### Backend Error Handling

```python
# In SceneEditPipeline.run()
try:
    # ... edit pipeline steps ...
except ValueError as e:
    # Validation errors
    logger.error(f"Validation error: {e}")
    update_campaign(self.db, self.campaign_id, status="failed", error_message=str(e))
    raise HTTPException(status_code=400, detail=str(e))
except RuntimeError as e:
    # Runtime errors (S3, video generation)
    logger.error(f"Runtime error: {e}")
    update_campaign(self.db, self.campaign_id, status="failed", error_message=str(e))
    raise HTTPException(status_code=500, detail=str(e))
except Exception as e:
    # Unexpected errors
    logger.exception(f"Unexpected error: {e}")
    update_campaign(self.db, self.campaign_id, status="failed", error_message="Internal error")
    raise HTTPException(status_code=500, detail="Internal server error")
finally:
    # Always cleanup
    self._cleanup_temp_files()
    self.db.close()
```

### Frontend Error Handling

```typescript
// In useSceneEditing hook
const editScene = useCallback(async (...) => {
  try {
    // ... edit logic ...
  } catch (err: any) {
    // Handle different error types
    if (err.response?.status === 400) {
      setError('Invalid edit request. Please check your input.');
    } else if (err.response?.status === 404) {
      setError('Campaign or scene not found.');
    } else if (err.response?.status === 500) {
      setError('Server error. Please try again later.');
    } else if (err.message?.includes('timeout')) {
      setError('Edit timed out. Please refresh and try again.');
    } else {
      setError(err.message || 'Failed to edit scene.');
    }
    throw err; // Re-throw for component handling
  }
}, []);
```

---

## Testing Examples

### Backend Unit Test

**File:** `backend/tests/test_edit_service.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.edit_service import EditService

@pytest.mark.asyncio
async def test_modify_scene_prompt_brightening():
    """Test prompt modification for brightening request."""
    with patch('app.services.edit_service.AsyncOpenAI') as mock_openai:
        # Mock OpenAI response
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{"modified_prompt": "Bright scene", "changes_summary": "Made brighter"}'
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client
        
        service = EditService(api_key="test")
        result = await service.modify_scene_prompt(
            original_prompt="Dark moody perfume scene",
            edit_instruction="Make brighter",
            style_spec={},
            scene_role="showcase",
            perfume_name="Test"
        )
        
        assert "bright" in result['modified_prompt'].lower()
        assert result['changes_summary'] is not None
```

### Frontend Component Test

**File:** `frontend/src/components/__tests__/EditScenePopup.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EditScenePopup } from '../EditScenePopup';
import { Scene } from '../../types';

const mockScene: Scene = {
  scene_index: 1,
  scene_id: 1,
  role: 'showcase',
  duration: 4,
  background_prompt: 'Original prompt',
  video_url: 'http://example.com/video.mp4',
  edit_count: 0
};

describe('EditScenePopup', () => {
  it('renders correctly when open', () => {
    const onSubmit = jest.fn();
    render(
      <EditScenePopup
        scene={mockScene}
        isOpen={true}
        onClose={jest.fn()}
        onSubmit={onSubmit}
      />
    );
    
    expect(screen.getByText('Edit Scene 2 - showcase')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e.g., 'Make brighter/)).toBeInTheDocument();
  });
  
  it('calls onSubmit with prompt when submitted', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(
      <EditScenePopup
        scene={mockScene}
        isOpen={true}
        onClose={jest.fn()}
        onSubmit={onSubmit}
      />
    );
    
    const textarea = screen.getByPlaceholderText(/e.g., 'Make brighter/);
    fireEvent.change(textarea, { target: { value: 'Make brighter' } });
    
    const submitButton = screen.getByText('Edit Scene');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith('Make brighter');
    });
  });
});
```

---

**This implementation guide provides detailed code examples for all major components. Use this as a reference during implementation!** 🚀

