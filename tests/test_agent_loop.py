import pytest, asyncio
from core.agent_loop import run_agent, run_agent_async

def mock_chat_completion(self, messages, *args, **kwargs):
    system = messages[0]["content"] if messages else ""
    if "Project Manager" in system:
        return '{"steps": [{"kind": "search", "rationale": "Find papers", "expected_output": "list"}, {"kind": "code", "rationale": "Write test", "expected_output": "results"}]}'
    elif "Critic" in system:
        return '{"strengths": "ok", "weaknesses": "none", "bias_check": "none", "confidence_score": 0.9, "recommendations": "none", "final_verdict": "good"}'
    return '{"done": true, "result": "mock result"}'

@pytest.fixture
def mock_llm(mocker):
    mocker.patch("core.llm_client.LLMClient.chat_completion", new=mock_chat_completion)

def test_run_agent(mock_llm, mocker, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    monkeypatch.setenv("RUNS_DIR", "./runs")
    mocker.patch("tools.arxiv_search.search_arxiv", return_value=[])
    mocker.patch("tools.web_search.web_search", return_value=[{"title": "Test", "content": "Text", "url": "http://test"}])
    mocker.patch("docker.from_env")
    mocker.patch("tools.code_executor.PythonExecutor.execute", return_value={"stdout": "hello", "stderr": "", "exit_code": 0, "runtime": 0.1, "artifacts": []})
    embedding_response = mocker.Mock()
    embedding_response.data = [mocker.Mock(embedding=[0.0] * 384)]
    mock_openai_client = mocker.Mock()
    mock_openai_client.embeddings.create.return_value = embedding_response
    mock_openai_class = mocker.patch("openai.OpenAI", return_value=mock_openai_client)

    result = asyncio.run(run_agent_async("Test question"))

    mock_openai_class.assert_called()
    mock_openai_client.embeddings.create.assert_called()
    assert "report_md" in result
    assert "report_pdf_path" in result
    assert "tasks" in result
    assert "usage" in result


def test_run_agent_sync_entrypoint(mocker):
    """README/UI compatibility: core.agent_loop must expose sync run_agent()."""
    mocker.patch(
        "core.agent_loop.run_agent_async",
        return_value={"report_md": "report.md", "report_pdf_path": "report.pdf", "tasks": [], "usage": {}},
    )

    result = run_agent("Tiny question")

    assert result["report_md"] == "report.md"
    assert result["report_pdf_path"] == "report.pdf"
