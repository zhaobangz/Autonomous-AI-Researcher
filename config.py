"""
config.py — Centralized, validated application configuration.

All settings are loaded from environment variables (or a .env file) once at
import time.  Every other module imports `settings` from here instead of
calling os.getenv() directly, giving us:

  - A single source of truth for all tunable values
  - Type validation and sensible defaults via Pydantic Settings
  - An easy place to add future settings without scattering os.getenv calls
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_KNOWN_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
}


class Settings(BaseSettings):
    """Application-wide settings, read from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM provider ───────────────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        description="Which LLM provider to use.",
    )
    llm_model: str = Field(
        default="gpt-4o",
        description="Model identifier for the chosen provider.",
    )

    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key.")
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key."
    )

    # ── Optional tool keys ─────────────────────────────────────────────────
    tavily_api_key: Optional[str] = Field(
        default=None, description="Tavily web-search key (optional)."
    )
    pinecone_api_key: Optional[str] = Field(
        default=None, description="Pinecone key (optional, falls back to ChromaDB)."
    )
    pinecone_index: str = Field(default="research-context")

    # ── Memory / storage ───────────────────────────────────────────────────
    vector_backend: Literal["chroma", "pinecone"] = Field(
        default="chroma",
        description="Vector store backend.",
    )
    runs_dir: Path = Field(
        default=Path("./runs"),
        description="Directory where run artefacts are stored.",
    )

    # ── Agent loop ────────────────────────────────────────────────────────
    max_steps: int = Field(
        default=12,
        ge=1,
        le=50,
        description="Maximum number of agent steps per run.",
    )
    run_timeout_seconds: int = Field(
        default=600,
        ge=60,
        description="Hard timeout (seconds) for a single research run.",
    )
    max_reroutes: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Max self-correction reroutes per run when critic confidence is low.",
    )

    # ── API server ────────────────────────────────────────────────────────
    internal_api_key: Optional[str] = Field(
        default=None,
        description="If set, all POST/GET research endpoints require X-API-Key header.",
    )
    allowed_origins: str = Field(
        default="http://localhost:8501",
        description="Comma-separated CORS allowed origins for the API server.",
    )
    # How long (seconds) to keep a completed/failed run queue before cleanup
    queue_ttl_seconds: int = Field(default=300, ge=30)

    # ── Rate limiting ─────────────────────────────────────────────────────
    rate_limit_per_minute: int = Field(
        default=10,
        ge=1,
        description="Max research-run starts per IP per minute.",
    )

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_json: bool = Field(
        default=False,
        description="Emit structured JSON logs (useful in production/Docker).",
    )

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for the run manager.",
    )

    # ── UI ───────────────────────────────────────────────────────────────
    api_base_url: str = Field(
        default="http://localhost:8000",
        description="API base URL for the Streamlit UI.",
    )

    # ── Validators ────────────────────────────────────────────────────────
    @field_validator("runs_dir", mode="before")
    @classmethod
    def _resolve_runs_dir(cls, v: str | Path) -> Path:
        return Path(v).resolve()

    @field_validator("llm_model")
    @classmethod
    def _warn_unknown_model(cls, v: str) -> str:
        if v not in _KNOWN_MODELS:
            import warnings
            warnings.warn(
                f"LLM_MODEL='{v}' is not in the known-good model list. Double-check spelling.",
                stacklevel=2,
            )
        return v

    # ── Helpers ───────────────────────────────────────────────────────────
    @property
    def active_llm_api_key(self) -> Optional[str]:
        """Return the key for the selected provider, if configured."""
        return self.openai_api_key if self.llm_provider == "openai" else self.anthropic_api_key

    def validate_llm_ready(self) -> None:
        """Raise a clear error only when an actual LLM call is about to run."""
        key_name = "OPENAI_API_KEY" if self.llm_provider == "openai" else "ANTHROPIC_API_KEY"
        key = self.active_llm_api_key
        if not key or key.startswith("your_"):
            raise RuntimeError(
                f"{key_name} is not configured. Copy .env.example to .env and set a real key."
            )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def run_dir(self, run_id: str) -> Path:
        """Return (and create) the artefact directory for a specific run."""
        path = self.runs_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere instead of os.getenv()
# ---------------------------------------------------------------------------
from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    return Settings()
