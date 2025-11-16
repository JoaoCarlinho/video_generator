"""Product Extractor Service - Background removal and product isolation.

This service takes a product image, removes the background using rembg,
and uploads the result to S3 for use in compositing.
"""

import logging
import io
from typing import Optional, Tuple
from PIL import Image
from urllib.parse import urlparse
import aiohttp
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# rembg / onnxruntime are heavy and may be unavailable on some Python versions.
# We treat them as OPTIONAL and gracefully fall back to using the original image
# if rembg cannot be imported or initialized.
try:  # pragma: no cover - environment-dependent
    from rembg import remove  # type: ignore
except Exception as e:  # ModuleNotFoundError, ImportError, runtime import error
    logger.warning(
        "rembg could not be loaded (background removal will be skipped): %s", e
    )
    remove = None  # type: ignore


# ============================================================================
# Product Extractor Service
# ============================================================================

class ProductExtractor:
    """Extracts products from images by removing backgrounds."""

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

    async def extract_product(
        self,
        image_url: str,
        project_id: str,
    ) -> str:
        """
        Extract product from image and save to local filesystem.

        Args:
            image_url: URL or local path of product image
            project_id: Project UUID for organizing local files

        Returns:
            Local file path of extracted product PNG with transparent background
        """
        logger.info(f"Extracting product from {image_url}")

        try:
            # Download/read image
            image_data = await self._download_image(image_url)
            if image_data is None:
                logger.error(f"Failed to read image from {image_url}")
                raise ValueError(f"Could not read image from {image_url}")

            # Remove background
            extracted_image = await self._remove_background(image_data)

            # Save to local filesystem
            local_path = await self._save_to_local(extracted_image, project_id)

            logger.info(f"✅ Product extracted and saved to {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"Error extracting product: {e}")
            raise

    async def _download_image(self, url_or_path: str) -> Optional[bytes]:
        """Download image from URL or read from local filesystem."""
        try:
            # Check if it's a local file path (starts with / or contains /tmp/)
            if url_or_path.startswith('/') or '/tmp/' in url_or_path:
                logger.info(f"Reading local file: {url_or_path}")
                
                # Read from local filesystem
                from pathlib import Path
                file_path = Path(url_or_path)
                
                if not file_path.exists():
                    logger.error(f"Local file not found: {url_or_path}")
                    return None
                
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                
                logger.info(f"✅ Read {len(image_data)} bytes from local file")
                return image_data
            
            # Parse URL to check if it's an S3 URL
            parsed_url = urlparse(url_or_path)
            
            # Check if it's an S3 URL (format: https://bucket.s3.region.amazonaws.com/key)
            if 's3.amazonaws.com' in parsed_url.netloc or 's3-' in parsed_url.netloc:
                # Extract bucket and key from S3 URL
                # Format: https://bucket.s3.region.amazonaws.com/path/to/file
                bucket_name = parsed_url.netloc.split('.')[0]
                s3_key = parsed_url.path.lstrip('/')
                
                logger.info(f"Downloading S3 object: s3://{bucket_name}/{s3_key}")
                
                # Download from S3 using credentials
                try:
                    response = self.s3_client.get_object(Bucket=bucket_name, Key=s3_key)
                    image_data = response['Body'].read()
                    logger.info(f"✅ Downloaded {len(image_data)} bytes from S3")
                    return image_data
                except ClientError as e:
                    logger.error(f"S3 download failed: {e}")
                    return None
            else:
                # Regular HTTP(S) URL - use aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url_or_path, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            return await resp.read()
                        else:
                            logger.error(f"Failed to download image: HTTP {resp.status}")
                            return None
        except Exception as e:
            logger.error(f"Error downloading/reading image: {e}")
            return None

    async def _remove_background(self, image_bytes: bytes) -> Image.Image:
        """
        Remove background from image using rembg if available.

        If rembg (or its dependencies like onnxruntime) are not available,
        this method will **gracefully fall back** to returning the original
        image with no background removal. This keeps the pipeline usable on
        environments where rembg wheels are not published yet (e.g. newer
        Python versions) at the cost of visual quality.
        """
        try:
            # Open image
            input_image = Image.open(io.BytesIO(image_bytes))

            # Ensure RGB mode for rembg
            if input_image.mode != "RGB" and input_image.mode != "RGBA":
                input_image = input_image.convert("RGB")

            # If rembg is not available, skip background removal
            if remove is None:
                logger.warning(
                    "rembg not available; skipping background removal and "
                    "using original image instead."
                )
                # Ensure we still return a format suitable for compositing
                return input_image.convert("RGBA")

            # Remove background via rembg
            output_image = remove(input_image)

            logger.info(f"Background removed: {input_image.size} → {output_image.size}")
            return output_image

        except Exception as e:
            logger.error(f"Error removing background: {e}")
            raise

    async def _save_to_local(self, image: Image.Image, project_id: str) -> str:
        """Save extracted product image to local filesystem."""
        try:
            from pathlib import Path
            
            # Create directory structure: /tmp/genads/{project_id}/draft/product/
            project_dir = Path(f"/tmp/genads/{project_id}/draft/product")
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as PNG
            local_path = project_dir / "extracted.png"
            image.save(local_path, format="PNG")

            logger.info(f"✅ Saved product to local filesystem: {local_path}")
            return str(local_path)

        except Exception as e:
            logger.error(f"Local save error: {e}")
            raise

    async def get_product_dimensions(self, file_path: str) -> Tuple[int, int]:
        """Get dimensions of extracted product image from local file or URL."""
        try:
            image_data = await self._download_image(file_path)
            if image_data:
                img = Image.open(io.BytesIO(image_data))
                return img.size  # (width, height)
            return (0, 0)
        except Exception as e:
            logger.error(f"Error getting product dimensions: {e}")
            return (0, 0)

