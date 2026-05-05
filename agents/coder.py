"""
Async Coder tied into ToolRegistry for secure sandbox execution.
"""
from typing import Dict, Any
import asyncio
from agents.base_agent import BaseAgent
from core.tool_registry import ToolRegistry

class Coder(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        super().__init__(
            name="Coder",
            role="Research Software Engineer",
            system_prompt=(
                "You are a specialist in writing reproducible research experiments. "
                "Write a COMPLETE Python script that benchmarks or tests the research hypotheses. "
                "Output ONLY the raw code blocks. "
                "Start your code with `import sys, json, time` and ensure any final results are printed."
            ),
            memory=memory,
            tool_registry=tool_registry
        )

    async def run_async(self, research_summary: str) -> Dict[str, Any]:
        prompt = f"Translate these research insights into a Python experiment.\nInsights:\n{research_summary}"
        self.emit("status", "Writing Python experiment code")
        
        registry = self.tool_registry or ToolRegistry()
        
        for attempt in range(2):
            code = await self.generate_response_async(prompt)
            code = self._clean_code(code)
            
            if "import sys" not in code:
                code = "import sys, json, time\n" + code
                
            self.emit("status", "Executing code in sandbox")
            results = await asyncio.to_thread(registry.execute, "run_python_code", {"code": code})
            
            if results["exit_code"] != 0 and "ModuleNotFoundError" in results["stderr"]:
                if attempt == 0:
                    self.emit("status", "ImportError detected. Retrying code generation.")
                    prompt += f"\n\nPrevious attempt failed with error:\n{results['stderr']}\nPlease rewrite the code to NOT use this missing module or print a mock result instead."
                    continue
            
            break
            
        return {
            "code": code,
            "results": results
        }

    def _clean_code(self, code: str) -> str:
        code = code.strip()
        if "```" in code:
            lines = code.split('\n')
            clean_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    clean_lines.append(line)
            return '\n'.join(clean_lines) if clean_lines else code
        return code
