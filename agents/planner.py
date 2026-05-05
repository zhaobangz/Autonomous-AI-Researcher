"""
Structured async execution planner logic.
"""
from typing import List, Any
import asyncio
from pydantic import BaseModel, field_validator, Field
from agents.base_agent import BaseAgent

class PlanStep(BaseModel):
    kind: str = Field(description="One of: search, summarize, code, exec, review")
    rationale: str
    expected_output: str

class Plan(BaseModel):
    steps: List[PlanStep]

    @field_validator('steps')
    @classmethod
    def validate_steps(cls, steps):
        kinds = [s.kind for s in steps]
        if 'search' not in kinds:
            raise ValueError("Plan must contain at least one 'search' step.")
        if 'code' not in kinds:
            raise ValueError("Plan must contain at least one 'code' step.")
        valid_kinds = {'search', 'summarize', 'code', 'exec', 'review'}
        for k in kinds:
            if k not in valid_kinds:
                raise ValueError(f"Invalid step kind: {k}")
        return steps

class Planner(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        super().__init__(
            name="Planner",
            role="Senior Research Project Manager",
            system_prompt=(
                "You are a Senior Research Project Manager. "
                "Your goal is to decompose a complex research query into a structured roadmap. "
                "You must include at least one 'search' step and one 'code' step."
            ),
            memory=memory,
            tool_registry=tool_registry
        )

    async def run_async(self, query: str, kg=None) -> Plan:
        if kg:
            related_nodes = kg.query_related(query, k=3)
            prior_brief = "\n".join([
                f"- Run {r.get('run_id')}: {r.get('title')} (similarity: {r.get('similarity', 0):.2f})\n  Summary: {r.get('summary', '')[:200]}"
                for r in related_nodes
            ])
            if prior_brief:
                self.system_prompt += f"\n\nPRIOR RESEARCH CONTEXT (do not repeat, build upon):\n{prior_brief}"

        messages = self._create_messages(query)
        self.emit("status", f"Generating plan for: {query}")
        plan = await asyncio.to_thread(self.llm.structured_output, messages, Plan)
        self.emit("plan_generated", plan.model_dump())
        return plan
