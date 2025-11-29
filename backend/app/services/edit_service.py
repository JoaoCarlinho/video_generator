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
        product_name: str,
        product_type: str
    ) -> Dict[str, str]:
        """
        Modify scene prompt based on user's edit instruction.

        Args:
            original_prompt: Current scene prompt
            edit_instruction: User's edit request (e.g., "make brighter")
            style_spec: Campaign's style specification
            scene_role: Scene role (hook, showcase, cta, etc.)
            product_name: Name of the product
            product_type: Type of product (fragrance, watch, car, energy)

        Returns:
            Dict with:
              - modified_prompt: New prompt with edits applied
              - changes_summary: Human-readable summary of changes
        """
        logger.info(f"Modifying scene prompt - Role: {scene_role}, Edit: '{edit_instruction}'")
        
        system_prompt = f"""You are an expert video director editing luxury {product_type} TikTok ads.

Given an original scene prompt and an edit instruction, modify the prompt to incorporate the changes while maintaining:
1. The core scene concept and composition
2. Product shot grammar rules (luxury, elegant, cinematic)
3. Overall style consistency with the campaign
4. TikTok vertical (9:16) optimization
5. User-first creative philosophy (honor the user's vision)

IMPORTANT:
- Apply the edit instruction precisely
- Keep the same scene structure (duration, role, transitions)
- Maintain {product_type} product visibility and placement
- Preserve brand visual identity
- Add specific cinematography details (lighting, camera, movement)

Return a JSON object with:
{{
  "modified_prompt": "The full modified prompt with changes applied",
  "changes_summary": "Brief 2-3 sentence summary of what changed"
}}"""
        
        user_message = f"""Original Scene Prompt:
{original_prompt}

Edit Instruction: {edit_instruction}

Context:
- Scene Role: {scene_role}
- Product: {product_name}
- Product Type: {product_type}
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
        changes_summary: str,
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
            "changes_summary": changes_summary,
            "cost": cost,
            "duration_seconds": duration_seconds
        }

