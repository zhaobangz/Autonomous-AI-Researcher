import tempfile, time, shutil, docker
from pathlib import Path
from typing import Optional, Dict, Any

class PythonExecutor:
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"[PythonExecutor] Docker unavailable: {e}") from e

    def execute(self, code: str, timeout: int = 120, work_dir: Optional[Path] = None) -> Dict[str, Any]:
        tmpdir = tempfile.mkdtemp()
        start_time = time.time()
        try:
            script_path = Path(tmpdir) / "experiment.py"
            script_path.write_text(code)
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            container = self.client.containers.run(
                image="python:3.11-slim",
                command=["sh", "-c", "pip install numpy pandas matplotlib scipy --quiet && python /code/experiment.py"],
                volumes={
                    tmpdir: {"bind": "/code", "mode": "ro"},
                    str(output_dir): {"bind": "/output", "mode": "rw"},
                },
                environment={"OUTPUT_DIR": "/output"},
                mem_limit="512m",
                cpu_period=100000, cpu_quota=50000,
                network_mode="none",
                remove=False, stdout=True, stderr=True, detach=True
            )
            try:
                result = container.wait(timeout=timeout)
                exit_code = result["StatusCode"]
                stdout_data = container.logs(stdout=True, stderr=False).decode("utf-8")
                stderr_data = container.logs(stdout=False, stderr=True).decode("utf-8")
            except Exception:
                container.kill()
                raise
            finally:
                container.remove(force=True)
            return {"stdout": stdout_data, "stderr": stderr_data, "exit_code": exit_code, "runtime": time.time()-start_time, "artifacts": [str(p) for p in output_dir.iterdir() if p.is_file()]}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "exit_code": -1, "runtime": time.time()-start_time, "artifacts": []}
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
