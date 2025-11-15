"""Renderer Service - Final video rendering and multi-aspect export.

This service combines composited video scenes with audio and generates
final videos in multiple aspect ratios (9:16, 1:1, 16:9).
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
import aiohttp
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


# ============================================================================
# Renderer Service
# ============================================================================

class Renderer:
    """Renders final videos in multiple aspect ratios."""

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

    async def render_final_video(
        self,
        scene_video_urls: List[str],
        audio_url: str,
        project_id: str,
        output_aspect_ratios: List[str] = None,
    ) -> Dict[str, str]:
        """
        Render final video with multiple aspect ratios.

        Args:
            scene_video_urls: List of S3 URLs of scene videos (in order)
            audio_url: S3 URL of background music
            project_id: Project UUID
            output_aspect_ratios: Aspect ratios to generate (default: all 3)

        Returns:
            Dict mapping aspect ratio to S3 URL
            e.g., {"9:16": "https://...", "1:1": "https://...", "16:9": "https://..."}
        """
        if output_aspect_ratios is None:
            output_aspect_ratios = ["9:16", "1:1", "16:9"]

        logger.info(f"Rendering final video in {output_aspect_ratios} aspect ratios")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Download all scene videos
                scene_paths = []
                for i, url in enumerate(scene_video_urls):
                    path = Path(tmpdir) / f"scene_{i:02d}.mp4"
                    await self._download_file(url, path)
                    scene_paths.append(path)

                # Download audio
                audio_path = Path(tmpdir) / "audio.mp3"
                await self._download_file(audio_url, audio_path)

                # Concatenate scene videos
                concat_path = Path(tmpdir) / "concatenated.mp4"
                await self._concatenate_videos(scene_paths, concat_path)

                # Mix with audio
                mixed_path = Path(tmpdir) / "with_audio.mp4"
                await self._mix_audio(concat_path, audio_path, mixed_path)

                # Generate outputs for each aspect ratio
                outputs = {}
                for aspect_ratio in output_aspect_ratios:
                    logger.info(f"Rendering {aspect_ratio} aspect ratio...")

                    output_path = Path(tmpdir) / f"final_{aspect_ratio.replace(':', '_')}.mp4"
                    await self._apply_aspect_ratio(mixed_path, output_path, aspect_ratio)

                    # Upload to S3
                    s3_url = await self._upload_final_video(output_path, project_id, aspect_ratio)
                    outputs[aspect_ratio] = s3_url

                logger.info(f"✅ Final videos rendered: {outputs}")
                return outputs

            except Exception as e:
                logger.error(f"Error rendering final video: {e}")
                raise

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
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                        if resp.status == 200:
                            with open(output_path, "wb") as f:
                                f.write(await resp.read())
                            logger.debug(f"Downloaded via HTTP: {output_path.name}")
                        else:
                            raise ValueError(f"HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise

    async def _concatenate_videos(self, video_paths: List[Path], output_path: Path):
        """Concatenate multiple videos using FFmpeg."""
        try:
            # Create concat demux file
            concat_file = output_path.parent / "concat_list.txt"
            with open(concat_file, "w") as f:
                for path in video_paths:
                    f.write(f"file '{path.absolute()}'\n")

            # FFmpeg concat command
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                "-y",
                str(output_path),
            ]

            logger.debug(f"Concatenating {len(video_paths)} videos...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"FFmpeg concat error: {result.stderr}")
                raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")

            logger.info(f"✅ Videos concatenated: {output_path}")

        except Exception as e:
            logger.error(f"Error concatenating videos: {e}")
            raise

    async def _mix_audio(self, video_path: Path, audio_path: Path, output_path: Path):
        """Mix video with audio using FFmpeg."""
        try:
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",  # End at shortest input
                "-y",
                str(output_path),
            ]

            logger.debug("Mixing audio with video...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"FFmpeg audio mix error: {result.stderr}")
                raise RuntimeError(f"FFmpeg mix failed: {result.stderr}")

            logger.info(f"✅ Audio mixed: {output_path}")

        except Exception as e:
            logger.error(f"Error mixing audio: {e}")
            raise

    async def _apply_aspect_ratio(self, input_path: Path, output_path: Path, aspect_ratio: str):
        """Apply aspect ratio using FFmpeg with padding."""
        try:
            # Aspect ratio dimensions
            aspect_map = {
                "16:9": (1920, 1080),
                "9:16": (1080, 1920),  # Portrait
                "1:1": (1080, 1080),  # Square
            }

            if aspect_ratio not in aspect_map:
                logger.warning(f"Unknown aspect ratio: {aspect_ratio}, using 16:9")
                aspect_ratio = "16:9"

            width, height = aspect_map[aspect_ratio]

            # Use scale and pad to achieve aspect ratio
            # This ensures content isn't cropped, just padded
            filter_str = (
                f"scale=min({width}\\,iw*{height}/ih):min({height}\\,ih*{width}/iw),"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
            )

            cmd = [
                "ffmpeg",
                "-i",
                str(input_path),
                "-vf",
                filter_str,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-q:a",
                "4",
                "-y",
                str(output_path),
            ]

            logger.debug(f"Applying {aspect_ratio} aspect ratio...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"FFmpeg aspect ratio error: {result.stderr}")
                raise RuntimeError(f"FFmpeg aspect ratio failed: {result.stderr}")

            logger.info(f"✅ {aspect_ratio} video rendered: {output_path}")

        except Exception as e:
            logger.error(f"Error applying aspect ratio: {e}")
            raise

    async def _upload_final_video(
        self, video_path: Path, project_id: str, aspect_ratio: str
    ) -> str:
        """Upload final video to S3."""
        try:
            # S3 RESTRUCTURING: Use new project folder structure with final/ subfolder
            aspect_tag = aspect_ratio.replace(':', '_')
            s3_key = f"projects/{project_id}/final/{project_id}_{aspect_tag}.mp4"

            file_size = video_path.stat().st_size
            logger.info(f"Uploading final video ({file_size / 1024 / 1024:.1f}MB)...")

            with open(video_path, "rb") as f:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket_name,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType="video/mp4",
                    # ACL removed - bucket doesn't allow ACLs, use bucket policy instead
                )

            s3_url = f"https://{self.s3_bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"

            logger.info(f"✅ Uploaded: {aspect_ratio} video ({s3_url})")
            return s3_url

        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise

    async def get_video_duration(self, video_url: str) -> float:
        """Get duration of video from FFprobe."""
        try:
            # This is a simplified version - in production, download and check locally
            logger.debug(f"Getting video duration: {video_url}")
            return 30.0  # Default 30s for now

        except Exception as e:
            logger.error(f"Error getting duration: {e}")
            return 30.0

