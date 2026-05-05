import os
from typing import List, Dict

def web_search(query: str, k: int = 5) -> List[Dict[str, str]]:
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query, max_results=k)
            return response.get("results", [])
        except Exception as e:
            print(f"Tavily search error: {e}")
            
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=k))
            return [{"title": r.get("title", ""), "content": r.get("body", ""), "url": r.get("href", "")} for r in results]
    except Exception as e:
        print(f"DDG search error: {e}")
        return []
