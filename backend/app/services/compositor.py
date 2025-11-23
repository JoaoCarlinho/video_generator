"""Compositor Service - Product bottle compositing onto TikTok vertical videos.

This service overlays extracted perfume bottle images onto background videos,
positioning them with TikTok vertical safe zones (15-75% vertical space)
and perfume-specific scaling based on scene role.
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
    """Composites perfume bottle images onto TikTok vertical background videos."""

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
        campaign_id: str,
        position: str = "center",
        scale: Optional[float] = None,
        opacity: float = 1.0,
        scene_index: int = 0,
        scene_role: Optional[str] = None,
        variation_index: Optional[int] = None,
    ) -> str:
        """
        Composite perfume bottle image onto TikTok vertical background video.

        Args:
            background_video_url: S3 URL or local path of background video
            product_image_url: S3 URL or local path of extracted perfume bottle PNG
            campaign_id: Campaign UUID for local path organization
            position: Position preset ("center", "center_upper", "center_lower")
            scale: Optional scale override (0.1 to 1.0). If None, uses scene_role-based scaling
            opacity: Product opacity (0.0 to 1.0)
            scene_index: Scene index for filename
            scene_role: Scene role ("hook", "showcase", "cta") for automatic scaling

        Returns:
            Local path to composited video
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available - skipping compositing, returning background video as-is")
            return background_video_url
        
        # Use scene role-based scaling if scale not provided
        if scale is None:
            if scene_role:
                scale = self._get_perfume_scale(scene_role)
                logger.info(f"Using scene role-based scale: {scene_role} → {scale*100:.0f}%")
            else:
                scale = 0.5  # Default perfume bottle scale
                logger.info(f"Using default perfume scale: {scale*100:.0f}%")
        
        logger.info(f"Compositing perfume bottle onto TikTok vertical video: {position} at {scale*100:.0f}% scale")

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

                # Save composited video locally
                local_path = await self._save_video_locally(output_path, campaign_id, scene_index, variation_index)

                logger.info(f"✅ Composited video saved: {local_path}")
                return local_path

            except Exception as e:
                logger.error(f"Error in compositing: {e}")
                raise

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
                logger.info(f"✅ Downloaded from S3: {s3_key} → {output_path}")
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

            # Calculate perfume-specific position (TikTok vertical optimized)
            x, y = self._calculate_perfume_position(
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

    def _calculate_perfume_position(
        self,
        frame_width: int,
        frame_height: int,
        product_width: int,
        product_height: int,
        position: str,
    ) -> Tuple[int, int]:
        """
        Calculate perfume bottle position (TikTok vertical optimized).
        
        TikTok vertical safe zones (9:16 aspect ratio):
        - Top 15%: UI elements (avoid)
        - Bottom 25%: captions/CTAs (avoid)
        - Safe zone: 15-75% vertical space
        
        Args:
            frame_width: Video frame width (1080 for TikTok vertical)
            frame_height: Video frame height (1920 for TikTok vertical)
            product_width: Product image width
            product_height: Product image height
            position: Position preset ("center", "center_upper", "center_lower")
            
        Returns:
            Tuple of (x, y) coordinates for product placement
        """
        # Calculate TikTok vertical safe zones
        safe_top = int(frame_height * 0.15)  # Top 15% - UI elements
        safe_bottom = int(frame_height * 0.75)  # Bottom 25% - captions
        safe_height = safe_bottom - safe_top
        
        positions = {
            "center": (
                (frame_width - product_width) // 2,  # Centered horizontally
                safe_top + (safe_height - product_height) // 2  # Centered in safe zone
            ),
            "center_upper": (
                (frame_width - product_width) // 2,  # Centered horizontally
                safe_top + int(safe_height * 0.3)  # Upper third of safe zone
            ),
            "center_lower": (
                (frame_width - product_width) // 2,  # Centered horizontally
                safe_top + int(safe_height * 0.6)  # Lower third of safe zone
            ),
        }
        
        return positions.get(position, positions["center"])
    
    def _get_perfume_scale(self, scene_role: str) -> float:
        """
        Get optimal perfume bottle scale based on scene role.
        
        Args:
            scene_role: Scene role ("hook", "showcase", "cta", "default")
            
        Returns:
            Scale factor (0.1 to 1.0) as fraction of frame height
        """
        scales = {
            "hook": 0.5,      # Medium size for hook scenes
            "showcase": 0.6,   # Larger for product focus scenes
            "cta": 0.5,       # Medium for final CTA moment
            "default": 0.5
        }
        return scales.get(scene_role, scales["default"])

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

    async def _save_video_locally(self, video_path: Path, campaign_id: str, scene_index: int = 0, variation_index: Optional[int] = None) -> str:
        """Save composited video to local filesystem."""
        try:
            import shutil
            
            # Create directory structure: /tmp/genads/{campaign_id}/draft/composited/
            save_dir = Path(f"/tmp/genads/{campaign_id}/draft/composited")
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy to permanent location with descriptive name (include variation index if provided)
            if variation_index is not None:
                local_path = save_dir / f"scene_{variation_index}_{scene_index:02d}_composited.mp4"
            else:
                local_path = save_dir / f"scene_{scene_index:02d}_composited.mp4"
            shutil.copy2(video_path, local_path)
            
            logger.info(f"✅ Saved locally: {local_path}")
            return str(local_path)

        except Exception as e:
            logger.error(f"Local save error: {e}")
            raise

    async def composite_logo(
        self,
        video_url: str,
        logo_image_url: str,
        campaign_id: str,
        position: str = "top_right",
        scale: float = 0.1,
        opacity: float = 0.9,
        scene_index: int = 0,
        variation_index: Optional[int] = None,
    ) -> str:
        """
        Composite logo onto video (similar to product compositing).
        
        Task 4: New method to actually overlay logo images onto video scenes.
        
        Args:
            video_url: Video to overlay logo onto (local path)
            logo_image_url: Logo image URL (S3)
            campaign_id: Campaign UUID
            position: Logo position (top_left, top_right, bottom_left, bottom_right, bottom_center)
            scale: Logo size as fraction of frame height (0.05-0.2)
            opacity: Logo opacity (0.0-1.0)
            scene_index: Scene index for filename
            
        Returns:
            Local path to video with logo
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available - skipping logo compositing")
            return video_url
        
        logger.info(f"🏷️  Compositing logo onto video: {position} at {scale*100:.0f}% scale, opacity={opacity:.2f}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Download logo
                logo_path = Path(tmpdir) / "logo.png"
                await self._download_file(logo_image_url, logo_path)
                
                # Load logo
                logo_image = cv2.imread(str(logo_path), cv2.IMREAD_UNCHANGED)
                if logo_image is None:
                    logger.warning("Could not load logo image, skipping")
                    return video_url
                
                # Get video properties
                video_props = await self._get_video_properties(video_url)
                
                # Composite logo frame by frame (reuse product compositing logic)
                output_path = Path(tmpdir) / "with_logo.mp4"
                await self._composite_video_frames(
                    input_video_path=video_url,
                    product_image=logo_image,  # Reuse product compositing logic
                    output_path=output_path,
                    frame_width=video_props["width"],
                    frame_height=video_props["height"],
                    position=position,
                    scale=scale,
                    opacity=opacity,
                )
                
                # Save locally
                local_path = await self._save_logo_video_locally(output_path, campaign_id, scene_index, variation_index)
                
                logger.info(f"✅ Logo composited: {local_path}")
                return local_path
                
            except Exception as e:
                logger.error(f"Error compositing logo: {e}")
                # Non-critical failure - return original video
                return video_url

    async def _save_logo_video_locally(self, video_path: Path, campaign_id: str, scene_index: int = 0, variation_index: Optional[int] = None) -> str:
        """Save video with logo to local filesystem."""
        try:
            import shutil
            
            save_dir = Path(f"/tmp/genads/{campaign_id}/draft/logo")
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Include variation index in filename if provided
            if variation_index is not None:
                local_path = save_dir / f"scene_{variation_index}_{scene_index:02d}_logo.mp4"
            else:
                local_path = save_dir / f"scene_{scene_index:02d}_logo.mp4"
            shutil.copy2(video_path, local_path)
            
            logger.info(f"✅ Saved locally: {local_path}")
            return str(local_path)
            
        except Exception as e:
            logger.error(f"Local save error: {e}")
            raise

