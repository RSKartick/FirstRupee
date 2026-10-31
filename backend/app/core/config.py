"""Application configuration, loaded from environment variables and an optional backend/.env file.

Secrets (LLM_API_KEY / OPENAI_API_KEY) are only ever read from the environment and are never echoed back in responses or logs.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    # SQLite by default. Any SQLAlchemy URL (e.g. postgresql+psycopg://user:pass@host/db) is accepted.
    database_url: str = "sqlite:///./data/firstrupee.db"
    session_ttl_hours: int = 12
    # Set COOKIE_SECURE=true whenever the app is served over HTTPS.
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Optional, provider-independent LLM. "none" keeps every feature on the deterministic engines.
    llm_provider: str = "none"  # none | openai-compatible
    llm_api_key: str | None = Field(default=None, validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"))
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: float = 25.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider != "none" and bool(self.llm_api_key and self.llm_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
