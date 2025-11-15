"""Product Extractor Service - Background removal and product isolation.

This service takes a product image, removes the background using rembg,
and uploads the result to S3 for use in compositing.
"""

import logging
import io
from typing import Optional, Tuple
from PIL import Image
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
        Extract product from image and upload masked PNG to S3.

        Args:
            image_url: URL of product image
            project_id: Project UUID for S3 path organization

        Returns:
            S3 URL of extracted product PNG with transparent background
        """
        logger.info(f"Extracting product from {image_url}")

        try:
            # Download image
            image_data = await self._download_image(image_url)
            if image_data is None:
                logger.error(f"Failed to download image from {image_url}")
                raise ValueError(f"Could not download image from {image_url}")

            # Remove background
            extracted_image = await self._remove_background(image_data)

            # Upload to S3
            s3_url = await self._upload_to_s3(extracted_image, project_id)

            logger.info(f"✅ Product extracted and uploaded to {s3_url}")
            return s3_url

        except Exception as e:
            logger.error(f"Error extracting product: {e}")
            raise

    async def _download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        logger.error(f"Failed to download image: HTTP {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
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

    async def _upload_to_s3(self, image: Image.Image, project_id: str) -> str:
        """Upload extracted product image to S3."""
        try:
            # Convert to PNG bytes
            png_buffer = io.BytesIO()
            image.save(png_buffer, format="PNG")
            png_buffer.seek(0)

            # Upload to S3 (S3 RESTRUCTURING: Use new project folder structure)
            s3_key = f"projects/{project_id}/draft/product/extracted.png"

            self.s3_client.put_object(
                Bucket=self.s3_bucket_name,
                Key=s3_key,
                Body=png_buffer.getvalue(),
                ContentType="image/png",
                # ACL removed - bucket doesn't allow ACLs, use bucket policy instead
            )

            # Generate URL
            s3_url = f"https://{self.s3_bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"

            logger.info(f"✅ Uploaded product to S3: {s3_url}")
            return s3_url

        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise

    async def get_product_dimensions(self, s3_url: str) -> Tuple[int, int]:
        """Get dimensions of extracted product image."""
        try:
            image_data = await self._download_image(s3_url)
            if image_data:
                img = Image.open(io.BytesIO(image_data))
                return img.size  # (width, height)
            return (0, 0)
        except Exception as e:
            logger.error(f"Error getting product dimensions: {e}")
            return (0, 0)

