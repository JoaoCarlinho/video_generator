"""Configuration management for the AI Ad Video Generator backend."""

from pydantic_settings import BaseSettings
from pydantic import field_validator, HttpUrl
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: Optional[str] = None

    # Job Queue (SQS - replaces Redis)
    sqs_queue_url: Optional[str] = None
    sqs_dlq_url: Optional[str] = None

    # AI APIs
    replicate_api_token: Optional[str] = None
    openai_api_key: Optional[str] = None

    # ECS Provider Configuration
    ecs_endpoint_url: Optional[HttpUrl] = None

    # AWS S3
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    aws_region: str = "us-east-1"

    # JWT Authentication
    jwt_secret: str = "your-secret-key-change-in-production"

    # App Config
    environment: str = "development"
    debug: bool = True
    
    # API Config
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: Optional[str] = None

    # Worker Config
    worker_processes: int = 1

    @property
    def ecs_provider_enabled(self) -> bool:
        """Check if ECS provider is enabled via endpoint configuration.

        Returns:
            bool: True if ECS_ENDPOINT_URL is set and non-empty, False otherwise
        """
        return self.ecs_endpoint_url is not None and str(self.ecs_endpoint_url).strip() != ""

    @field_validator('ecs_endpoint_url')
    @classmethod
    def validate_ecs_endpoint(cls, v):
        """Validate ECS endpoint URL format.

        Args:
            v: ECS endpoint URL value

        Returns:
            HttpUrl: Validated URL

        Raises:
            ValueError: If URL format is invalid
        """
        if v is not None:
            url_str = str(v)
            if not url_str.startswith(('http://', 'https://')):
                raise ValueError("ECS_ENDPOINT_URL must start with http:// or https://")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


# Try to load settings, with graceful fallback for development
try:
    settings = Settings()
except Exception as e:
    print(f"⚠️  Settings loading warning: {e}")
    print("⚠️  Using development defaults. Create .env file to configure services.")
    settings = Settings()

# Log ECS provider configuration on startup
if settings.ecs_provider_enabled:
    logger.info(f"ECS provider enabled: {settings.ecs_endpoint_url}")
else:
    logger.info("ECS provider disabled")

