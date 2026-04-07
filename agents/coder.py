from typing import List, Dict, Any
from core.base_agent import BaseAgent
from tools .code_executor import PythonExecutor

class Coder(BaseAgent):
    """Coder Agent: Translates research insights into executable Python code."""
    
    def __init__(self):
        super().__init__(
            name="Coder",
            role="Research Software Engineer",
            system_prompt=("You are a specialist in writing reproducible research experiments. "
                           "Your goal is to take a research summary and write a COMPLETE Python script "
                           "that benchmarks or tests the research hypotheses. Output ONLY the raw "
                           "code blocks with NO explanations or markdown at the start/end.")
        )
        self.executor = PythonExecutor()

    def run(self, research_summary: str) -> Dict[str, Any]:
        """Convert a summary into a Python script and execute it."""
        prompt = (f"Translate these research insights into a Python experiment. "
                  f"Insights: {research_summary}")
        
        # 1. Logic generation
        code = self.generate_response(prompt)
        
        # 2. Cleanup (removing markdown markers)
        code = self._clean_code(code)
        
        # 3. Execution
        results = self.executor.execute(code)
        
        return {
            "code": code,
            "results": results
        }

    def _clean_code(self, code: str) -> str:
        """Utility to strip markdown code blocks."""
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
