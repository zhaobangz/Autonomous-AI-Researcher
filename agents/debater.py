"""
Adversarial validation agent.
"""
from typing import Any
from agents.base_agent import BaseAgent
from agents.critic import CriticReport

class Debater(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        super().__init__(
            name="Debater",
            role="Scientific Adversary",
            system_prompt=(
                "You are a rigorous scientific adversary. You will be given a "
                "Critic's review of a research experiment. Your job is to find "
                "logical flaws, unsupported conclusions, and overlooked alternative "
                "explanations in the Critic's own reasoning. Be specific and cite "
                "the exact claims you challenge."
            ),
            memory=memory,
            tool_registry=tool_registry
        )

    async def run_async(self, critic_report: CriticReport) -> str:
        self.emit("status", "Debating the Critic's review.")
        prompt = f"Critic Review:\n{critic_report.model_dump_json(indent=2)}"
        rebuttal = await self.generate_response_async(prompt)
        return rebuttal
