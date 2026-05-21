import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)


def web_search(query: str, k: int = 5) -> List[Dict[str, str]]:
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query, max_results=k)
            return response.get("results", [])
        except Exception as e:
            logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", e)

    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=k))
            return [{"title": r.get("title", ""), "content": r.get("body", ""), "url": r.get("href", "")} for r in results]
    except Exception as e:
        logger.warning("DuckDuckGo search failed, returning empty results: %s", e)
        return []
