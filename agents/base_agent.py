"""
Abstract base class updated with asyncio and ReAct structured patterns.
"""
import asyncio
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from core.llm_client import LLMClient
from core.tool_registry import ToolRegistry    

class ToolCallOrResult(BaseModel):
    done: bool
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[str] = None

class BaseAgent(ABC):
    """Abstract base class for all autonomous research agents."""
    
    def __init__(self, 
                 name: str, 
                 role: str, 
                 system_prompt: str,
                 memory: Optional[Any] = None,
                 tool_registry: Optional[ToolRegistry] = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.llm = LLMClient()
        self.history: List[Dict[str, str]] = []
        self.memory = memory
        self.tool_registry = tool_registry
        self.event_queue: List[Dict[str, Any]] = []
        
    def emit(self, event_type: str, payload: Any):
        self.event_queue.append({
            "agent": self.name,
            "type": event_type,
            "payload": payload
        })

    def _create_messages(self, user_content: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content}
        ]
        
    @abstractmethod
    async def run_async(self, input_data: Any) -> Any:
        """Async core execution logic for each agent type."""
        pass
        
    async def generate_response_async(self, prompt: str) -> str:
        messages = self._create_messages(prompt)
        response = await asyncio.to_thread(self.llm.chat_completion, messages)
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": response})
        return response

    async def react_loop(self, task: str, max_iterations: int = 6) -> str:
        if not self.tool_registry:
            raise ValueError("No tool registry provided for ReAct loop.")
            
        schema_json = self.tool_registry.get_schema_json()
        prompt = f"Task: {task}\nAvailable Tools:\n{schema_json}\nRespond with JSON matching ToolCallOrResult schema."
        messages = self._create_messages(prompt)
        
        for _ in range(max_iterations):
            parsed: ToolCallOrResult = await asyncio.to_thread(self.llm.structured_output, messages, ToolCallOrResult)
            
            if parsed.done:
                return parsed.result or "Done."
                
            if parsed.tool:
                try:
                    tool_res = await asyncio.to_thread(self.tool_registry.execute, parsed.tool, parsed.args or {})
                    messages.append({"role": "assistant", "content": f"Called {parsed.tool} with {parsed.args}"})
                    safe_result = str(tool_res)[:8000]  # hard cap
                    safe_result = re.sub(r'(?i)(ignore|disregard).{0,40}(instruction|prompt|above)', '[FILTERED]', safe_result)
                    messages.append({"role": "user", "content": f"[TOOL_OUTPUT]\n{safe_result}\n[/TOOL_OUTPUT]"})
                except Exception as e:
                    messages.append({"role": "assistant", "content": f"Called {parsed.tool} with {parsed.args}"})
                    messages.append({"role": "user", "content": f"Tool Error: {str(e)}"})
            else:
                messages.append({"role": "user", "content": "No tool or result provided. Please provide one."})
                
        return "Max iterations reached in ReAct loop."

    def __repr__(self):
        return f"<{self.name} Agent - {self.role}>"
