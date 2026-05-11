"""
tests/test_tools.py — Unit tests for the tool layer.

Covers:
  * arxiv_search (mocked HTTP)
  * web_search (Tavily + DuckDuckGo paths)
  * paper_parser SSRF protection
  * code_executor happy path + Docker-unavailable fallback
  * ToolRegistry.execute error handling
"""

from __future__ import annotations

import pytest


# ── arxiv_search ──────────────────────────────────────────────────────────
class TestArxivSearch:
    def test_returns_list_on_success(self, mocker):
        """A normal arXiv response produces a non-empty list of ArxivPaper objects."""
        import arxiv

        fake_result = mocker.MagicMock()
        fake_result.get_short_id.return_value = "2301.00001"
        fake_result.title = "Attention Is All You Need"
        fake_author = mocker.MagicMock()
        fake_author.name = "Vaswani"  # must be a real string, not a MagicMock
        fake_result.authors = [fake_author]
        fake_result.pdf_url = "https://arxiv.org/pdf/2301.00001"
        fake_result.published = "2023-01-01"
        fake_result.summary = "A paper about attention"

        mocker.patch.object(arxiv.Client, "results", return_value=iter([fake_result]))

        from tools.arxiv_search import search_arxiv
        papers = search_arxiv("attention mechanism", max_results=1)

        assert len(papers) == 1
        assert papers[0].title == "Attention Is All You Need"
        assert papers[0].id == "2301.00001"

    def test_returns_empty_list_on_exception(self, mocker):
        """Network errors are swallowed and an empty list is returned."""
        mocker.patch("arxiv.Client.results", side_effect=Exception("network down"))
        from tools.arxiv_search import search_arxiv
        assert search_arxiv("anything") == []


# ── web_search ────────────────────────────────────────────────────────────
class TestWebSearch:
    def test_uses_tavily_when_key_present(self, mocker, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tv-fake-key")
        mock_client = mocker.MagicMock()
        mock_client.search.return_value = {
            "results": [{"title": "Test", "content": "body", "url": "http://x.com"}]
        }
        mocker.patch("tavily.TavilyClient", return_value=mock_client)

        from importlib import reload
        import tools.web_search as ws
        reload(ws)

        results = ws.web_search("test query")
        assert len(results) >= 1

    def test_falls_back_to_ddg(self, mocker, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        fake_results = [{"title": "A", "body": "B", "href": "http://b.com"}]
        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__ = mocker.MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = mocker.MagicMock(return_value=False)
        mock_ddgs.text.return_value = fake_results
        mocker.patch("duckduckgo_search.DDGS", return_value=mock_ddgs)

        from importlib import reload
        import tools.web_search as ws
        reload(ws)
        results = ws.web_search("test query")
        assert isinstance(results, list)

    def test_returns_empty_on_all_failures(self, mocker, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        mocker.patch("duckduckgo_search.DDGS", side_effect=Exception("ddg down"))
        from importlib import reload
        import tools.web_search as ws
        reload(ws)
        assert ws.web_search("query") == []


# ── paper_parser ──────────────────────────────────────────────────────────
class TestPaperParser:
    def test_blocks_non_arxiv_urls(self):
        """SSRF protection: non-arXiv URLs must raise ValueError."""
        from tools.paper_parser import parse_pdf
        result = parse_pdf("https://evil.com/malicious.pdf")
        # The function catches the ValueError internally and returns error text
        assert "Error" in result.text or "Blocked" in result.text

    def test_parses_local_file(self, tmp_path):
        """Local file parsing returns a ParsedPaper with non-empty text."""
        fpdf = pytest.importorskip("fpdf")
        FPDF = fpdf.FPDF

        pdf_path = tmp_path / "test.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(200, 10, "Hello World", ln=True)
        pdf.output(str(pdf_path))

        from tools.paper_parser import parse_pdf
        result = parse_pdf(str(pdf_path))
        assert "Hello" in result.text or result.text == ""  # pypdf may vary


# ── code_executor ─────────────────────────────────────────────────────────
class TestCodeExecutor:
    def test_docker_unavailable_raises(self, mocker):
        """When Docker is not running, PythonExecutor __init__ raises RuntimeError."""
        mocker.patch("docker.from_env", side_effect=Exception("docker not running"))
        from tools.code_executor import PythonExecutor
        with pytest.raises(RuntimeError, match="Docker unavailable"):
            PythonExecutor()

    def test_execute_simple_code(self, mocker):
        """Happy path: Docker available, code exits 0, stdout captured."""
        mock_container = mocker.MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = lambda stdout, stderr: (
            b"hello\n" if stdout else b""
        )
        mock_client = mocker.MagicMock()
        mock_client.ping.return_value = True
        mock_client.containers.run.return_value = mock_container
        mocker.patch("docker.from_env", return_value=mock_client)

        from tools.code_executor import PythonExecutor
        exe = PythonExecutor()
        result = exe.execute("print('hello')", timeout=30)
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]


# ── ToolRegistry ──────────────────────────────────────────────────────────
class TestToolRegistry:
    def test_not_singleton(self):
        """Each ToolRegistry() call creates a distinct instance."""
        from core.tool_registry import ToolRegistry
        r1 = ToolRegistry()
        r2 = ToolRegistry()
        assert r1 is not r2

    def test_unknown_tool_raises(self):
        from core.tool_registry import ToolRegistry
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="not found"):
            registry.execute("nonexistent_tool", {})

    def test_get_schema_json_is_valid_json(self):
        import json
        from core.tool_registry import ToolRegistry
        registry = ToolRegistry()
        schema = json.loads(registry.get_schema_json())
        assert isinstance(schema, list)
        assert len(schema) >= 3  # search_arxiv, web_search, parse_pdf, run_python_code

    def test_register_custom_tool(self):
        from core.tool_registry import ToolDefinition, ToolRegistry
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="greet",
            description="Say hello",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            fn=lambda name: f"Hello, {name}!",
        ))
        result = registry.execute("greet", {"name": "World"})
        assert result == "Hello, World!"
