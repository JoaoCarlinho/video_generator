"""ECS-hosted Wan2.5 video generation provider.

This module implements the ECS provider for video generation, which communicates
with the internal ALB endpoint fronting VPC-hosted Wan2.5 inference containers
on GPU instances (g5.xlarge).
"""

import logging
from typing import Optional
import aiohttp

from app.services.providers.base import BaseVideoProvider

logger = logging.getLogger(__name__)


class ECSVideoProvider(BaseVideoProvider):
    """ECS provider for video generation using VPC-hosted Wan2.5 model.

    This provider communicates with the internal Application Load Balancer that
    distributes traffic across ECS tasks running Wan2.5 inference containers on
    GPU instances. The endpoint is only accessible from within the VPC.

    Attributes:
        endpoint_url: Internal ALB DNS name (e.g., http://internal-adgen-ecs-alb-123...)
    """

    def __init__(self, endpoint_url: str):
        """Initialize ECS video provider.

        Args:
            endpoint_url: Internal ALB endpoint URL for Wan2.5 inference service.
                Format: http://<alb-dns-name> (port 80)
        """
        self.endpoint_url = endpoint_url.rstrip('/')  # Remove trailing slash
        self.logger = logger

    async def generate_scene_background(
        self,
        prompt: str,
        style_spec_dict: dict,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
        extracted_style: Optional[dict] = None,
        style_override: Optional[str] = None,
    ) -> str:
        """Generate video using ECS-hosted Wan2.5 model.

        Args:
            prompt: Text description of the scene to generate
            style_spec_dict: Style specifications (camera movement, lighting, etc.)
            duration: Video duration in seconds (default: 5.0)
            aspect_ratio: Video aspect ratio (default: "16:9")
            seed: Optional random seed for reproducible generation
            extracted_style: Optional extracted style attributes
            style_override: Optional style override string

        Returns:
            str: URL to the generated video file in S3

        Raises:
            aiohttp.ClientError: Connection or timeout errors
            ValueError: Invalid response from ECS endpoint
        """
        # Build request payload
        payload = {
            "prompt": prompt,
            "style_spec": style_spec_dict,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }

        # Add optional parameters
        if seed is not None:
            payload["seed"] = seed
        if extracted_style is not None:
            payload["extracted_style"] = extracted_style
        if style_override is not None:
            payload["style_override"] = style_override

        # Log request
        self.logger.info(f"ECS endpoint: Generating video via {self.endpoint_url}/generate")
        self.logger.debug(f"ECS payload: {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                # Set 300-second timeout for inference (5 minutes max)
                timeout = aiohttp.ClientTimeout(total=300)

                async with session.post(
                    f"{self.endpoint_url}/generate",
                    json=payload,
                    timeout=timeout,
                ) as response:
                    # Raise error for HTTP error responses
                    response.raise_for_status()

                    # Parse JSON response
                    try:
                        data = await response.json()
                    except Exception as e:
                        self.logger.error(f"ECS endpoint returned invalid JSON: {e}")
                        raise ValueError(f"Invalid response from ECS endpoint: {e}")

                    # Extract video URL
                    if "video_url" not in data:
                        self.logger.error(f"ECS endpoint response missing 'video_url': {data}")
                        raise ValueError("ECS endpoint response missing 'video_url' field")

                    video_url = data["video_url"]
                    self.logger.info(f"ECS endpoint: Video generated successfully: {video_url}")

                    return video_url

        except aiohttp.ClientTimeout as e:
            self.logger.error(f"ECS endpoint timeout after 300s: {e}")
            raise

        except aiohttp.ClientConnectorError as e:
            self.logger.error(f"ECS endpoint connection failed: {self.endpoint_url} - {e}")
            raise

        except aiohttp.ClientResponseError as e:
            self.logger.error(
                f"ECS endpoint HTTP error: {e.status} - {e.message} - URL: {self.endpoint_url}"
            )
            raise

        except Exception as e:
            self.logger.error(f"ECS endpoint unexpected error: {e}", exc_info=True)
            raise

    async def health_check(self) -> bool:
        """Check if ECS endpoint is healthy.

        Performs a lightweight health check against the ECS ALB endpoint.
        Returns True if the endpoint is accessible and returns 200 OK.

        Returns:
            bool: True if endpoint is healthy, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Set 5-second timeout for health check
                timeout = aiohttp.ClientTimeout(total=5)

                async with session.get(
                    f"{self.endpoint_url}/health",
                    timeout=timeout,
                ) as response:
                    is_healthy = response.status == 200

                    if is_healthy:
                        self.logger.info(f"ECS endpoint healthy: {self.endpoint_url}")
                    else:
                        self.logger.warning(
                            f"ECS endpoint unhealthy: {self.endpoint_url} - status: {response.status}"
                        )

                    return is_healthy

        except aiohttp.ClientTimeout:
            self.logger.warning(f"ECS endpoint health check timeout: {self.endpoint_url}")
            return False

        except aiohttp.ClientConnectorError:
            self.logger.warning(f"ECS endpoint not reachable: {self.endpoint_url}")
            return False

        except Exception as e:
            self.logger.warning(f"ECS endpoint health check failed: {e}")
            return False

    def get_provider_name(self) -> str:
        """Return provider name identifier.

        Returns:
            str: "ecs"
        """
        return "ecs"
