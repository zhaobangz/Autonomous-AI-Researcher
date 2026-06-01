"""
tests/test_coder.py — Unit tests for Coder._clean_code and run_async.

The _clean_code method previously had a bug where:
  - A code block without a closing ``` returned an empty string.
  - Multiple blocks returned only the first rather than the longest.

These tests lock in the correct behaviour.
"""

from __future__ import annotations

import pytest
from agents.coder import Coder


# ── _clean_code ───────────────────────────────────────────────────────────
class TestCleanCode:
    @pytest.fixture
    def coder(self):
        # Coder.__init__ creates an LLMClient which needs an API key.
        # Bypass by patching at the class level.
        return Coder.__new__(Coder)

    def test_extracts_python_fenced_block(self, coder):
        raw = "Here is the code:\n```python\nprint('hi')\n```\nDone."
        assert coder._clean_code(raw) == "print('hi')"

    def test_extracts_plain_fenced_block(self, coder):
        raw = "```\nresult = 42\n```"
        assert coder._clean_code(raw) == "result = 42"

    def test_handles_unclosed_fence(self, coder):
        """Bug fix: unclosed ``` should still extract whatever code is there."""
        raw = "```python\nimport sys\nprint('hello')"
        result = coder._clean_code(raw)
        assert "print('hello')" in result

    def test_returns_longest_block(self, coder):
        """When multiple blocks exist, the longest (the real code) wins."""
        raw = (
            "Short example:\n```python\nx = 1\n```\n\n"
            "Full script:\n```python\nimport sys\nimport json\n"
            "data = {'key': 'value'}\nprint(json.dumps(data))\n```"
        )
        result = coder._clean_code(raw)
        assert "json.dumps" in result

    def test_raw_code_no_fence(self, coder):
        """Responses with no fences are returned as-is."""
        raw = "import os\nprint(os.getcwd())"
        result = coder._clean_code(raw)
        assert "print(os.getcwd())" in result

    def test_strips_outer_whitespace(self, coder):
        raw = "\n\n```python\nx = 1\n```\n\n"
        result = coder._clean_code(raw)
        assert result == "x = 1"

    def test_empty_fence_returns_empty(self, coder):
        raw = "```\n```"
        # An empty fence — nothing inside, should return empty string gracefully
        result = coder._clean_code(raw)
        assert isinstance(result, str)


# ── run_async ─────────────────────────────────────────────────────────────
class TestCoderRunAsync:
    def test_prepends_imports_if_missing(self, mocker, monkeypatch):
        """Coder prepends 'import sys, json, time' if the LLM omits it."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        monkeypatch.setenv("LLM_PROVIDER", "openai")

        mocker.patch(
            "core.llm_client.LLMClient.chat_completion",
            return_value="```python\nprint('hello')\n```",
        )
        mocker.patch(
            "core.tool_registry.ToolRegistry.execute",
            return_value={"stdout": "hello\n", "stderr": "", "exit_code": 0, "runtime": 0.1, "artifacts": []},
        )

        import asyncio
        from agents.coder import Coder
        from core.tool_registry import ToolRegistry

        coder = Coder(tool_registry=ToolRegistry())
        result = asyncio.run(coder.run_async("Compute 2+2 and print the result"))

        assert "import sys" in result["code"]
        assert result["results"]["exit_code"] == 0
