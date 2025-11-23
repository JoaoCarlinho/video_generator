"""Product Shot Grammar Loader.

Loads and validates perfume-specific scene grammar constraints for TikTok vertical videos.
Ensures LLM-generated scenes follow luxury perfume visual language.

Version: 1.0
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProductGrammarLoader:
    """Loads perfume shot grammar rules and constraints.
    
    Manages the perfume_shot_grammar.json file which defines:
    - Allowed shot types (macro_bottle, aesthetic_broll, atmospheric, human_silhouette, brand_moment)
    - Scene flow rules (first/last scene requirements)
    - Text overlay constraints
    - Pacing guidelines based on video duration
    - Validation rules for scene plans
    """

    def __init__(self, grammar_file_path: Optional[str] = None):
        """Initialize loader with grammar file path.
        
        Args:
            grammar_file_path: Optional path to grammar JSON file.
                              Defaults to backend/app/templates/scene_grammar/perfume_shot_grammar.json
        """
        if grammar_file_path is None:
            # Default path relative to this file
            base_dir = Path(__file__).parent.parent
            grammar_file_path = base_dir / "templates" / "scene_grammar" / "perfume_shot_grammar.json"

        self.grammar_file_path = Path(grammar_file_path)
        self.grammar: Optional[Dict[str, Any]] = None
        self._load_grammar()

    def _load_grammar(self) -> None:
        """Load grammar from JSON file.
        
        Raises:
            FileNotFoundError: If grammar file doesn't exist
            json.JSONDecodeError: If grammar file is invalid JSON
        """
        try:
            with open(self.grammar_file_path, "r") as f:
                self.grammar = json.load(f)
            
            version = self.grammar.get("grammar_version", "1.0")
            logger.info(f"✅ Loaded perfume shot grammar v{version}")
            logger.debug(f"   Shot types: {list(self.grammar.get('allowed_shot_types', {}).keys())}")
        except FileNotFoundError:
            logger.error(f"❌ Grammar file not found: {self.grammar_file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in grammar file: {e}")
            raise

    def get_allowed_shot_types(self) -> Dict[str, Dict[str, Any]]:
        """Get all allowed shot types with their configurations.
        
        Returns:
            Dict mapping shot type IDs to their full configuration including
            variations, camera movements, lighting keywords, etc.
        """
        return self.grammar.get("allowed_shot_types", {})

    def get_shot_type_ids(self) -> List[str]:
        """Get list of allowed shot type IDs (for LLM constraint).
        
        Returns:
            List of IDs like ["macro_bottle", "aesthetic_broll", "atmospheric", ...]
        """
        shot_types = self.get_allowed_shot_types()
        return [config.get("id") for config in shot_types.values()]

    def get_scene_count_for_duration(self, duration: int) -> int:
        """Determine optimal scene count based on duration.
        
        Args:
            duration: Video duration in seconds (15-60)
            
        Returns:
            Recommended number of scenes (3-5)
        """
        pacing = self.grammar.get("pacing_guidelines", {})

        if duration <= 30:
            return pacing.get("15_30_seconds", {}).get("scene_count", 3)
        elif duration <= 45:
            return pacing.get("31_45_seconds", {}).get("scene_count", 4)
        else:
            return pacing.get("46_60_seconds", {}).get("scene_count", 5)

    def get_avg_scene_duration_for_count(self, scene_count: int) -> Tuple[float, float]:
        """Get recommended average scene duration based on scene count.
        
        Args:
            scene_count: Number of scenes (3, 4, or 5)
            
        Returns:
            Tuple of (min_duration, max_duration) in seconds
        """
        pacing = self.grammar.get("pacing_guidelines", {})

        if scene_count <= 3:
            return tuple(pacing.get("15_30_seconds", {}).get("avg_scene_duration", [5, 10]))
        elif scene_count == 4:
            return tuple(pacing.get("31_45_seconds", {}).get("avg_scene_duration", [7, 11]))
        else:
            return tuple(pacing.get("46_60_seconds", {}).get("avg_scene_duration", [9, 12]))

    def get_flow_rules(self) -> Dict[str, Any]:
        """Get scene flow rules (first/last scene requirements, etc).
        
        Returns:
            Dict containing:
            - first_scene_must_be: List of allowed first shot types
            - last_scene_must_be: List of allowed last shot types
            - max_consecutive_same_type: Max times same type can appear consecutively
            - product_visibility_rules: Rules about product appearance
        """
        return self.grammar.get("scene_flow_rules", {})

    def get_text_overlay_rules(self) -> Dict[str, Any]:
        """Get text overlay constraints.
        
        Returns:
            Dict containing:
            - max_text_blocks: Maximum text elements (usually 3)
            - allowed_positions: Where text can appear (top, center, bottom)
            - font_style: Allowed fonts (serif_luxury, sans_minimal)
            - max_words_per_block: Word limit per text element
            - required_text_scenes: Which scenes must have text
        """
        return self.grammar.get("text_overlay_rules", {})

    def get_pacing_guidelines(self) -> Dict[str, Any]:
        """Get pacing guidelines for different durations.
        
        Returns:
            Dict with breakdowns for 15-30s, 31-45s, 46-60s videos
        """
        return self.grammar.get("pacing_guidelines", {})

    def validate_scene_plan(self, scenes: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate a scene plan against all grammar rules.

        Args:
            scenes: List of scene dictionaries with fields like:
                   - shot_type: One of the allowed shot type IDs
                   - duration: Scene duration in seconds
                   - use_product: Boolean indicating if product is visible

        Returns:
            Tuple of (is_valid: bool, violations: List[str])
            If is_valid is True, violations will be empty list.
            If is_valid is False, violations contains human-readable error messages.
        """
        violations = []
        flow_rules = self.get_flow_rules()
        shot_types = self.get_shot_type_ids()

        # Check if we have scenes
        if not scenes:
            violations.append("Scene plan cannot be empty")
            return (False, violations)

        # Validate each scene
        for i, scene in enumerate(scenes):
            shot_type = scene.get("shot_type")
            duration = scene.get("duration", 0)

            # Check shot type is valid
            if shot_type not in shot_types:
                violations.append(
                    f"Scene {i+1}: Invalid shot_type '{shot_type}'. "
                    f"Must be one of: {', '.join(shot_types)}"
                )

            # Check duration is in valid range
            if duration < 3 or duration > 8:
                violations.append(
                    f"Scene {i+1}: Duration {duration}s is outside valid range (3-8 seconds)"
                )

        # Check first scene
        first_type = scenes[0].get("shot_type")
        allowed_first = flow_rules.get("first_scene_must_be", [])
        if first_type not in allowed_first:
            violations.append(
                f"First scene must be one of {allowed_first}, got '{first_type}'"
            )

        # Check last scene
        last_type = scenes[-1].get("shot_type")
        allowed_last = flow_rules.get("last_scene_must_be", [])
        if last_type not in allowed_last:
            violations.append(
                f"Last scene must be '{allowed_last[0]}', got '{last_type}'"
            )

        # Check max consecutive same type
        max_consecutive = flow_rules.get("max_consecutive_same_type", 2)
        consecutive_count = 1
        for i in range(1, len(scenes)):
            if scenes[i].get("shot_type") == scenes[i - 1].get("shot_type"):
                consecutive_count += 1
                if consecutive_count > max_consecutive:
                    violations.append(
                        f"Too many consecutive '{scenes[i].get('shot_type')}' shots "
                        f"(max {max_consecutive})"
                    )
            else:
                consecutive_count = 1

        # Check product visibility rules
        product_rules = flow_rules.get("product_visibility_rules", {})
        product_scenes = [s for s in scenes if s.get("use_product", False)]
        min_product = product_rules.get("minimum_product_scenes", 2)
        max_product = product_rules.get("maximum_product_scenes", 4)

        if len(product_scenes) < min_product:
            violations.append(
                f"Need at least {min_product} product scenes, got {len(product_scenes)}"
            )
        if len(product_scenes) > max_product:
            violations.append(
                f"Maximum {max_product} product scenes allowed, got {len(product_scenes)}"
            )

        # Check if product appears in required scenes
        must_show_in = product_rules.get("must_show_product_in", [])
        if "final" in must_show_in and len(scenes) > 0:
            if not scenes[-1].get("use_product", False):
                violations.append("Final scene must show the product")

        return (len(violations) == 0, violations)

    def get_llm_constraint_prompt(self, duration: int) -> str:
        """Generate LLM constraint prompt enforcing perfume grammar.

        Args:
            duration: Target video duration in seconds

        Returns:
            Formatted prompt string to include in LLM request
        """
        scene_count = self.get_scene_count_for_duration(duration)
        shot_type_ids = self.get_shot_type_ids()
        template = self.grammar.get("llm_prompt_template", "")

        constraint_prompt = template.format(scene_count=scene_count)

        # Add shot type details
        shot_types = self.get_allowed_shot_types()
        shot_descriptions = []
        for shot_type_id, config in shot_types.items():
            shot_id = config.get("id")
            display_name = config.get("display_name")
            description = config.get("description")
            shot_descriptions.append(f"- {shot_id}: {display_name} - {description}")

        constraint_prompt += "\n\nALLOWED SHOT TYPES:\n" + "\n".join(shot_descriptions)

        return constraint_prompt

    def get_validation_summary(self, scene_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get detailed validation summary of a scene plan.

        Args:
            scene_plan: List of scene dictionaries

        Returns:
            Dict with validation details:
            - is_valid: Boolean
            - violations: List of violation messages
            - scene_count: Number of scenes
            - total_duration: Total duration in seconds
            - product_appearances: Count of product scenes
            - shot_type_breakdown: Dict of shot types and their counts
        """
        is_valid, violations = self.validate_scene_plan(scene_plan)
        
        total_duration = sum(s.get("duration", 0) for s in scene_plan)
        product_scenes = sum(1 for s in scene_plan if s.get("use_product", False))
        
        # Build shot type breakdown
        shot_breakdown: Dict[str, int] = {}
        for scene in scene_plan:
            shot_type = scene.get("shot_type", "unknown")
            shot_breakdown[shot_type] = shot_breakdown.get(shot_type, 0) + 1

        return {
            "is_valid": is_valid,
            "violations": violations,
            "scene_count": len(scene_plan),
            "total_duration": total_duration,
            "product_appearances": product_scenes,
            "shot_type_breakdown": shot_breakdown,
        }

    def reload_grammar(self) -> None:
        """Reload grammar from file (useful for hot-reloading during development)."""
        self._load_grammar()
        logger.info("✅ Grammar reloaded")


# Example usage
if __name__ == "__main__":
    # Test the loader
    loader = ProductGrammarLoader()

    # Get allowed shot types
    shot_types = loader.get_allowed_shot_types()
    print(f"✅ Loaded {len(shot_types)} shot types")

    # Get scene count for 30s video
    scene_count = loader.get_scene_count_for_duration(30)
    print(f"✅ Recommended {scene_count} scenes for 30s video")

    # Get constraint prompt
    prompt = loader.get_llm_constraint_prompt(30)
    print(f"✅ Generated LLM constraint prompt ({len(prompt)} chars)")

    # Validate example scene plan
    example_scenes = [
        {"shot_type": "macro_bottle", "duration": 5, "use_product": True},
        {"shot_type": "aesthetic_broll", "duration": 4, "use_product": False},
        {"shot_type": "brand_moment", "duration": 5, "use_product": True},
    ]

    is_valid, violations = loader.validate_scene_plan(example_scenes)
    print(f"✅ Scene plan valid: {is_valid}")
    if violations:
        print(f"   Violations: {violations}")

    summary = loader.get_validation_summary(example_scenes)
    print(f"✅ Validation summary: {summary}")

