"""
core/tool_registry.py — Dynamic tool registry for ReAct agent loops.

Design notes
------------
* **No singleton** — each research run constructs its own ToolRegistry so that
  tool state (e.g. the PythonExecutor's Docker client) is scoped to a single
  run and concurrent runs don't share mutable state.
* Tools are registered eagerly in `_init_default_tools()` but the PythonExecutor
  is constructed lazily (via the function closure) so that import-time Docker
  unavailability raises a warning rather than crashing the process.
* External callers can extend the registry with `registry.register(ToolDefinition(…))`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    fn: Callable


class ToolRegistry:
    """
    A plain, non-singleton registry of callable tools.

    Instantiate once per research run:

        registry = ToolRegistry()
        result   = registry.execute("search_arxiv", {"query": "attention mechanism"})
    """

    def __init__(self) -> None:
        self.tools: Dict[str, ToolDefinition] = {}
        self._executor = None  # lazy
        self._init_default_tools()

    # ------------------------------------------------------------------
    # Default tools
    # ------------------------------------------------------------------
    def _init_default_tools(self) -> None:
        from tools.arxiv_search import search_arxiv
        from tools.paper_parser import parse_pdf
        from tools.web_search import web_search

        self.register(
            ToolDefinition(
                name="search_arxiv",
                description="Search arXiv for research papers on a topic.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {
                            "type": "integer",
                            "description": "Max papers to return (default 5)",
                        },
                    },
                    "required": ["query"],
                },
                fn=search_arxiv,
            )
        )
        self.register(
            ToolDefinition(
                name="web_search",
                description="Search the public web for information (Tavily / DuckDuckGo fallback).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "k": {"type": "integer", "description": "Number of results"},
                    },
                    "required": ["query"],
                },
                fn=web_search,
            )
        )
        self.register(
            ToolDefinition(
                name="parse_pdf",
                description="Download and parse a PDF from an arXiv URL.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url_or_path": {
                            "type": "string",
                            "description": "arXiv PDF URL (https://arxiv.org/pdf/…)",
                        }
                    },
                    "required": ["url_or_path"],
                },
                fn=parse_pdf,
            )
        )

        # PythonExecutor is lazy — constructed on first use so that Docker
        # unavailability at startup is a warning, not a crash.
        def _run_python_code(code: str, timeout: int = 120) -> dict:
            if self._executor is None:
                from tools.code_executor import PythonExecutor
                self._executor = PythonExecutor()
            return self._executor.execute(code=code, timeout=timeout)

        self.register(
            ToolDefinition(
                name="run_python_code",
                description="Execute Python code in an isolated Docker sandbox and return stdout/stderr.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Complete Python script to execute",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds (default 120)",
                        },
                    },
                    "required": ["code"],
                },
                fn=_run_python_code,
            )
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def register(self, tool_def: ToolDefinition) -> None:
        """Register (or replace) a tool by name."""
        self.tools[tool_def.name] = tool_def
        logger.debug("Registered tool: %s", tool_def.name)

    def get_schema_json(self) -> str:
        """Return JSON description of all registered tools for LLM prompts."""
        schemas: List[dict] = [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            }
            for t in self.tools.values()
        ]
        return json.dumps(schemas, indent=2)

    def execute(self, name: str, args: dict) -> Any:
        """
        Execute a registered tool by name.

        Raises
        ------
        ValueError
            If the tool name is not registered.
        """
        if name not in self.tools:
            available = ", ".join(self.tools.keys())
            raise ValueError(
                f"Tool '{name}' not found in registry. Available: {available}"
            )
        logger.debug("Executing tool '%s' with args: %s", name, list(args.keys()))
        return self.tools[name].fn(**args)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={list(self.tools.keys())}>"
