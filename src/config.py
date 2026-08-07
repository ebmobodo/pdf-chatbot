"""Centralized application configuration.

All external service credentials (Supabase, NVIDIA, Google, Groq) and tunable
pipeline parameters are read from the environment here so that no secrets
or settings are hardcoded across the codebase.

Local development: copy ``.env.example`` to ``.env`` and fill in values.
Render: provide the same values as environment variables in the Render
dashboard (see DEPLOYMENT.md). Values here must never be committed to source
control.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

DEFAULT_LLM_MODEL = "gemini-2.5-flash"
DEFAULT_LLM_TEMPERATURE = 0.3
DEFAULT_FALLBACK_LLM_MODEL = "llama-3.3-70b-versatile"
DEFAULT_EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
DEFAULT_EMBED_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_OCR_DPI = 300
DEFAULT_OCR_LANGUAGE = "eng"
DEFAULT_POSTGREST_TIMEOUT = 60

_REQUIRED_ENV = (
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "GOOGLE_API_KEY",
    "NVIDIA_API_KEY",
)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        logger.warning(
            "Environment variable %s=%r is not an integer; using default %d.",
            name,
            raw,
            default,
        )
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        logger.warning(
            "Environment variable %s=%r is not a float; using default %s.",
            name,
            raw,
            default,
        )
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    supabase_url: str
    supabase_service_key: str
    google_api_key: str
    nvidia_api_key: str

    llm_model: str = DEFAULT_LLM_MODEL
    llm_temperature: float = DEFAULT_LLM_TEMPERATURE

    groq_api_key: str = ""
    fallback_llm_model: str = DEFAULT_FALLBACK_LLM_MODEL

    embed_model: str = DEFAULT_EMBED_MODEL
    embed_base_url: str = DEFAULT_EMBED_BASE_URL

    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP

    ocr_enabled: bool = False
    ocr_dpi: int = DEFAULT_OCR_DPI
    ocr_language: str = DEFAULT_OCR_LANGUAGE

    postgrest_timeout: int = DEFAULT_POSTGREST_TIMEOUT

    @classmethod
    def from_env(cls) -> Settings:
        """Build a ``Settings`` instance from the process environment."""
        settings = cls(
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            nvidia_api_key=os.getenv("NVIDIA_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL),
            llm_temperature=_get_float("LLM_TEMPERATURE", DEFAULT_LLM_TEMPERATURE),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            fallback_llm_model=os.getenv("FALLBACK_LLM_MODEL", DEFAULT_FALLBACK_LLM_MODEL),
            embed_model=os.getenv("EMBED_MODEL", DEFAULT_EMBED_MODEL),
            embed_base_url=os.getenv("EMBED_BASE_URL", DEFAULT_EMBED_BASE_URL),
            chunk_size=_get_int("CHUNK_SIZE", DEFAULT_CHUNK_SIZE),
            chunk_overlap=_get_int("CHUNK_OVERLAP", DEFAULT_CHUNK_OVERLAP),
            ocr_enabled=_get_bool("OCR_ENABLED", False),
            ocr_dpi=_get_int("OCR_DPI", DEFAULT_OCR_DPI),
            ocr_language=os.getenv("OCR_LANGUAGE", DEFAULT_OCR_LANGUAGE),
            postgrest_timeout=_get_int("POSTGREST_TIMEOUT", DEFAULT_POSTGREST_TIMEOUT),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Fail fast with a clear message when required credentials are missing."""
        missing = [name for name in _REQUIRED_ENV if not os.getenv(name)]
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Set them in a .env file (local) or as Render environment "
                "variables (production) before running the app."
            )


def get_settings() -> Settings:
    """Return validated settings for the current process."""
    return Settings.from_env()
