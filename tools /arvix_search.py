import requests

def search_arxiv(query):

    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results=5"

    response = requests.get(url)

    return response.text