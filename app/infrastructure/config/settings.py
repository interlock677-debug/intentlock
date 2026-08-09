from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DEV_JWT_SECRET = "development-intentlock-secret-key-2026-abcdef"


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
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "sqlite:///./intentlock.db"

    jwt_secret_key: str = Field(default=DEFAULT_DEV_JWT_SECRET, min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)

    bcrypt_rounds: int = Field(default=12, ge=10, le=15)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

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
    @classmethod
    def enforce_production_secret(cls, values: "Settings") -> "Settings":
        if values.app_env != "development" and values.jwt_secret_key == DEFAULT_DEV_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET_KEY must be configured explicitly for non-development environments."
            )
        return values
@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
