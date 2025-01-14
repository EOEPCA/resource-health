import atoma
import pytest
# from os import environ
import requests


# search_query: str = environ["SEARCH_QUERY"]
# max_results: int = environ["MAX_RESULTS"]
search_query: str = "all:esa"
max_results: int = 10

query: str = f"search_query={search_query}&max_results={max_results}"
url: str = f"http://export.arxiv.org/api/query?{query}"


def test_arxiv_links() -> None:
    response = requests.get(url)
    assert response.status_code == 200, "arXiv API did not return a 200 response"
    
    feed = atoma.parse_atom_bytes(response.content)
    assert len(feed.entries) > 0, "arXiv feed does not contain any entries"
    
    doi_links = []
    for entry in feed.entries:
        doi_href = [link.href for link in entry.links if link.title == "doi"]
        doi_links.extend(doi_href)
    
    doi_links_and_status_codes = [(doi, requests.get(doi).status_code) for doi in doi_links]
    
    bad_status_codes = [(doi, code) for (doi, code) in doi_links_and_status_codes if code != 200]

    assert len(bad_status_codes) == 0, f"Follows the list of DOI links and their status codes which are not 200: {bad_status_codes}"
