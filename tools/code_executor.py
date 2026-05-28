import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any

import docker
from docker.types import Ulimit

EXECUTOR_IMAGE = "autonomous-ai-researcher-executor:latest"
REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_CODE_BYTES = 200_000
MAX_EXECUTION_TIMEOUT_SECONDS = 120

class PythonExecutor:
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"[PythonExecutor] Docker unavailable: {e}") from e

        self._ensure_executor_image()

    def _ensure_executor_image(self) -> None:
        try:
            self.client.images.get(EXECUTOR_IMAGE)
        except docker.errors.ImageNotFound:
            self.client.images.build(
                path=str(REPO_ROOT),
                dockerfile="executor.Dockerfile",
                tag=EXECUTOR_IMAGE,
                rm=True,
            )

    def execute(self, code: str, timeout: int = 120, work_dir: Optional[Path] = None) -> Dict[str, Any]:
        tmpdir = tempfile.mkdtemp()
        start_time = time.time()
        try:
            code_bytes = code.encode("utf-8")
            if len(code_bytes) > MAX_CODE_BYTES:
                return {
                    "stdout": "",
                    "stderr": f"Code exceeds {MAX_CODE_BYTES} byte limit.",
                    "exit_code": -1,
                    "runtime": time.time() - start_time,
                    "artifacts": [],
                }

            timeout = max(1, min(int(timeout), MAX_EXECUTION_TIMEOUT_SECONDS))
            script_path = Path(tmpdir) / "experiment.py"
            script_path.write_bytes(code_bytes)
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            output_dir.chmod(0o777)
            container = self.client.containers.run(
                image=EXECUTOR_IMAGE,
                command=["python", "/code/experiment.py"],
                volumes={
                    tmpdir: {"bind": "/code", "mode": "ro"},
                    str(output_dir): {"bind": "/output", "mode": "rw"},
                },
                environment={"OUTPUT_DIR": "/output"},
                mem_limit="512m",
                cpu_period=100000, cpu_quota=50000,
                network_mode="none",
                user="1000:1000",
                read_only=True,
                tmpfs={
                    "/tmp": "rw,nosuid,noexec,size=64m",
                    "/home/sandbox": "rw,nosuid,noexec,size=16m",
                },
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                pids_limit=128,
                ulimits=[Ulimit(name="nofile", soft=256, hard=256)],
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
