"""Text Overlay Renderer Service - Add text overlays to videos.

This service uses FFmpeg to add animated text overlays to videos with
support for positioning, animations, and styling.

For luxury perfume ads, use add_perfume_text_overlay() which enforces
luxury typography constraints (max 3-4 text blocks, luxury fonts, restricted positions).
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import aiohttp
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


# ============================================================================
# Luxury Typography Presets
# ============================================================================

class LuxuryTextPreset:
    """Luxury typography presets for perfume ads."""
    
    SERIF_LUXURY = {
        "font": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "style": "elegant serif",
        "weight": "regular",
        "letter_spacing": 2,
        "font_size": 56,
    }
    
    SANS_MINIMAL = {
        "font": "/System/Library/Fonts/Helvetica.ttc",
        "style": "clean sans-serif",
        "weight": "light",
        "letter_spacing": 1,
        "font_size": 42,
    }
    
    @staticmethod
    def get_font_path(preset: Dict[str, Any]) -> str:
        """Get font file path, with fallback to system default."""
        font_path = preset.get("font", "")
        if Path(font_path).exists():
            return font_path
        
        # Fallback to system fonts
        if "serif" in preset.get("style", "").lower():
            # Try common serif fonts
            fallbacks = [
                "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            ]
        else:
            # Try common sans-serif fonts
            fallbacks = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ]
        
        for fallback in fallbacks:
            if Path(fallback).exists():
                logger.debug(f"Using fallback font: {fallback}")
                return fallback
        
        # Last resort: return empty (FFmpeg will use default)
        logger.warning("No luxury font found, using FFmpeg default")
        return ""


# ============================================================================
# Text Overlay Renderer Service
# ============================================================================

class TextOverlayRenderer:
    """Renders text overlays on videos using FFmpeg."""

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        s3_bucket_name: str,
        aws_region: str = "us-east-1",
    ):
        """Initialize with AWS S3 credentials."""
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.s3_bucket_name = s3_bucket_name
        self.aws_region = aws_region

    async def add_text_overlay(
        self,
        video_url: str,
        text: str,
        position: str = "bottom",
        duration: float = 2.0,
        start_time: float = 0.0,
        font_size: int = 48,
        color: str = "white",
        animation: str = "fade_in",
        project_id: str = "",
        scene_index: int = 0,
        font_preset: Optional[Dict[str, Any]] = None,
        variation_index: Optional[int] = None,
    ) -> str:
        """
        Add text overlay to TikTok vertical video (9:16 positioning).

        Args:
            video_url: URL/path of video to overlay
            text: Text to display
            position: Text position ("top", "bottom", "center")
            duration: How long text displays (seconds)
            start_time: When text appears (seconds into video)
            font_size: Font size in pixels
            color: Text color (hex or named color)
            animation: Animation type ("fade_in", "slide", "none")
            project_id: Project UUID for local path
            scene_index: Scene index for unique filenames
            font_preset: Optional luxury font preset dict (for perfume ads)

        Returns:
            Local file path of video with text overlay
        """
        logger.info(f"Adding text overlay to TikTok vertical: '{text}' at {position}")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Download video
                video_path = Path(tmpdir) / "video.mp4"
                await self._download_file(video_url, video_path)

                # Add text overlay using FFmpeg (TikTok vertical 9:16)
                output_path = Path(tmpdir) / "with_text.mp4"
                await self._render_text_overlay(
                    input_video=video_path,
                    output_video=output_path,
                    text=text,
                    position=position,
                    duration=duration,
                    start_time=start_time,
                    font_size=font_size,
                    color=color,
                    animation=animation,
                    font_preset=font_preset,
                )

                # Save locally
                local_path = await self._save_video_locally(output_path, project_id, scene_index, variation_index)

                logger.info(f"✅ Text overlay added: {local_path}")
                return local_path

            except Exception as e:
                logger.error(f"Error adding text overlay: {e}")
                raise

    async def add_multiple_overlays(
        self,
        video_url: str,
        overlays: list,
        project_id: str = "",
    ) -> str:
        """
        Add multiple text overlays to video sequentially.

        Args:
            video_url: S3 URL of base video
            overlays: List of overlay dicts with text, position, etc.
            project_id: Project UUID

        Returns:
            S3 URL of video with all overlays
        """
        logger.info(f"Adding {len(overlays)} text overlays...")

        current_url = video_url

        for i, overlay in enumerate(overlays):
            logger.debug(f"Overlay {i+1}/{len(overlays)}: {overlay.get('text', '')}")

            current_url = await self.add_text_overlay(
                video_url=current_url,
                text=overlay.get("text", ""),
                position=overlay.get("position", "bottom"),
                duration=overlay.get("duration", 2.0),
                start_time=overlay.get("start_time", 0.0),
                font_size=overlay.get("font_size", 48),
                color=overlay.get("color", "white"),
                animation=overlay.get("animation", "fade_in"),
                project_id=project_id,
            )

        logger.info(f"✅ All {len(overlays)} overlays added")
        return current_url

    def _validate_perfume_text(self, text: str, max_words: int = 6) -> bool:
        """Validate text overlay for perfume ads.
        
        Args:
            text: Text to validate
            max_words: Maximum allowed words (default: 6)
            
        Returns:
            True if valid, False if too long
        """
        word_count = len(text.split())
        
        if word_count > max_words:
            logger.warning(f"Text too long: {word_count} words (max {max_words})")
            return False
        
        return True

    async def add_perfume_text_overlay(
        self,
        video_url: str,
        text: str,
        text_type: str,  # 'perfume_name', 'tagline', 'brand_name', 'cta'
        position: str = "bottom",
        duration: float = 2.0,
        start_time: float = 0.0,
        project_id: str = "",
        scene_index: int = 0,
        variation_index: Optional[int] = None,
    ) -> str:
        """
        Add luxury typography text overlay for perfume ads.
        
        Enforces perfume-specific constraints:
        - Max 6 words per text block
        - Luxury fonts (serif for names, sans-serif for taglines)
        - Restricted positions (center/bottom center only)
        - Fade-in/out animations only
        
        Args:
            video_url: URL/path of video to overlay
            text: Text to display
            text_type: Type of text ('perfume_name', 'tagline', 'brand_name', 'cta')
            position: Text position ("center" or "bottom" only)
            duration: How long text displays (seconds, 2-4s recommended)
            start_time: When text appears (seconds into video)
            project_id: Project UUID for local path
            scene_index: Scene index for unique filenames
            
        Returns:
            Local file path of video with text overlay
        """
        logger.info(f"Adding luxury perfume text overlay: '{text}' ({text_type}) at {position}")
        
        # Validate text length
        if not self._validate_perfume_text(text, max_words=6):
            logger.warning("Text too long, truncating to 6 words...")
            text = " ".join(text.split()[:6])
        
        # Restrict positions to center/bottom only
        if position not in ["center", "bottom"]:
            logger.warning(f"Position '{position}' not allowed for perfume ads, using 'bottom'")
            position = "bottom"
        
        # Get font preset based on text type
        if text_type in ["perfume_name", "brand_name"]:
            font_preset = LuxuryTextPreset.SERIF_LUXURY
            font_size = font_preset["font_size"]
        else:  # tagline, cta
            font_preset = LuxuryTextPreset.SANS_MINIMAL
            font_size = font_preset["font_size"]
        
        # Use luxury text overlay with fade animation
        return await self.add_text_overlay(
            video_url=video_url,
            text=text,
            position=position,
            duration=duration,
            start_time=start_time,
            font_size=font_size,
            color="#FFFFFF",  # White for luxury contrast
            animation="fade_in",  # Fade-in/out only
            project_id=project_id,
            scene_index=scene_index,
            font_preset=font_preset,  # Pass preset for font file
            variation_index=variation_index,  # Pass variation index
        )

    async def _download_file(self, url: str, output_path: Path):
        """Download file from URL (S3 or HTTP) or copy from local path."""
        try:
            # Check if it's a local file path (starts with / or contains /tmp/)
            if url.startswith('/') or '/tmp/' in url or url.startswith('./'):
                import shutil
                source_path = Path(url)
                if not source_path.exists():
                    raise FileNotFoundError(f"Local file not found: {url}")
                shutil.copy2(source_path, output_path)
                logger.debug(f"Copied from local: {output_path.name}")
                return
            
            # Check if it's an S3 URL
            if '.s3.' in url or 's3.amazonaws.com' in url:
                from app.utils.s3_utils import parse_s3_url
                
                # Parse S3 URL to get bucket and key
                bucket_name, s3_key = parse_s3_url(url)
                
                # Download using boto3
                self.s3_client.download_file(
                    bucket_name,
                    s3_key,
                    str(output_path)
                )
                logger.info(f"✅ Downloaded from S3: {s3_key} → {output_path.name}")
            else:
                # Use HTTP for non-S3 URLs (e.g., Replicate URLs)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                        if resp.status == 200:
                            with open(output_path, "wb") as f:
                                f.write(await resp.read())
                            logger.debug(f"Downloaded via HTTP: {output_path.name}")
                        else:
                            raise ValueError(f"HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise

    async def _render_text_overlay(
        self,
        input_video: Path,
        output_video: Path,
        text: str,
        position: str,
        duration: float,
        start_time: float,
        font_size: int,
        color: str,
        animation: str,
        font_preset: Optional[Dict[str, Any]] = None,
    ):
        """Render text overlay using FFmpeg with TikTok vertical (9:16) positioning."""
        try:
            # Convert color name to hex if needed
            color_hex = self._normalize_color(color)

            # Calculate position (TikTok vertical 9:16)
            x_expr, y_expr = self._get_vertical_position_expr(position)

            # Build FFmpeg filter
            filter_complex = self._build_filter_complex(
                text=text,
                x_expr=x_expr,
                y_expr=y_expr,
                font_size=font_size,
                color=color_hex,
                duration=duration,
                start_time=start_time,
                animation=animation,
                font_preset=font_preset,
            )

            # FFmpeg command
            cmd = [
                "ffmpeg",
                "-i",
                str(input_video),
                "-filter_complex",
                filter_complex,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-c:a",
                "aac",
                "-q:v",
                "5",
                "-y",
                str(output_video),
            ]

            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")

            logger.info(f"Text overlay rendered: {output_video}")

        except Exception as e:
            logger.error(f"Error rendering text: {e}")
            raise

    def _normalize_color(self, color: str) -> str:
        """Convert color names to hex."""
        color_map = {
            "white": "FFFFFF",
            "black": "000000",
            "red": "FF0000",
            "green": "00FF00",
            "blue": "0000FF",
            "yellow": "FFFF00",
            "cyan": "00FFFF",
            "magenta": "FF00FF",
        }

        if color.lower() in color_map:
            return f"0x{color_map[color.lower()]}"

        # Already hex
        if color.startswith("0x") or color.startswith("#"):
            return color.replace("#", "0x")

        return "0xFFFFFF"  # Default to white

    def _get_vertical_position_expr(self, position: str):
        """
        Get FFmpeg position expressions for TikTok vertical (9:16).
        
        For perfume ads, only "center" and "bottom" are allowed.
        Other positions fall back to "bottom".
        
        Args:
            position: Logical position ("top", "bottom", "center", etc.)
            
        Returns:
            Tuple of (x_expr, y_expr) for FFmpeg
        """
        # TikTok vertical (9:16) positioning - optimized for mobile UI
        # For perfume ads: restricted to center/bottom only
        positions = {
            "top": ("(w-text_w)/2", "h*0.15"),  # More space for UI elements
            "bottom": ("(w-text_w)/2", "h*0.75"),  # Higher up to avoid captions/CTAs
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "top-left": ("20", "20"),
            "top-right": ("w-text_w-20", "20"),
            "bottom-left": ("20", "h-text_h-40"),
            "bottom-right": ("w-text_w-20", "h-text_h-40"),
        }
        
        return positions.get(position, positions["bottom"])

    def _build_filter_complex(
        self,
        text: str,
        x_expr: str,
        y_expr: str,
        font_size: int,
        color: str,
        duration: float,
        start_time: float,
        animation: str,
        font_preset: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build FFmpeg filter complex string.
        
        Args:
            text: Text to display
            x_expr: X position expression
            y_expr: Y position expression
            font_size: Font size in pixels
            color: Color hex code
            duration: Display duration
            start_time: Start time
            animation: Animation type
            font_preset: Optional luxury font preset dict
        """
        # Escape special characters in text
        text_escaped = text.replace("'", "\\'").replace(":", "\\:")

        # Get font file path
        font_file = ""
        if font_preset:
            font_file = LuxuryTextPreset.get_font_path(font_preset)
        else:
            # Default font fallback
            if Path("/System/Library/Fonts/Helvetica.ttc").exists():
                font_file = "/System/Library/Fonts/Helvetica.ttc"

        # Build drawtext filter
        drawtext_params = [
            f"text='{text_escaped}'",
            f"fontsize={font_size}",
            f"fontcolor={color}",
            f"x={x_expr}",
            f"y={y_expr}",
        ]
        
        # Add font file if available
        if font_file:
            drawtext_params.append(f"fontfile={font_file}")
        
        # Add letter spacing if luxury preset provided
        if font_preset and "letter_spacing" in font_preset:
            # FFmpeg doesn't support letter spacing directly, but we can simulate
            # by adjusting x position slightly (not perfect, but better than nothing)
            # For now, we'll skip this as FFmpeg drawtext doesn't have letter_spacing
            pass
        
        # Add fade animation (fade-in/out)
        fade_duration = 0.3  # 300ms fade
        alpha_expr = (
            f"if(lt(t,{start_time}),0,"
            f"if(lt(t,{start_time+fade_duration}),(t-{start_time})/{fade_duration},"
            f"if(lt(t,{start_time+duration}),1,"
            f"max(0,(1-(t-{start_time+duration})/{fade_duration})))))"
        )
        drawtext_params.append(f"alpha='{alpha_expr}'")

        drawtext_params = [p for p in drawtext_params if p]  # Remove empty strings
        drawtext_filter = "drawtext=" + ":".join(drawtext_params)

        return drawtext_filter

    async def _save_video_locally(self, video_path: Path, project_id: str, scene_index: int = 0, variation_index: Optional[int] = None) -> str:
        """Save video to local filesystem."""
        try:
            import shutil
            
            # Create directory structure: /tmp/genads/{project_id}/draft/text_overlays/
            save_dir = Path(f"/tmp/genads/{project_id}/draft/text_overlays")
            save_dir.mkdir(parents=True, exist_ok=True)

            # Copy to permanent location with descriptive name (include variation index if provided)
            if variation_index is not None:
                local_path = save_dir / f"scene_{variation_index}_{scene_index:02d}_text.mp4"
            else:
                local_path = save_dir / f"scene_{scene_index:02d}_text.mp4"
            shutil.copy2(video_path, local_path)
            
            logger.info(f"✅ Saved locally: {local_path}")
            return str(local_path)

        except Exception as e:
            logger.error(f"Local save error: {e}")
            raise

