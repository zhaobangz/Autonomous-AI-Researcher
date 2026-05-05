"""
Researcher configured dynamically to pull from the dynamic ReAct tool pool.
"""
from agents.base_agent import BaseAgent
from core.tool_registry import ToolRegistry

class Researcher(BaseAgent):
    def __init__(self, memory=None, tool_registry: ToolRegistry = None):
        if tool_registry is None:
            tool_registry = ToolRegistry()
            
        super().__init__(
            name="Researcher",
            role="Academic Librarian and Peer-Reviewer",
            system_prompt=(
                "You are a technical researcher. Synthesize findings using available tools. "
                "Use search_arxiv to find papers, parse_pdf to read them, and web_search as a fallback. "
                "When you have enough information, set done=true and provide the final summary in the result field."
            ),
            memory=memory,
            tool_registry=tool_registry
        )

    async def run_async(self, query: str, stream_callback=None) -> str:
        self.emit("status", f"Starting ReAct research loop for: {query}")
        result = await self.react_loop(query, max_iterations=4)
        
        if stream_callback:
            messages = self._create_messages(f"Provide a clear, cohesive final narrative of this research context: {result}")
            final_summary = ""
            async for token in self.llm.stream_completion_async(messages):
                stream_callback("Researcher", token)
                final_summary += token
            result = final_summary
            
        if self.memory:
            self.memory.add(
                texts=[result], 
                metadatas=[{"source": "researcher_react", "query": query}]
            )
            
        return result
