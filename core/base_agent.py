from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.llm_client import LLMClient

class BaseAgent(ABC):
    """Abstract base class for all autonomous research agents."""
    
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.llm = LLMClient()
        self.history: List[Dict[str, str]] = []
        
    def _create_messages(self, user_content: str) -> List[Dict[str, str]]:
        """Wraps user input in a standard chat context."""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content}
        ]
        
    @abstractmethod
    def run(self, input_data: Any) -> Any:
        """Core execution logic for each agent type."""
        pass
        
    def generate_response(self, prompt: str) -> str:
        """Wrapper for LLM call with agent context."""
        messages = self._create_messages(prompt)
        response = self.llm.chat_completion(messages)
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": response})
        return response

    def __repr__(self):
        return f"<{self.name} Agent - {self.role}>"
