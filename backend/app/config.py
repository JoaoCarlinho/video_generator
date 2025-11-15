"""Configuration management for the AI Ad Video Generator backend."""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: Optional[str] = None
    
    # Redis
    redis_url: Optional[str] = None
    
    # AI APIs
    replicate_api_token: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # AWS S3
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # Supabase
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # App Config
    environment: str = "development"
    debug: bool = True
    
    # API Config
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Worker Config
    worker_processes: int = 1
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Try to load settings, with graceful fallback for development
try:
    settings = Settings()
except Exception as e:
    print(f"⚠️  Settings loading warning: {e}")
    print("⚠️  Using development defaults. Create .env file to configure services.")
    settings = Settings()

