"""Tests for config.py — Settings validation and helper properties."""
import pytest
from pydantic import ValidationError

from config import Settings


class TestFieldValidation:
    def test_max_steps_below_min_raises(self):
        with pytest.raises(ValidationError):
            Settings(max_steps=0)

    def test_max_steps_above_max_raises(self):
        with pytest.raises(ValidationError):
            Settings(max_steps=999)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValidationError, match="LLM_PROVIDER"):
            Settings(llm_provider="unknown")

    def test_weak_internal_api_key_raises(self):
        with pytest.raises(ValidationError, match="placeholder"):
            Settings(internal_api_key="change_me")

    def test_short_internal_api_key_raises(self):
        with pytest.raises(ValidationError, match="at least 16"):
            Settings(internal_api_key="too-short")

    def test_wildcard_allowed_origin_raises(self):
        with pytest.raises(ValidationError, match="wildcards"):
            Settings(allowed_origins="*")

    def test_origin_with_path_raises(self):
        with pytest.raises(ValidationError, match="paths"):
            Settings(allowed_origins="https://example.com/app")


class TestValidateLlmReady:
    def test_missing_openai_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        s = Settings(llm_provider="openai", openai_api_key=None)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            s.validate_llm_ready()

    def test_placeholder_openai_key_raises(self):
        s = Settings(llm_provider="openai", openai_api_key="your_openai_api_key_here")
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            s.validate_llm_ready()

    def test_real_key_passes(self):
        s = Settings(llm_provider="openai", openai_api_key="sk-real")
        s.validate_llm_ready()  # no raise


class TestAllowedOriginsList:
    def test_parses_comma_separated(self):
        s = Settings(allowed_origins="http://a.com, http://b.com ,http://c.com")
        assert s.allowed_origins_list == ["http://a.com", "http://b.com", "http://c.com"]

    def test_single_origin(self):
        s = Settings(allowed_origins="http://only.com")
        assert s.allowed_origins_list == ["http://only.com"]

    def test_empty_segments_dropped(self):
        s = Settings(allowed_origins="http://a.com,, ,http://b.com")
        assert s.allowed_origins_list == ["http://a.com", "http://b.com"]
