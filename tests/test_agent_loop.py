# tests/test_agent_loop.py
import pytest
import asyncio
from core.agent_loop import run_agent_async

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
    monkeypatch.setenv("RUNS_DIR", "./runs")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    mocker.patch("tools.arxiv_search.search_arxiv", return_value=[])
    mocker.patch("tools.web_search.web_search", return_value=[{"title": "Test", "content": "Text", "url": "http://test"}])
    mocker.patch("tools.code_executor.PythonExecutor.execute", return_value={"stdout": "hello", "stderr": "", "exit_code": 0, "runtime": 0.1, "artifacts": []})
    mocker.patch("memory.embeddings.embed", return_value=None)
    
    result = asyncio.run(run_agent_async("Test question"))
    assert "report_md" in result
    assert "report_pdf_path" in result
    assert "tasks" in result
    assert "usage" in result
