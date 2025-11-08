"""
Application configuration management using Pydantic Settings.
Provides type-safe configuration with validation and environment variable support.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and type hints."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_name: str = "ComplianceGuard AI"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # API Settings
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = Field(default=["*"])
    cors_allow_headers: List[str] = Field(default=["*"])

    # Security Settings
    secret_key: str = Field(default="dev-secret-key-change-this-in-production-min-32-chars")
    access_token_expire_minutes: int = Field(default=60 * 24 * 8)  # 8 days

    # Database Configuration
    database_url: PostgresDsn = Field(
        default="postgresql://complianceguard:secure_password@localhost:5432/complianceguard"
    )
    database_pool_size: int = Field(default=20, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    database_pool_timeout: int = Field(default=30, ge=1)
    database_echo: bool = Field(default=False)

    # Redis Configuration
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = Field(default=50)
    redis_decode_responses: bool = Field(default=True)

    # Celery Configuration
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    celery_task_always_eager: bool = Field(default=False)  # For testing
    celery_task_eager_propagates: bool = Field(default=True)
    celery_worker_concurrency: int = Field(default=4, ge=1)
    celery_worker_prefetch_multiplier: int = Field(default=4, ge=1)

    # S3 Configuration
    s3_bucket_name: str = Field(default="complianceguard-documents")
    s3_region: str = Field(default="us-east-1")
    s3_access_key_id: Optional[str] = Field(default=None)
    s3_secret_access_key: Optional[str] = Field(default=None)
    s3_endpoint_url: Optional[str] = Field(default=None)  # For LocalStack/MinIO compatibility
    s3_use_ssl: bool = Field(default=True)

    # Landing AI Configuration
    landing_ai_api_key: Optional[str] = Field(default=None)
    landing_ai_base_url: str = Field(default="https://api.landing.ai/v1")
    landing_ai_timeout_seconds: int = Field(default=60, ge=1, le=300)
    landing_ai_max_retries: int = Field(default=3, ge=0, le=10)

    # AWS Bedrock Configuration
    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")
    aws_bedrock_max_tokens: int = Field(default=8000, ge=100, le=100000)
    aws_bedrock_temperature: float = Field(default=0.1, ge=0.0, le=1.0)

    # File Processing Settings
    max_file_size_mb: int = Field(default=50, ge=1, le=500)
    allowed_file_extensions: List[str] = Field(default=[".pdf", ".docx"])
    extraction_timeout_seconds: int = Field(default=120, ge=10, le=600)

    # Compliance Settings
    compliance_frameworks: List[str] = Field(default=["SEC_CYBER"])
    violation_severity_levels: List[str] = Field(default=["critical", "high", "medium", "low"])
    max_parallel_document_comparisons: int = Field(default=10, ge=1, le=50)

    # Monitoring & Observability
    sentry_dsn: Optional[str] = Field(default=None)
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=9090, ge=1024, le=65535)
    enable_tracing: bool = Field(default=False)
    jaeger_agent_host: str = Field(default="localhost")
    jaeger_agent_port: int = Field(default=6831)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info: Any) -> str:
        """Ensure secret key is set in production."""
        if info.data.get("environment") == "production" and not v:
            raise ValueError("SECRET_KEY must be set in production environment")
        return v or "development-secret-key-change-in-production"

    @model_validator(mode="after")
    def set_celery_urls(self):
        """Set Celery URLs from Redis URL if not explicitly provided."""
        if not self.celery_broker_url:
            self.celery_broker_url = str(self.redis_url)
        if not self.celery_result_backend:
            self.celery_result_backend = str(self.redis_url)
        return self

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: PostgresDsn) -> PostgresDsn:
        """Ensure database URL is properly formatted."""
        return v

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def get_database_url_with_driver(self) -> str:
        """Get database URL with asyncpg driver for async operations."""
        url = str(self.database_url)
        return url.replace("postgresql://", "postgresql+asyncpg://")

    def get_sync_database_url(self) -> str:
        """Get database URL with psycopg2 driver for sync operations."""
        url = str(self.database_url)
        return url.replace("postgresql://", "postgresql+psycopg2://")

    def to_dict(self, exclude_sensitive: bool = True) -> Dict[str, Any]:
        """
        Convert settings to dictionary, optionally excluding sensitive values.

        Args:
            exclude_sensitive: If True, exclude sensitive configuration values.

        Returns:
            Dictionary of settings.
        """
        data = self.model_dump()

        if exclude_sensitive:
            sensitive_fields = [
                "secret_key",
                "database_url",
                "redis_url",
                "s3_access_key_id",
                "s3_secret_access_key",
                "landing_ai_api_key",
                "aws_access_key_id",
                "aws_secret_access_key",
                "sentry_dsn",
            ]
            for field in sensitive_fields:
                if field in data:
                    data[field] = "***REDACTED***"

        return data


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance (cached).
    """
    return Settings()


# Create a global settings instance
settings = get_settings()

# Export commonly used settings
DEBUG = settings.debug
ENVIRONMENT = settings.environment
DATABASE_URL = settings.database_url
REDIS_URL = settings.redis_url