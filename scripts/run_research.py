from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "runs" / "auto"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass(frozen=True)
class RunResult:
    run_id: str
    cost_usd: float
    report_path: Path
    pdf_path: Path


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


async def run(question: str, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> RunResult:
    question = question.strip()
    if not question:
        raise ValueError("Research question is required.")

    output_path = _resolve_project_path(output_dir)
    os.chdir(PROJECT_ROOT)
    os.environ["RUNS_DIR"] = str(output_path)

    from config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.validate_llm_ready()
    output_path.mkdir(parents=True, exist_ok=True)

    from core.agent_loop import run_agent_async

    run_id = str(uuid.uuid4())
    result: dict[str, Any] = await run_agent_async(question, run_id=run_id)
    usage = result.get("usage", {})
    cost = float(usage.get("cost_estimate", 0.0) or 0.0)
    report_path = Path(str(result.get("report_md", output_path / run_id / "report.md")))
    pdf_path = Path(str(result.get("report_pdf_path", output_path / run_id / "report.pdf")))

    return RunResult(
        run_id=run_id,
        cost_usd=cost,
        report_path=report_path.resolve(),
        pdf_path=pdf_path.resolve(),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a headless Autonomous AI Researcher job."
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Research question to run. Falls back to RESEARCH_QUESTION.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated run reports. Defaults to ./runs/auto.",
    )
    return parser.parse_args()


def _question_from_args(args: argparse.Namespace) -> str:
    return (args.question or os.getenv("RESEARCH_QUESTION") or "").strip()


def format_summary(result: RunResult) -> str:
    return (
        f"✓ Run complete  |  run_id: {result.run_id}  |  "
        f"cost: ${result.cost_usd:.4f}  |  report: {result.report_path}"
    )


def main() -> int:
    args = _parse_args()
    try:
        result = asyncio.run(run(_question_from_args(args), args.output_dir))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(format_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
