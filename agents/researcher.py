from typing import List, Dict, Any
from core.base_agent import BaseAgent
from tools .arvix_search import search_arxiv

class Researcher(BaseAgent):
    """Researcher Agent: Gathers and synthesizes technical information from arXiv."""
    
    def __init__(self):
        super().__init__(
            name="Researcher",
            role="Academic Librarian and Peer-Reviewer",
            system_prompt=("You are a technical researcher who excels at reading technical "
                           "XML data from academic APIs. Your goal is to synthesize the findings from "
                           "the provided paper metadata into clear technical summaries that can "
                           "inform an experimenter on the state of the art.")
        )

    def run(self, query: str) -> str:
        """Fetch papers based on a query and synthesize the results."""
        # 1. External tool use (fetching from arXiv)
        raw_papers = search_arxiv(query)
        
        # 2. Reasoning Loop
        prompt = (f"Synthesize the following paper results based on the research query: '{query}'. "
                  f"Raw Results: {raw_papers}")
        
        return self.generate_response(prompt)
