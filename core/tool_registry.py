"""
Singleton pattern handling ReAct logic dynamically loading the execution sandbox environment.
"""
import json
from dataclasses import dataclass
from typing import Callable, Dict, Any, List
from tools.arxiv_search import search_arxiv
from tools.web_search import web_search
from tools.paper_parser import parse_pdf
from tools.code_executor import PythonExecutor

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    fn: Callable

class ToolRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance.tools = {}
            cls._instance._init_default_tools()
        return cls._instance
        
    def _init_default_tools(self):
        self.register(ToolDefinition(
            name="search_arxiv",
            description="Search arXiv for research papers.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]},
            fn=search_arxiv
        ))
        self.register(ToolDefinition(
            name="web_search",
            description="Search the web for information as a fallback.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}}, "required": ["query"]},
            fn=web_search
        ))
        self.register(ToolDefinition(
            name="parse_pdf",
            description="Parse a PDF document from an arxiv URL.",
            input_schema={"type": "object", "properties": {"url_or_path": {"type": "string"}}, "required": ["url_or_path"]},
            fn=parse_pdf
        ))
        executor = PythonExecutor()
        self.register(ToolDefinition(
            name="run_python_code",
            description="Run python code in an isolated sandbox.",
            input_schema={"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
            fn=executor.execute
        ))

    def register(self, tool_def: ToolDefinition):
        self.tools[tool_def.name] = tool_def
        
    def get_schema_json(self) -> str:
        schemas = []
        for t in self.tools.values():
            schemas.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema
            })
        return json.dumps(schemas, indent=2)

    def execute(self, name: str, args: dict) -> Any:
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found in registry.")
        return self.tools[name].fn(**args)
