# src/config/settings.py
"""Centralized configuration using pydantic-settings."""

import secrets
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──
    APP_NAME: str = "Al-Ilm"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # ── Server ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # ── Database (MongoDB) ──
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "islamic_rag"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379"

    # ── Auth ──
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── LLM ──
    LLM_PROVIDER: str = "groq"  # ollama, openai, groq, anthropic
    LLM_MODEL: str = "llama-3.1-8b-instant"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    ANTHROPIC_API_KEY: str = ""

    # ── Vector Store ──
    VECTOR_STORE_PATH: str = "data/vectorstore"

    # ── Rate Limiting ──
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_RPM: int = 60  # requests per minute

    # ── API Keys (lightweight gate for the public main.py endpoints) ──
    # PUBLIC_API_KEY: if set, /api/ask and /ws/ask require it via X-API-Key.
    # ADMIN_API_KEY: required for /api/index-document; endpoint is disabled if unset.
    PUBLIC_API_KEY: str = ""
    ADMIN_API_KEY: str = ""

    # ── Billing ──
    BILLING_ENABLED: bool = False

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


def _validate_settings(settings: Settings) -> None:
    """Validate critical settings at startup."""
    if not settings.JWT_SECRET:
        if settings.is_production:
            raise RuntimeError(
                "JWT_SECRET must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        # In dev, auto-generate an ephemeral secret (session only)
        settings.JWT_SECRET = secrets.token_hex(32)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    settings = Settings()
    _validate_settings(settings)
    return settings
