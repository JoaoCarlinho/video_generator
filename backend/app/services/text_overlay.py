"""Text Overlay Renderer Service - Add text overlays to videos.

This service uses FFmpeg to add animated text overlays to videos with
support for positioning, animations, and styling.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import aiohttp
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


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
    ) -> str:
        """
        Add text overlay to video.

        Args:
            video_url: S3 URL of video to overlay
            text: Text to display
            position: Text position ("top", "bottom", "center")
            duration: How long text displays (seconds)
            start_time: When text appears (seconds into video)
            font_size: Font size in pixels
            color: Text color (hex or named color)
            animation: Animation type ("fade_in", "slide", "none")
            project_id: Project UUID for S3 path

        Returns:
            S3 URL of video with text overlay
        """
        logger.info(f"Adding text overlay: '{text}' at {position}")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Download video
                video_path = Path(tmpdir) / "video.mp4"
                await self._download_file(video_url, video_path)

                # Add text overlay using FFmpeg
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
                )

                # Upload to S3
                s3_url = await self._upload_video_to_s3(output_path, project_id, scene_index)

                logger.info(f"✅ Text overlay added: {s3_url}")
                return s3_url

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

    async def _download_file(self, url: str, output_path: Path):
        """Download file from URL (S3 or HTTP)."""
        try:
            # Check if it's an S3 URL
            if f"s3.{self.aws_region}.amazonaws.com" in url or f"s3.amazonaws.com/{self.s3_bucket_name}" in url:
                # Extract S3 key from URL
                # Format: https://bucket.s3.region.amazonaws.com/projects/id/file.mp4
                if f"s3.{self.aws_region}.amazonaws.com" in url:
                    s3_key = url.split(f".s3.{self.aws_region}.amazonaws.com/")[1]
                else:
                    s3_key = url.split(f"s3.amazonaws.com/{self.s3_bucket_name}/")[1]
                
                # Download using boto3
                self.s3_client.download_file(
                    self.s3_bucket_name,
                    s3_key,
                    str(output_path)
                )
                logger.debug(f"Downloaded from S3: {output_path.name}")
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
    ):
        """Render text overlay using FFmpeg."""
        try:
            # Convert color name to hex if needed
            color_hex = self._normalize_color(color)

            # Calculate position
            x_expr, y_expr = self._get_position_expr(position)

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

    def _get_position_expr(self, position: str):
        """Get FFmpeg position expressions."""
        positions = {
            "top": ("(w-text_w)/2", "h*0.1"),
            "bottom": ("(w-text_w)/2", "h*0.85"),
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "top-left": ("10", "10"),
            "top-right": ("w-text_w-10", "10"),
            "bottom-left": ("10", "h-text_h-10"),
            "bottom-right": ("w-text_w-10", "h-text_h-10"),
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
    ) -> str:
        """Build FFmpeg filter complex string."""

        # Escape special characters in text
        text_escaped = text.replace("'", "\\'").replace(":", "\\:")

        # Build drawtext filter
        drawtext_params = [
            f"text='{text_escaped}'",
            f"fontsize={font_size}",
            f"fontcolor={color}",
            f"x={x_expr}",
            f"y={y_expr}",
            "fontfile=/System/Library/Fonts/Helvetica.ttc" if Path("/System/Library/Fonts").exists()
            else "",  # macOS default font
            f"alpha='if(lt(t,{start_time}),0,if(lt(t,{start_time+0.3}),(t-{start_time})/0.3,if(lt(t,{start_time+duration}),1,max(0,(1-(t-{start_time+duration})/0.3)))))'",
        ]

        drawtext_params = [p for p in drawtext_params if p]  # Remove empty strings
        drawtext_filter = "drawtext=" + ":".join(drawtext_params)

        # Combine filters
        filter_complex = f"[0:v]{drawtext_filter}[v];[v][0:a]concat=n=1:v=1:a=1[out]"

        # Simplified filter for better compatibility
        filter_complex = drawtext_filter

        return filter_complex

    async def _upload_video_to_s3(self, video_path: Path, project_id: str, scene_index: int = 0) -> str:
        """Upload video to S3."""
        try:
            # S3 RESTRUCTURING: Use new project folder structure
            s3_key = f"projects/{project_id}/draft/text_overlays/scene_{scene_index:02d}_text.mp4"

            with open(video_path, "rb") as f:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket_name,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType="video/mp4",
                    # ACL removed - bucket doesn't allow ACLs, use bucket policy instead
                )

            s3_url = f"https://{self.s3_bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"

            return s3_url

        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise

