"""
tests/test_llm_client.py — Unit tests for the unified LLMClient interface.

Covers:
  * Provider validation
  * API key resolution and placeholder rejection
  * Cost / usage accounting (known + unknown models)
  * chat_completion success paths for OpenAI, Anthropic, and OpenRouter
  * structured_output parsing, fenced-block stripping, and retry on bad JSON
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from core.llm_client import LLMClient


# ── Initialization ───────────────────────────────────────────────────────
class TestInit:
    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "bogus")
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMClient()

    def test_default_provider_is_openrouter(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        client = LLMClient()
        assert client.provider == "openrouter"
        assert client.model == "openai/gpt-4o-mini"

    def test_initial_usage_is_zero(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        client = LLMClient()
        assert client.usage == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_estimate": 0.0,
        }


# ── API key resolution ──────────────────────────────────────────────────
class TestApiKey:
    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = LLMClient()
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
            client._get_api_key()

    def test_placeholder_key_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "your_key_here")
        client = LLMClient()
        with pytest.raises(EnvironmentError):
            client._get_api_key()

    def test_openrouter_key_in_openai_slot_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-or-v1-test")
        client = LLMClient()
        with pytest.raises(EnvironmentError, match="OpenRouter key"):
            client._get_api_key()

    def test_anthropic_uses_anthropic_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        client = LLMClient()
        assert client._get_api_key() == "test-anthropic-key"

    def test_openrouter_uses_openrouter_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
        client = LLMClient()
        assert client._get_api_key() == "test-openrouter-key"


# ── Cost accounting ─────────────────────────────────────────────────────
class TestUsageAccounting:
    def test_known_model_uses_table_pricing(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_MODEL", "gpt-4o")
        client = LLMClient()
        client._update_usage(prompt_tokens=1000, completion_tokens=500)
        assert client.usage["prompt_tokens"] == 1000
        assert client.usage["completion_tokens"] == 500
        # gpt-4o: 0.005 / 0.015 per 1k tokens
        expected = (1000 * 0.005 / 1000) + (500 * 0.015 / 1000)
        assert client.usage["cost_estimate"] == pytest.approx(expected)

    def test_unknown_model_falls_back_to_default_rates(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_MODEL", "totally-made-up-model")
        client = LLMClient()
        client._update_usage(prompt_tokens=100, completion_tokens=200)
        # Default fallback rates are [0.01, 0.03]
        expected = (100 * 0.01 / 1000) + (200 * 0.03 / 1000)
        assert client.usage["cost_estimate"] == pytest.approx(expected)

    def test_usage_accumulates_across_calls(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_MODEL", "gpt-4o")
        client = LLMClient()
        client._update_usage(100, 50)
        client._update_usage(200, 80)
        assert client.usage["prompt_tokens"] == 300
        assert client.usage["completion_tokens"] == 130


# ── chat_completion ─────────────────────────────────────────────────────
class TestChatCompletion:
    def test_openai_success_path(self, mocker, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_MODEL", "gpt-4o")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

        fake_response = mocker.MagicMock()
        fake_response.choices[0].message.content = "hello world"
        fake_response.usage.prompt_tokens = 10
        fake_response.usage.completion_tokens = 4

        fake_client = mocker.MagicMock()
        fake_client.chat.completions.create.return_value = fake_response
        mocker.patch("openai.OpenAI", return_value=fake_client)

        client = LLMClient()
        out = client.chat_completion([{"role": "user", "content": "hi"}])

        assert out == "hello world"
        assert client.usage["prompt_tokens"] == 10
        assert client.usage["completion_tokens"] == 4

    def test_anthropic_success_path(self, mocker, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("LLM_MODEL", "claude-sonnet-4-6")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")

        fake_response = mocker.MagicMock()
        fake_response.content = [mocker.MagicMock(type="text", text="claude says hi")]
        fake_response.usage.input_tokens = 7
        fake_response.usage.output_tokens = 3

        fake_client = mocker.MagicMock()
        fake_client.messages.create.return_value = fake_response
        mocker.patch("anthropic.Anthropic", return_value=fake_client)

        client = LLMClient()
        out = client.chat_completion(
            [
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "hi"},
            ]
        )

        assert out == "claude says hi"
        assert client.usage["prompt_tokens"] == 7
        # System message must be split out from messages array
        called_kwargs = fake_client.messages.create.call_args.kwargs
        assert called_kwargs["system"] == "be brief"
        assert all(m["role"] != "system" for m in called_kwargs["messages"])

    def test_anthropic_skips_leading_thinking_block(self, mocker, monkeypatch):
        """Models with adaptive thinking emit a thinking block before the answer.

        Its .text is None, so reading content[0] returned None and blew up two
        layers later in structured_output().strip().
        """
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("LLM_MODEL", "claude-sonnet-5")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")

        fake_response = mocker.MagicMock()
        fake_response.content = [
            mocker.MagicMock(type="thinking", text=None, thinking=""),
            mocker.MagicMock(type="text", text='{"ok": true}'),
        ]
        fake_response.usage.input_tokens = 7
        fake_response.usage.output_tokens = 3

        fake_client = mocker.MagicMock()
        fake_client.messages.create.return_value = fake_response
        mocker.patch("anthropic.Anthropic", return_value=fake_client)

        out = LLMClient().chat_completion([{"role": "user", "content": "hi"}])

        assert out == '{"ok": true}'

    def test_anthropic_no_text_block_raises_clear_error(self, mocker, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("LLM_MODEL", "claude-sonnet-5")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")

        fake_response = mocker.MagicMock()
        fake_response.content = []
        fake_response.stop_reason = "refusal"
        fake_response.usage.input_tokens = 7
        fake_response.usage.output_tokens = 0

        fake_client = mocker.MagicMock()
        fake_client.messages.create.return_value = fake_response
        mocker.patch("anthropic.Anthropic", return_value=fake_client)

        with pytest.raises(RuntimeError, match="no text block"):
            LLMClient().chat_completion([{"role": "user", "content": "hi"}])

    def test_anthropic_omits_temperature_on_models_that_reject_it(self, mocker, monkeypatch):
        """Claude Opus 4.7+ removed the sampling params; sending them 400s."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")

        from config import get_settings

        for model, expect_temperature in (
            ("claude-sonnet-5", False),
            ("claude-sonnet-4-6", True),
        ):
            monkeypatch.setenv("LLM_PROVIDER", "anthropic")
            monkeypatch.setenv("LLM_MODEL", model)
            get_settings.cache_clear()  # settings are cached per process

            fake_response = mocker.MagicMock()
            fake_response.content = [mocker.MagicMock(type="text", text="ok")]
            fake_response.usage.input_tokens = 1
            fake_response.usage.output_tokens = 1

            fake_client = mocker.MagicMock()
            fake_client.messages.create.return_value = fake_response
            mocker.patch("anthropic.Anthropic", return_value=fake_client)

            LLMClient().chat_completion([{"role": "user", "content": "hi"}])

            sent = fake_client.messages.create.call_args.kwargs
            assert sent["model"] == model
            assert ("temperature" in sent) is expect_temperature, model

    def test_openrouter_success_path(self, mocker, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("LLM_MODEL", "openai/gpt-4o-mini")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
        monkeypatch.setenv("OPENROUTER_SITE_URL", "https://example.com")
        monkeypatch.setenv("OPENROUTER_APP_NAME", "Test App")

        fake_response = mocker.MagicMock()
        fake_response.choices[0].message.content = "router says hi"
        fake_response.usage.prompt_tokens = 8
        fake_response.usage.completion_tokens = 5

        fake_client = mocker.MagicMock()
        fake_client.chat.completions.create.return_value = fake_response
        openai_class = mocker.patch("openai.OpenAI", return_value=fake_client)

        client = LLMClient()
        out = client.chat_completion([{"role": "user", "content": "hi"}])

        assert out == "router says hi"
        assert client.usage["prompt_tokens"] == 8
        assert client.usage["completion_tokens"] == 5
        called_kwargs = openai_class.call_args.kwargs
        assert called_kwargs["api_key"] == "test-openrouter-key"
        assert str(called_kwargs["base_url"]) == "https://openrouter.ai/api/v1"
        assert called_kwargs["default_headers"] == {
            "HTTP-Referer": "https://example.com",
            "X-OpenRouter-Title": "Test App",
        }


# ── structured_output ───────────────────────────────────────────────────
class _Greeting(BaseModel):
    greeting: str
    target: str


class TestStructuredOutput:
    def test_parses_raw_json(self, mocker, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        mocker.patch.object(
            LLMClient,
            "chat_completion",
            return_value='{"greeting": "hi", "target": "world"}',
        )
        client = LLMClient()
        result = client.structured_output(
            [{"role": "user", "content": "make a greeting"}], schema=_Greeting
        )
        assert result.greeting == "hi"
        assert result.target == "world"

    def test_strips_markdown_fences(self, mocker, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        fenced = '```json\n{"greeting": "hello", "target": "you"}\n```'
        mocker.patch.object(LLMClient, "chat_completion", return_value=fenced)
        client = LLMClient()
        result = client.structured_output(
            [{"role": "user", "content": "x"}], schema=_Greeting
        )
        assert result.target == "you"

    def test_retries_once_on_invalid_json(self, mocker, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        responses = iter(
            [
                "not even close to json",
                '{"greeting": "hi", "target": "again"}',
            ]
        )
        mocker.patch.object(
            LLMClient, "chat_completion", side_effect=lambda *a, **k: next(responses)
        )
        client = LLMClient()
        result = client.structured_output(
            [{"role": "user", "content": "x"}], schema=_Greeting
        )
        assert result.target == "again"

    def test_raises_after_two_failed_attempts(self, mocker, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        mocker.patch.object(
            LLMClient, "chat_completion", return_value="never valid json"
        )
        client = LLMClient()
        with pytest.raises(Exception, match="Failed structured output validation"):
            client.structured_output(
                [{"role": "user", "content": "x"}], schema=_Greeting
            )
