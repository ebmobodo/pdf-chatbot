"""Tests for src.config.Settings."""

import pytest
from src.config import Settings


class TestSettings:
    def test_defaults_when_only_required_set(self, monkeypatch):
        for key in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GOOGLE_API_KEY", "NVIDIA_API_KEY"]:
            monkeypatch.setenv(key, "value")

        settings = Settings.from_env()

        assert settings.supabase_url == "value"
        assert settings.llm_model == "gemini-2.5-flash"
        assert settings.llm_temperature == 0.3
        assert settings.groq_api_key == ""
        assert settings.fallback_llm_model == "llama-3.3-70b-versatile"
        assert settings.embed_model == "nvidia/nemotron-3-embed-1b"
        assert settings.embed_base_url == "https://integrate.api.nvidia.com/v1"
        assert settings.chunk_size == 1000
        assert settings.chunk_overlap == 200
        assert settings.ocr_enabled is False
        assert settings.ocr_dpi == 300
        assert settings.ocr_language == "eng"
        assert settings.postgrest_timeout == 60

    def test_env_overrides(self, monkeypatch):
        for key in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GOOGLE_API_KEY", "NVIDIA_API_KEY"]:
            monkeypatch.setenv(key, "value")
        monkeypatch.setenv("LLM_MODEL", "gemini-2.0-flash")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        monkeypatch.setenv("FALLBACK_LLM_MODEL", "llama-3.1-8b-instant")
        monkeypatch.setenv("EMBED_MODEL", "custom-model")
        monkeypatch.setenv("CHUNK_SIZE", "512")
        monkeypatch.setenv("CHUNK_OVERLAP", "64")
        monkeypatch.setenv("OCR_ENABLED", "true")
        monkeypatch.setenv("OCR_DPI", "150")
        monkeypatch.setenv("OCR_LANGUAGE", "deu")
        monkeypatch.setenv("POSTGREST_TIMEOUT", "120")

        settings = Settings.from_env()

        assert settings.llm_model == "gemini-2.0-flash"
        assert settings.llm_temperature == 0.7
        assert settings.groq_api_key == "test-groq-key"
        assert settings.fallback_llm_model == "llama-3.1-8b-instant"
        assert settings.embed_model == "custom-model"
        assert settings.chunk_size == 512
        assert settings.chunk_overlap == 64
        assert settings.ocr_enabled is True
        assert settings.ocr_dpi == 150
        assert settings.ocr_language == "deu"
        assert settings.postgrest_timeout == 120

    def test_missing_required_raises(self, monkeypatch):
        for key in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GOOGLE_API_KEY", "NVIDIA_API_KEY"]:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(RuntimeError, match="SUPABASE_URL"):
            Settings.from_env()

    def test_invalid_int_falls_back_to_default(self, monkeypatch):
        for key in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GOOGLE_API_KEY", "NVIDIA_API_KEY"]:
            monkeypatch.setenv(key, "value")
        monkeypatch.setenv("CHUNK_SIZE", "not-a-number")

        settings = Settings.from_env()

        assert settings.chunk_size == 1000

    def test_get_settings_returns_validated_settings(self, monkeypatch):
        for key in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GOOGLE_API_KEY", "NVIDIA_API_KEY"]:
            monkeypatch.setenv(key, "value")

        from src.config import get_settings

        assert get_settings().supabase_url == "value"
