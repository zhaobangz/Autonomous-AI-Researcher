from typing import Any, Dict
from core.base_agent import BaseAgent

class Critic(BaseAgent):
    """Critic Agent: Evaluates findings and synthesizes final research results."""
    
    def __init__(self):
        super().__init__(
            name="Critic",
            role="Scientific Reviewer and Quality Assurance Analyst",
            system_prompt=("You are a specialist in validating academic research. "
                           "Your goal is to take a research roadmap, scientific synthesis, "
                           "and experimental results to produce a comprehensive final report. "
                           "Identify strengths, weaknesses, biases, and future directions.")
        )

    def run(self, context: Dict[str, Any]) -> str:
        """Analyze the total context and produce a final synthesis."""
        prompt = (f"Review the follow research lifecycle and produce a final report. "
                  f"Context Map: {context}")
        
        # 1. Reasoning cycle
        return self.generate_response(prompt)
