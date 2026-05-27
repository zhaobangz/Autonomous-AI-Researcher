from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from run_research import DEFAULT_OUTPUT_DIR, PROJECT_ROOT, run


SUMMARY_FIELDS = [
    "question",
    "run_id",
    "cost_usd",
    "report_path",
    "status",
    "error_message",
]


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multiple headless research jobs from a question file."
    )
    parser.add_argument("questions_file", help="Plain-text file of questions.")
    return parser.parse_args()


def _load_questions(path: Path) -> list[str]:
    questions: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        question = line.strip()
        if question and not question.startswith("#"):
            questions.append(question)
    return questions


async def _run_batch(questions_file: Path) -> Path:
    questions = _load_questions(questions_file)
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "batch_summary.csv"
    rows: list[dict[str, str]] = []

    for question in questions:
        try:
            result = await run(question, output_dir)
            rows.append(
                {
                    "question": question,
                    "run_id": result.run_id,
                    "cost_usd": f"{result.cost_usd:.4f}",
                    "report_path": str(result.report_path),
                    "status": "success",
                    "error_message": "",
                }
            )
        except Exception as exc:
            print(f"Run failed for question: {question}\nError: {exc}", file=sys.stderr)
            rows.append(
                {
                    "question": question,
                    "run_id": "",
                    "cost_usd": "",
                    "report_path": "",
                    "status": "error",
                    "error_message": str(exc),
                }
            )

    with summary_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return summary_path


def main() -> int:
    args = _parse_args()
    questions_file = _resolve_project_path(args.questions_file)
    try:
        summary_path = asyncio.run(_run_batch(questions_file))
    except Exception as exc:
        print(f"Batch failed: {exc}", file=sys.stderr)
        return 1

    print(f"Batch summary written to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
