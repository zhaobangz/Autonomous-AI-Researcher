"""Tests for tools/code_executor.py — sandbox execution and artifact collection.

These tests launch real Docker containers. They auto-skip when Docker is unavailable.
"""
import shutil

import pytest


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        import docker
        docker.from_env().ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not available",
)


@pytest.fixture(scope="module")
def executor():
    from tools.code_executor import PythonExecutor
    return PythonExecutor()


def test_simple_print_returns_zero_and_stdout(executor):
    result = executor.execute("print('hello')", timeout=60)
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]


def test_output_dir_artifact_is_collected(executor):
    code = (
        "import os\n"
        "out = os.environ.get('OUTPUT_DIR', '/output')\n"
        "with open(os.path.join(out, 'result.txt'), 'w') as f:\n"
        "    f.write('ok')\n"
    )
    result = executor.execute(code, timeout=60)
    assert result["exit_code"] == 0
    assert any(p.endswith("result.txt") for p in result["artifacts"])
