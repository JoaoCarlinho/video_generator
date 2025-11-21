"""Provider health check API endpoints."""

from fastapi import APIRouter
from cachetools import TTLCache
import logging

from backend.app.config import settings
from backend.app.services.providers.ecs import ECSVideoProvider
from backend.app.models.schemas import ProviderHealthStatus, ProvidersHealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple TTL cache for health check results (30 seconds)
health_cache = TTLCache(maxsize=10, ttl=30)


async def check_ecs_health() -> ProviderHealthStatus:
    """Check ECS provider health status.

    Returns:
        ProviderHealthStatus: ECS provider health information
    """
    if not settings.ecs_provider_enabled:
        return ProviderHealthStatus(
            provider="ecs",
            healthy=False,
            message="Not configured"
        )

    try:
        provider = ECSVideoProvider(endpoint_url=str(settings.ecs_endpoint_url))
        is_healthy = await provider.health_check()

        if is_healthy:
            return ProviderHealthStatus(
                provider="ecs",
                healthy=True,
                message="Operational",
                endpoint=str(settings.ecs_endpoint_url)
            )
        else:
            return ProviderHealthStatus(
                provider="ecs",
                healthy=False,
                message="Endpoint unreachable",
                endpoint=str(settings.ecs_endpoint_url)
            )
    except Exception as e:
        logger.error(f"ECS health check failed: {e}")
        return ProviderHealthStatus(
            provider="ecs",
            healthy=False,
            message=f"Health check error: {str(e)}",
            endpoint=str(settings.ecs_endpoint_url) if settings.ecs_endpoint_url else None
        )


def check_replicate_health() -> ProviderHealthStatus:
    """Check Replicate provider health status.

    Replicate API is always available (cloud service with 99.9% SLA).

    Returns:
        ProviderHealthStatus: Replicate provider health information
    """
    return ProviderHealthStatus(
        provider="replicate",
        healthy=True,
        message="Always available"
    )


@router.get(
    "/api/providers/health",
    response_model=ProvidersHealthResponse,
    tags=["providers"],
    summary="Get provider health status",
    description="Returns health status for all video generation providers (Replicate and ECS)"
)
async def get_providers_health() -> ProvidersHealthResponse:
    """Get health status for all video generation providers.

    This endpoint checks the availability of both Replicate (cloud API) and ECS
    (self-hosted GPU) providers. Results are cached for 30 seconds to reduce
    load on the ECS endpoint.

    Returns:
        ProvidersHealthResponse: Health status for replicate and ecs providers

    Example Response:
        ```json
        {
          "replicate": {
            "provider": "replicate",
            "healthy": true,
            "message": "Always available"
          },
          "ecs": {
            "provider": "ecs",
            "healthy": true,
            "message": "Operational",
            "endpoint": "http://internal-adgen-ecs-alb-123.us-east-1.elb.amazonaws.com"
          }
        }
        ```
    """
    # Check cache first
    cache_key = "providers_health"
    if cache_key in health_cache:
        logger.info("Returning cached health status")
        return health_cache[cache_key]

    # Run health checks
    logger.info("Running provider health checks")
    replicate_status = check_replicate_health()
    ecs_status = await check_ecs_health()

    response = ProvidersHealthResponse(
        replicate=replicate_status,
        ecs=ecs_status
    )

    # Cache results
    health_cache[cache_key] = response
    logger.info("Health check completed, results cached")

    return response
