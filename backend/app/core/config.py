"""Application configuration, loaded from environment variables and backend/.env.

Secrets (GEMINI_API_KEY / GOOGLE_API_KEY / LLM_API_KEY / OPENAI_API_KEY) are only ever read from the environment
or backend/.env and are never echoed back in responses or logs.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent
_ENV_FILES = (str(_REPO_ROOT / ".env"), str(_BACKEND_DIR / ".env"))
_PLACEHOLDERS = {
    "",
    "your_api_key_here",
    "paste_your_google_studio_api_key_here",
    "paste-your-google-studio-api-key-here",
}


def _clean_key(raw: str | None) -> str | None:
    if not raw:
        return None
    val = raw.strip().strip('"').strip("'")
    if not val or val.lower() in _PLACEHOLDERS:
        return None
    return val


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    # SQLite by default. Any SQLAlchemy URL (e.g. postgresql+psycopg://user:pass@host/db) is accepted.
    database_url: str = "sqlite:///./data/firstrupee.db"
    session_ttl_hours: int = 12
    # Set COOKIE_SECURE=true whenever the app is served over HTTPS.
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Google AI Studio (Gemini) or OpenAI-compatible LLM configuration.
    llm_provider: str = "gemini"  # gemini | openai-compatible | none
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    llm_model: str = "gemini-3.5-flash-lite"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    llm_timeout_seconds: float = 25.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_api_key(self) -> str | None:
        return _clean_key(self.gemini_api_key) or _clean_key(self.llm_api_key)

    @property
    def effective_provider(self) -> str:
        key = self.effective_api_key
        if not key:
            return "none"
        prov = (self.llm_provider or "").strip().lower()
        if prov == "none":
            return "none"
        if _clean_key(self.gemini_api_key) or key.startswith("AIza") or prov in ("gemini", "google", "google-gemini", "google-studio"):
            return "google-gemini"
        return prov or "openai-compatible"

    @property
    def llm_enabled(self) -> bool:
        return self.effective_provider != "none" and bool(self.effective_api_key)


_cached_settings: Settings | None = None
_cached_mtimes: tuple[float, float] = (-1.0, -1.0)


def _env_mtimes() -> tuple[float, float]:
    mtimes: list[float] = []
    for p in _ENV_FILES:
        try:
            mtimes.append(Path(p).stat().st_mtime)
        except OSError:
            mtimes.append(0.0)
    return (mtimes[0], mtimes[1])


def get_settings() -> Settings:
    global _cached_settings, _cached_mtimes
    current_mtimes = _env_mtimes()
    if _cached_settings is None or current_mtimes != _cached_mtimes:
        _cached_settings = Settings()
        _cached_mtimes = current_mtimes
    return _cached_settings
