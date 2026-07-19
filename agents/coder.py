"""
agents/coder.py — Async Coder tied into ToolRegistry for secure sandbox execution.

Key improvements
----------------
* _clean_code is now regex-based and correctly handles:
    - Fenced code blocks with or without a language tag (```python … ```)
    - Code blocks without a closing fence (truncated LLM responses)
    - Responses that contain only raw code with no markdown
    - Multiple code blocks (the largest one is returned)
* run_async uses self.tool_registry directly (no silent fallback to a new
  ToolRegistry()) so there is never a second, orphaned PythonExecutor.
* Logging replaces emit("status", …) for server-side visibility.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent
from core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

# Regex that matches a fenced code block with an optional language tag.
# Group 1 captures the code inside the fence.
# The closing fence is optional (handles truncated LLM output).
_FENCE_RE = re.compile(
    r"```(?:[a-zA-Z0-9_\-+#]*\n)?(.*?)(?:```|$)",
    re.DOTALL,
)


class Coder(BaseAgent):
    def __init__(self, memory=None, tool_registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="Coder",
            role="Research Software Engineer",
            system_prompt=(
                "You are a specialist in writing reproducible research experiments. "
                "Write a COMPLETE, self-contained Python script that benchmarks or "
                "tests the research hypotheses described by the user. "
                "Rules:\n"
                "  1. Output ONLY a fenced Python code block — no prose before or after.\n"
                "  2. The script must start with `import sys, json, time`.\n"
                "  3. Print all important results to stdout as JSON.\n"
                "  4. Only use the Python standard library plus: "
                "numpy, pandas, matplotlib, scipy, scikit-learn.\n"
                "  5. Ensure the script runs without user interaction."
            ),
            memory=memory,
            tool_registry=tool_registry,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    async def run_async(self, research_summary: str) -> Dict[str, Any]:
        if self.tool_registry is None:
            raise RuntimeError("Coder requires a ToolRegistry to execute code.")

        prompt = (
            "Translate these research insights into a Python experiment.\n\n"
            f"Insights:\n{research_summary}"
        )
        self.emit("status", "Writing Python experiment code")
        logger.info("Coder | generating experiment code")

        code = ""
        results: Dict[str, Any] = {
            "stdout": "", "stderr": "No code generated.", "exit_code": -1,
            "runtime": 0.0, "artifacts": [],
        }

        for attempt in range(2):
            raw = await self.generate_response_async(prompt)
            code = self._clean_code(raw)

            if not code.strip():
                logger.warning("Coder | attempt %d produced empty code block", attempt + 1)
                prompt += "\n\nPlease respond with ONLY a valid Python code block."
                continue

            # Ensure required stdlib imports are present
            if "import sys" not in code:
                code = "import sys, json, time\n" + code

            self.emit("status", "Executing code in sandbox")
            logger.info("Coder | executing code (attempt %d)", attempt + 1)

            results = await asyncio.to_thread(
                self.tool_registry.execute,
                "run_python_code",
                {"code": code},
            )

            exit_code = results.get("exit_code", -1)
            stderr = results.get("stderr", "")

            if exit_code != 0 and "ModuleNotFoundError" in stderr and attempt == 0:
                logger.warning("Coder | ModuleNotFoundError, retrying: %s", stderr[:200])
                self.emit("status", "Import error detected — retrying without missing module")
                prompt += (
                    f"\n\nPrevious attempt failed with:\n{stderr}\n\n"
                    "Rewrite the code WITHOUT this missing module. "
                    "Use only numpy, pandas, matplotlib, scipy, scikit-learn, or the standard library. "
                    "If the computation isn't possible, print a clearly labelled mock result."
                )
                continue

            # Success (or non-import error) — stop retrying
            break

        logger.info(
            "Coder | done (exit_code=%s, runtime=%.1fs)",
            results.get("exit_code"), results.get("runtime", 0),
        )
        return {"code": code, "results": results}

    # ------------------------------------------------------------------
    # Code extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_code(raw: str) -> str:
        """
        Extract the largest Python code block from a raw LLM response.

        Strategy
        --------
        1. Search for fenced code blocks (``` … ```).  If any are found,
           return the *longest* match (covers cases where the LLM includes
           a short example followed by the real script).
        2. If no fenced block is detected, assume the entire response is
           code (the LLM obeyed the instruction to output only code).
        """
        raw = raw.strip()

        matches = _FENCE_RE.findall(raw)
        if matches:
            # Pick the longest captured block (the real experiment code)
            best = max(matches, key=len).strip()
            if best:
                return best

        # Fallback: strip any stray ``` markers and return as-is
        cleaned = raw.replace("```", "").strip()
        return cleaned
