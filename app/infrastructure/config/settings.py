from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEV_JWT_SECRET = "development-intentlock-secret-key-2026-abcdef"  # noqa: S105


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "IntentLock"
    app_env: str = Field(default="development", pattern=r"^(development|staging|production|test)$")
    debug: bool = False
    api_host: str = "0.0.0.0"  # noqa: S104
    api_port: int = 8000

    database_url: str = "sqlite:///./intentlock.db"

    jwt_secret_key: str = Field(default=DEFAULT_DEV_JWT_SECRET, min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    jwt_clock_skew_seconds: int = Field(default=30, ge=0, le=300)

    execution_key_path: str | None = None
    execution_token_ttl_seconds: int = Field(default=1, ge=1, le=60)

    bcrypt_rounds: int = Field(default=12, ge=10, le=15)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    redis_url: str | None = None
    redis_enabled: bool = True

    rate_limit_login_per_minute: int = Field(default=5, ge=1)
    rate_limit_register_per_minute: int = Field(default=5, ge=1)
    rate_limit_intent_per_minute: int = Field(default=60, ge=1)

    hitl_ttl_seconds: int = Field(default=300, ge=30, le=3600)

    velocity_window_seconds: int = Field(default=60, ge=10, le=3600)
    velocity_max_requests: int = Field(default=100, ge=1)
    velocity_max_cumulative_value: float = Field(default=10_000.0, ge=0.0)
    velocity_max_cumulative_risk: float = Field(default=5.0, ge=0.0)
    velocity_max_sensitive_operations: int = Field(default=10, ge=1)

    webhook_hmac_secret: str | None = None
    webhook_timeout_seconds: int = Field(default=10, ge=1, le=60)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(origin) for origin in value]
        return []

    @field_validator("jwt_secret_key")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        if value.startswith("change-me"):
            msg = "JWT_SECRET_KEY must be replaced with a cryptographically secure value."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def enforce_production_secret(self) -> "Settings":
        if self.app_env != "development" and self.jwt_secret_key == DEFAULT_DEV_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET_KEY must be configured explicitly for non-development environments."
            )
        if self.app_env == "production" and not self.redis_url:
            raise ValueError(
                "REDIS_URL must be configured for production environments."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
