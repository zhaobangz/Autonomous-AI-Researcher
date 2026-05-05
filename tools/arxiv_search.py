import arxiv
from pydantic import BaseModel
from typing import List

class ArxivPaper(BaseModel):
    id: str
    title: str
    authors: List[str]
    abstract: str
    pdf_url: str
    published: str

def search_arxiv(query: str, max_results: int = 5) -> List[ArxivPaper]:
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        papers = []
        for result in client.results(search):
            papers.append(ArxivPaper(
                id=result.get_short_id(),
                title=result.title,
                authors=[a.name for a in result.authors],
                abstract=result.summary,
                pdf_url=result.pdf_url,
                published=str(result.published)
            ))
        return papers
    except Exception as e:
        print(f"Error searching arxiv: {e}")
        return []