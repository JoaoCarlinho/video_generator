"""Compositor Service - Product compositing onto background videos.

This service overlays extracted product images onto background videos,
positioning them with proper scaling and opacity for product showcase.
"""

import logging
import io
import subprocess
import tempfile
from typing import Tuple, Optional
from pathlib import Path
from PIL import Image
import aiohttp
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Safe imports for OpenCV and NumPy
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except (ImportError, OSError) as e:
    logger.warning(f"OpenCV/NumPy not available: {e}. Compositing will be disabled.")
    cv2 = None
    np = None
    CV2_AVAILABLE = False


# ============================================================================
# Compositor Service
# ============================================================================

class Compositor:
    """Composites product images onto background videos."""

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

    async def composite_product(
        self,
        background_video_url: str,
        product_image_url: str,
        project_id: str,
        position: str = "center",
        scale: float = 0.3,
        opacity: float = 1.0,
        scene_index: int = 0,
    ) -> str:
        """
        Composite product image onto background video.

        Args:
            background_video_url: S3 URL of background video
            product_image_url: S3 URL of extracted product PNG
            project_id: Project UUID for S3 path organization
            position: Position on screen ("center", "bottom-right", "top-left", etc.)
            scale: Product size as fraction of frame (0.1 to 1.0)
            opacity: Product opacity (0.0 to 1.0)

        Returns:
            S3 URL of composited video
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available - skipping compositing, returning background video as-is")
            return background_video_url
        
        logger.info(f"Compositing product onto video: {position} at {scale*100}% scale")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Download background video
                bg_video_path = Path(tmpdir) / "background.mp4"
                await self._download_file(background_video_url, bg_video_path)

                # Download product image
                product_path = Path(tmpdir) / "product.png"
                await self._download_file(product_image_url, product_path)

                # Load product image
                product_image = cv2.imread(str(product_path), cv2.IMREAD_UNCHANGED)
                if product_image is None:
                    logger.error("Could not load product image")
                    raise ValueError("Failed to load product image")

                # Get video properties
                video_props = await self._get_video_properties(bg_video_path)
                frame_width = video_props["width"]
                frame_height = video_props["height"]
                fps = video_props["fps"]
                frame_count = video_props["frame_count"]

                # Composite video frame by frame
                output_path = Path(tmpdir) / "composited.mp4"
                await self._composite_video_frames(
                    input_video_path=bg_video_path,
                    product_image=product_image,
                    output_path=output_path,
                    frame_width=frame_width,
                    frame_height=frame_height,
                    position=position,
                    scale=scale,
                    opacity=opacity,
                )

                # Upload composited video to S3
                s3_url = await self._upload_video_to_s3(output_path, project_id, scene_index)

                logger.info(f"✅ Composited video uploaded: {s3_url}")
                return s3_url

            except Exception as e:
                logger.error(f"Error in compositing: {e}")
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
                logger.info(f"Downloaded from S3: {output_path}")
            else:
                # Use HTTP for non-S3 URLs (e.g., Replicate URLs)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                        if resp.status == 200:
                            with open(output_path, "wb") as f:
                                f.write(await resp.read())
                            logger.info(f"Downloaded via HTTP: {output_path}")
                        else:
                            raise ValueError(f"HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise

    async def _get_video_properties(self, video_path: Path) -> dict:
        """Get video properties using FFprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate",
                "-of",
                "csv=p=0",
                str(video_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout.strip()

            parts = output.split(",")
            width = int(parts[0])
            height = int(parts[1])

            # Parse frame rate (e.g., "30/1" or "30")
            fps_str = parts[2]
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = int(num) / int(den)
            else:
                fps = int(fps_str)

            # Get frame count
            cmd2 = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-count",
                "packets",
                "-show_entries",
                "stream=nb_read_packets",
                "-of",
                "csv=p=0",
                str(video_path),
            ]

            result2 = subprocess.run(cmd2, capture_output=True, text=True)
            frame_count = int(result2.stdout.strip()) if result2.stdout.strip() else 0

            return {
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
            }

        except Exception as e:
            logger.error(f"Error getting video properties: {e}")
            # Return defaults
            return {"width": 1920, "height": 1080, "fps": 30, "frame_count": 150}

    async def _composite_video_frames(
        self,
        input_video_path: Path,
        product_image: np.ndarray,
        output_path: Path,
        frame_width: int,
        frame_height: int,
        position: str,
        scale: float,
        opacity: float,
    ):
        """Composite product onto each frame using OpenCV."""
        try:
            # Open input video
            cap = cv2.VideoCapture(str(input_video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Prepare output video writer
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_width, frame_height))

            # Calculate product dimensions
            product_height = int(frame_height * scale)
            product_width = int(product_image.shape[1] * (product_height / product_image.shape[0]))

            # Resize product
            product_resized = cv2.resize(product_image, (product_width, product_height))

            # Calculate position
            x, y = self._calculate_position(
                frame_width, frame_height, product_width, product_height, position
            )

            # Process frames
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Composite product onto frame
                frame_composited = self._blend_image_onto_frame(
                    frame, product_resized, x, y, opacity
                )

                out.write(frame_composited)
                frame_idx += 1

                if frame_idx % 30 == 0:
                    logger.debug(f"Processed {frame_idx}/{frame_count} frames")

            cap.release()
            out.release()

            logger.info(f"✅ Composited video: {output_path}")

        except Exception as e:
            logger.error(f"Error compositing frames: {e}")
            raise

    def _calculate_position(
        self,
        frame_width: int,
        frame_height: int,
        product_width: int,
        product_height: int,
        position: str,
    ) -> Tuple[int, int]:
        """Calculate product position in frame."""
        margin = 40  # pixels from edge

        positions = {
            "center": (
                (frame_width - product_width) // 2,
                (frame_height - product_height) // 2,
            ),
            "top-left": (margin, margin),
            "top-right": (frame_width - product_width - margin, margin),
            "bottom-left": (margin, frame_height - product_height - margin),
            "bottom-right": (
                frame_width - product_width - margin,
                frame_height - product_height - margin,
            ),
            "bottom-center": (
                (frame_width - product_width) // 2,
                frame_height - product_height - margin,
            ),
        }

        return positions.get(position, positions["center"])

    def _blend_image_onto_frame(
        self,
        frame: np.ndarray,
        product: np.ndarray,
        x: int,
        y: int,
        opacity: float,
    ) -> np.ndarray:
        """Blend product image onto frame using alpha blending."""
        try:
            # Ensure coordinates are valid
            x = max(0, min(x, frame.shape[1] - product.shape[1]))
            y = max(0, min(y, frame.shape[0] - product.shape[0]))

            # Extract region of interest
            roi = frame[y : y + product.shape[0], x : x + product.shape[1]]

            # If product has alpha channel, use it
            if product.shape[2] == 4:
                alpha = product[:, :, 3].astype(float) / 255.0 * opacity
                alpha = np.stack([alpha] * 3, axis=2)

                product_rgb = product[:, :, :3]
            else:
                alpha = opacity
                product_rgb = product

            # Blend
            blended = (product_rgb * alpha + roi * (1 - alpha)).astype(np.uint8)

            # Copy back
            frame[y : y + product.shape[0], x : x + product.shape[1]] = blended

            return frame

        except Exception as e:
            logger.error(f"Error blending: {e}")
            return frame

    async def _upload_video_to_s3(self, video_path: Path, project_id: str, scene_index: int = 0) -> str:
        """Upload composited video to S3."""
        try:
            # S3 RESTRUCTURING: Use new project folder structure
            s3_key = f"projects/{project_id}/draft/composited_videos/scene_{scene_index:02d}_composited.mp4"

            with open(video_path, "rb") as f:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket_name,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType="video/mp4",
                    # ACL removed - bucket doesn't allow ACLs, use bucket policy instead
                )

            s3_url = f"https://{self.s3_bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            logger.info(f"✅ Uploaded to S3: {s3_url}")

            return s3_url

        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise

