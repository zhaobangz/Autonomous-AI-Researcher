# tools/code_executor.py
"""
Secure Docker sandbox code executor.
"""
import tempfile
import time
import shutil
import docker
from pathlib import Path
from typing import Optional, Dict, Any

class PythonExecutor:
    """
    Executes Python code securely in a per-run Docker sandbox.
    """
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:
            import warnings
            warnings.warn(f"[PythonExecutor] Docker unavailable: {e}. Code execution will return errors.")
            self.client = None

    def execute(self, code: str, timeout: int = 120, work_dir: Optional[Path] = None) -> Dict[str, Any]:
        if self.client is None:
            return {
                "stdout": "",
                "stderr": "Docker is unavailable. Cannot execute code.",
                "exit_code": -1,
                "runtime": 0.0,
                "artifacts": []
            }
        tmpdir = tempfile.mkdtemp()
        start_time = time.time()
        try:
            script_path = Path(tmpdir) / "experiment.py"
            with open(script_path, "w") as f:
                f.write(code)
            
            try:
                container = self.client.containers.run(
                    image="python:3.11-slim",
                    command=["sh", "-c", "pip install numpy pandas matplotlib scipy --quiet && python /code/experiment.py"],
                    volumes={tmpdir: {"bind": "/code", "mode": "ro"}},
                    network_disabled=False,
                    mem_limit="512m",
                    cpu_period=100000,
                    cpu_quota=50000,
                    remove=False,
                    stdout=True,
                    stderr=True,
                    detach=True,
                )
                try:
                    exit_result = container.wait(timeout=timeout)
                    exit_code = exit_result["StatusCode"]
                    stdout_data = container.logs(stdout=True, stderr=False).decode("utf-8")
                    stderr_data = container.logs(stdout=False, stderr=True).decode("utf-8")
                except Exception as e:
                    container.kill()
                    raise
                finally:
                    container.remove(force=True)

            except docker.errors.ContainerError as e:
                stdout_data = ""
                stderr_data = e.stderr.decode("utf-8") if isinstance(e.stderr, bytes) else str(e.stderr)
                exit_code = e.exit_status
            
            runtime = time.time() - start_time
            artifacts = []
            for item in Path(tmpdir).iterdir():
                if item.name != "experiment.py" and item.is_file():
                    artifacts.append(str(item.absolute()))
                    
            return {
                "stdout": stdout_data,
                "stderr": stderr_data,
                "exit_code": exit_code,
                "runtime": runtime,
                "artifacts": artifacts
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "runtime": time.time() - start_time,
                "artifacts": []
            }
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
