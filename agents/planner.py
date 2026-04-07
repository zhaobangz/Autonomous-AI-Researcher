from typing import List, Dict, Any
from core.base_agent import BaseAgent
import json

class Planner(BaseAgent):
    """Planner Agent: Breaks down research goals into structured milestones."""
    
    def __init__(self):
        super().__init__(
            name="Planner",
            role="Senior Research Project Manager",
            system_prompt=("You are a Senior Strategic Researcher. Your goal is to take a research question "
                           "and output a structured list of 4-6 specific sub-tasks. These must include: "
                           "1. Literature discovery phase (which keywords to search). "
                           "2. Hypothesis extraction phase. "
                           "3. Experimental design phase. "
                           "4. Execution and Evaluation phase. "
                           "Output ONLY a JSON list of tasks.")
        )

    def run(self, research_question: str) -> List[str]:
        """Convert a broad research question into a tactical set of steps."""
        prompt = f"Develop a research plan for the following question: '{research_question}'"
        response = self.generate_response(prompt)
        
        # Simple extraction for now; in a production setting we'd use structured output
        try:
            # Basic attempt to parse if the LLM followed instructions
            if "[" in response:
                start = response.find("[")
                end = response.rfind("]") + 1
                return json.loads(response[start:end])
            else:
                return [line for line in response.split('\n') if line.strip()]
        except json.JSONDecodeError:
            return response.split('\n')
