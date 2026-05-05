"""
Scientific Critic utilizing async outputs validation.
"""
from typing import Any
import asyncio
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class CriticReport(BaseModel):
    strengths: str
    weaknesses: str
    bias_check: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommendations: str
    final_verdict: str

class Critic(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        super().__init__(
            name="Critic",
            role="Scientific Critic",
            system_prompt=(
                "You are a Scientific Critic. Evaluate whether the code results align with the initial research goal. "
                "Identify biases, errors, and areas for further iteration."
            ),
            memory=memory,
            tool_registry=tool_registry
        )

    async def run_async(self, context_summary: str, stream_callback=None) -> CriticReport:
        self.emit("status", "Critiquing the execution and results.")
        prompt = f"Evaluate the following research context and code execution results:\n\n{context_summary}"
        
        if stream_callback:
            messages = self._create_messages(prompt + "\nProvide your final verdict clearly and critically.")
            verdict = ""
            async for token in self.llm.stream_completion_async(messages):
                stream_callback("Critic", token)
                verdict += token
                
            messages.append({"role": "assistant", "content": verdict})
            messages.append({"role": "user", "content": "Now map your evaluation securely into the required JSON schema structure."})
            report = await asyncio.to_thread(self.llm.structured_output, messages, CriticReport)
            report.final_verdict = verdict
        else:
            messages = self._create_messages(prompt)
            report = await asyncio.to_thread(self.llm.structured_output, messages, CriticReport)
            
        self.emit("review_generated", report.model_dump())
        return report
